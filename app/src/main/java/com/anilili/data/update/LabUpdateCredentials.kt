package com.anilili.data.update

import android.content.Context
import com.anilili.data.auth.SecureTokenStore

/** Device-only update access, excluded from account profiles and exported backups. */
internal object LabUpdateCredentials {
    private fun store(context: Context) = SecureTokenStore(
        context.applicationContext, "github_release_access", "anilili_lab_update_access",
    )

    fun load(context: Context): String? = store(context).load()

    fun save(context: Context, token: String) {
        val value = token.trim()
        require(value.length >= 20 && value.none(Char::isWhitespace)) { "Enter a valid GitHub token" }
        store(context).save(value)
    }

    fun clear(context: Context) = store(context).clear()
}
