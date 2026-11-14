package com.anilili.data.update

/** Portable, genuinely signed fixture; its example.com URL is part of the signed bytes. */
internal val signedUpdateEventJson = """
        {
          "id": "61ddae93a60885d570184110cf84502678c54d0ea84d319c911abb482dfdd82b",
          "pubkey": "f1abd1ac685aed1f5145271283cd9418bf13aa92ed26399df191ae0c08b22207",
          "created_at": 1754000000,
          "kind": 30078,
          "tags": [["d", "anilili-update"]],
          "content": "{\"version\":\"0.1.54\",\"changelog\":\"Fixture release for unit tests\",\"apkUrl\":\"https://example.com/Anilili.apk\",\"sizeBytes\":12345}",
          "sig": "b0e84789a9862b50e814a1e43a4b8bff34ac2bbb9e5ce0faeb8b06076bcdb41ebbb5e306ee86eac01acb653324bde0c325b90268f6130cd83a403655b3fded94"
        }
    """.trimIndent()
