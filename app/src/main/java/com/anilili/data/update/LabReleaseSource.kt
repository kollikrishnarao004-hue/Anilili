package com.anilili.data.update

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import okhttp3.OkHttpClient
import okhttp3.Request

/** Authenticated access to approved APKs; the source fork remains public. */
internal object LabReleaseSource {
    const val REPOSITORY = "kollikrishnarao004-hue/Anilili-Lab-Releases"
    const val APPLICATION_ID = "com.anilili.lab"
    const val APK_NAME = "Anilili-Lab.apk"
    const val MANIFEST_NAME = "lab-update.json"
    const val RELEASE_URL = "https://api.github.com/repos/$REPOSITORY/releases/latest"

    fun fetch(client: OkHttpClient, json: Json, applicationId: String, token: String): UpdateManager.UpdateInfo {
        val releaseRequest = Request.Builder().url(RELEASE_URL)
            .header("Authorization", "Bearer $token")
            .header("Accept", "application/vnd.github+json")
            .header("Cache-Control", "no-cache")
            .header("X-GitHub-Api-Version", "2022-11-28")
            .build()
        val release = json.parseToJsonElement(readBounded(client, releaseRequest)).jsonObject
        require(release["draft"]?.jsonPrimitive?.content == "false" &&
            release["prerelease"]?.jsonPrimitive?.content == "false") { "Lab release is not approved" }
        val assets = release.getValue("assets").jsonArray.map { it.jsonObject }
        fun asset(name: String): String {
            val match = assets.single { it["name"]?.jsonPrimitive?.content == name }
            return match.getValue("url").jsonPrimitive.content.also(::requireAssetUrl)
        }
        val manifestRequest = Request.Builder().url(asset(MANIFEST_NAME))
        authorizeAsset(manifestRequest, token)
        val info = parse(readBounded(client, manifestRequest.build()), json, applicationId)
        require(release.getValue("tag_name").jsonPrimitive.content == "lab-v${info.version}-build${info.build}") {
            "Release and manifest versions differ"
        }
        return info.copy(apkUrl = asset(APK_NAME), privateGitHubAsset = true)
    }

    internal fun requireAssetUrl(url: String) {
        require(Regex("https://api\\.github\\.com/repos/$REPOSITORY/releases/assets/\\d+").matches(url)) {
            "Private update download must belong to the Lab repository"
        }
    }

    fun authorizeAsset(request: Request.Builder, token: String) {
        requireAssetUrl(request.build().url.toString())
        request.header("Authorization", "Bearer $token")
            .header("Accept", "application/octet-stream")
            .header("X-GitHub-Api-Version", "2022-11-28")
    }

    private fun readBounded(client: OkHttpClient, request: Request): String =
        client.newCall(request).execute().use { response ->
            check(response.isSuccessful) { "Private Lab feed HTTP ${response.code}; check token access and published releases" }
            val source = requireNotNull(response.body).source()
            require(!source.request(256L * 1024 + 1)) { "Lab update metadata is too large" }
            source.readUtf8()
        }

    internal fun parse(body: String, json: Json, applicationId: String): UpdateManager.UpdateInfo {
        val manifest = json.parseToJsonElement(body).jsonObject
        require(manifest.getValue("schemaVersion").jsonPrimitive.int == 1) { "Unsupported Lab update format" }
        require(applicationId == APPLICATION_ID &&
            manifest.getValue("applicationId").jsonPrimitive.content == applicationId) {
            "This update is for a different app"
        }
        val version = manifest.getValue("version").jsonPrimitive.content
        require(Regex("\\d+\\.\\d+\\.\\d+").matches(version)) { "Invalid Lab version" }
        val build = manifest.getValue("versionCode").jsonPrimitive.int
        require(build in 1..2_100_000_000) { "Invalid Lab build number" }
        val tag = "lab-v$version-build$build"
        require(manifest.getValue("tag").jsonPrimitive.content == tag) { "Lab release tag mismatch" }
        val url = manifest.getValue("apkUrl").jsonPrimitive.content
        require(url == "https://github.com/$REPOSITORY/releases/download/$tag/$APK_NAME") {
            "Update APK must belong to this fork and release"
        }
        val size = manifest.getValue("sizeBytes").jsonPrimitive.long
        require(size > 0) { "Invalid update APK size" }
        val checksum = manifest.getValue("sha256").jsonPrimitive.content
        require(Regex("[0-9a-fA-F]{64}").matches(checksum)) { "Invalid update APK checksum" }
        return UpdateManager.UpdateInfo(
            version = version,
            changelog = manifest["changelog"]?.jsonPrimitive?.content.orEmpty(),
            apkUrl = url,
            sizeBytes = size,
            build = build,
            important = true,
            sha256 = checksum.lowercase(),
        )
    }
}
