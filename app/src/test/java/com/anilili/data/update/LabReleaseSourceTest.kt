package com.anilili.data.update

import com.anilili.BuildConfig
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Test
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertNull

class LabReleaseSourceTest {
    private val manifest = """{
        "schemaVersion":1,"applicationId":"com.anilili.lab",
        "version":"0.1.85","versionCode":97,"tag":"lab-v0.1.85-build97",
        "apkUrl":"https://github.com/kollikrishnarao004-hue/Anilili-Lab-Releases/releases/download/lab-v0.1.85-build97/Anilili-Lab.apk",
        "sizeBytes":12345,"sha256":"${"ab".repeat(32)}","changelog":"First Lab release"
    }"""

    private fun parse(text: String = manifest, appId: String = LabReleaseSource.APPLICATION_ID) =
        LabReleaseSource.parse(text, Json, appId)

    @Test fun `approved manifest supplies checksum build number and notes`() {
        val info = parse()
        assertEquals(97, info.build)
        assertEquals("ab".repeat(32), info.sha256)
        assertEquals("First Lab release", info.changelog)
        assertEquals(UpdateOffer.PROMPT, updateOffer(info.version, info.build, "0.1.84", 96))
    }

    @Test fun `upstream and foreign asset URLs are refused`() {
        assertThrows(IllegalArgumentException::class.java) {
            parse(manifest.replace("kollikrishnarao004-hue/Anilili-Lab-Releases", "sanilili/Anilili"))
        }
        assertThrows(IllegalArgumentException::class.java) {
            parse(manifest.replace("https://github.com/", "http://github.com/"))
        }
    }

    @Test fun `wrong app malformed checksum and mismatched tag are refused`() {
        assertThrows(IllegalArgumentException::class.java) { parse(appId = "com.miruronative") }
        assertThrows(IllegalArgumentException::class.java) { parse(manifest.replace("ab".repeat(32), "broken")) }
        assertThrows(IllegalArgumentException::class.java) { parse(manifest.replace("\"versionCode\":97", "\"versionCode\":98")) }
    }

    @Test fun `lab builds never enable upstream telemetry or announcements`() {
        assertFalse(BuildConfig.ENABLE_UPSTREAM_SERVICES)
    }

    @Test fun `private API fetch authenticates metadata and chooses the exact APK asset`() {
        val base = "https://api.github.com/repos/${LabReleaseSource.REPOSITORY}/releases/assets/"
        val requests = mutableListOf<String>()
        val client = OkHttpClient.Builder().addInterceptor { chain ->
            val request = chain.request()
            assertEquals("Bearer test-token", request.header("Authorization"))
            requests.add(request.url.toString())
            val body = if (request.url.toString() == LabReleaseSource.RELEASE_URL) {
                """{"draft":false,"prerelease":false,"tag_name":"lab-v0.1.85-build97","assets":[
                    {"name":"lab-update.json","url":"${base}11"},
                    {"name":"Anilili-Lab.apk","url":"${base}12"}]}"""
            } else {
                assertEquals("application/octet-stream", request.header("Accept"))
                manifest
            }
            Response.Builder().request(request).protocol(Protocol.HTTP_1_1).code(200).message("OK")
                .body(body.toResponseBody("application/json".toMediaType())).build()
        }.build()
        val info = LabReleaseSource.fetch(client, Json, LabReleaseSource.APPLICATION_ID, "test-token")
        assertEquals("${base}12", info.apkUrl)
        assertEquals(listOf(LabReleaseSource.RELEASE_URL, "${base}11"), requests)
        assertEquals(true, info.privateGitHubAsset)
    }

    @Test fun `private token is never attached to a foreign host or repository`() {
        assertThrows(IllegalArgumentException::class.java) {
            LabReleaseSource.authorizeAsset(okhttp3.Request.Builder().url("https://example.com/a.apk"), "secret")
        }
        assertThrows(IllegalArgumentException::class.java) {
            LabReleaseSource.requireAssetUrl("https://api.github.com/repos/sanilili/Anilili/releases/assets/12")
        }
    }

    @Test fun `asset redirect never sends the GitHub bearer to the storage host`() {
        MockWebServer().use { api ->
            MockWebServer().use { storage ->
                storage.enqueue(MockResponse().setBody("APK bytes"))
                val storageUrl = storage.url("/signed-asset").newBuilder().host("127.0.0.1").build()
                api.enqueue(MockResponse().setResponseCode(302).addHeader("Location", storageUrl))
                val request = okhttp3.Request.Builder().url(
                    "https://api.github.com/repos/${LabReleaseSource.REPOSITORY}/releases/assets/12",
                )
                LabReleaseSource.authorizeAsset(request, "private-token")
                val client = OkHttpClient.Builder().addInterceptor { chain ->
                    // Keep the production authorization helper, route only transport to local servers.
                    chain.proceed(chain.request().newBuilder().url(api.url("/asset")).build())
                }.build()
                client.newCall(request.build()).execute().use { assertEquals("APK bytes", it.body!!.string()) }
                assertEquals("Bearer private-token", api.takeRequest().getHeader("Authorization"))
                assertNull(storage.takeRequest().getHeader("Authorization"))
            }
        }
    }
}
