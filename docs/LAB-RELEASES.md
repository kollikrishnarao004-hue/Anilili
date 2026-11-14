# Anilili Lab: private Android testing and updates

The source stays in public `kollikrishnarao004-hue/Anilili`. APKs, signed candidates,
build records and approved releases live in private
[`kollikrishnarao004-hue/Anilili-Lab-Releases`](https://github.com/kollikrishnarao004-hue/Anilili-Lab-Releases).
No signed APK is attached to the public source repository.

## What stays permanent

- Android application ID: `com.anilili.lab`; launcher name: **Anilili Lab**.
- Signing certificate: the public fingerprint in `signing-certificate.sha256`.
- One signing key, outside the checkout at `~/.local/share/anilili-lab-signing/`.
  Keep a secure independent backup of that entire directory, including credentials.
  Losing it prevents normal updates to installed Lab apps. GitHub secrets are not a backup.
- The app's namespace stays `com.anilili`. Mobile APKs are universal so no ABI choice is needed.

The first Lab install is separate from upstream and starts with its own library. Subsequent
Lab updates keep its app data, library and accounts because package and signing key stay the same.
Do not uninstall between updates. Android requires the user to confirm installation.

## Requirements and one-time setup

1. JDK 17, the Gradle 8.13 wrapper, Android SDK platform 36 and build-tools 35.0.1.
   GitHub workflows install these. Local builds use `ANDROID_HOME` pointing to the SDK.
2. A private release repository owned by your GitHub account, with Actions enabled.
   Private-repository Actions use the account's included minutes/storage allowance; check usage.
3. `python3 scripts/bootstrap_lab_signing.py` creates/reuses the permanent keystore and stores
   four secrets **only in the private release repository**: `LAB_KEYSTORE_BASE64`,
   `LAB_KEYSTORE_PASSWORD`, `LAB_KEY_ALIAS`, `LAB_KEY_PASSWORD`.
4. Install the workflow templates from `infrastructure/lab-releases/.github/workflows/`
   into the private repository's `.github/workflows/`. Their default branch is `main`.
5. On the phone, sign into GitHub in the browser as the repository owner (or an invited account).
   Download the first approved `Anilili-Lab.apk` from the private release page and install it.
6. Create a **fine-grained personal access token** on GitHub: resource owner is your account,
   repository access is **only `Anilili-Lab-Releases`**, repository permission is
   **Contents: read-only** (Metadata read is automatic). Choose an expiration you can maintain.
   Enter it once under **Settings → App → Private update access** on the phone.
   Never paste it into chat, source, release notes, or an APK build variable.

The updater uses GitHub's authenticated release/asset APIs, so logging into the phone browser
alone does not authenticate in-app updates. Its token is encrypted in a separate device-only
preferences file, not exported with backups or switched with anime-service profiles. It is only
attached to the fixed private GitHub repository's API requests; cross-host download redirects
do not retain the Authorization header. Replace/remove the token in the same settings row.
Expired/revoked access produces an update-check error; the installed app continues working.

## Each approved handoff

1. Implement and review changes in the source fork. Update `release-notes.md` and
   `version.properties`. Every new candidate gets a larger `versionCode`; never reuse a code
   for different APK bytes. Version names must not decrease. The first Lab candidate is
   `0.1.85`, build `97`, tag `lab-v0.1.85-build97`.
2. Commit and push the reviewed source to `main`. Public **Android checks** runs mobile release
   unit tests and vital release lint, with no signing key or APK publication.
3. Dispatch **Prepare Lab APK** in the **private release repository**, passing the full reviewed
   source commit as `source_commit`. It must still be the source fork's `main` head.
   This repeats checks, builds a signed release, verifies its identity/signature, and creates a
   **draft** containing the exact APK, `lab-update.json` and `SHA256SUMS`.
   The private Actions artifact also retains R8 mappings, test/lint reports and the release files.
   No phone sees a draft as an update. The owner can inspect/download drafts while signed in.
4. Review the exact version, source commit, release notes, test result, and candidate APK.
   After explicit approval, dispatch **Publish approved Lab APK**, entering the draft's exact
   tag in both `tag` and `approval`, plus the reviewed `lab-update.json` SHA-256 in
   `manifest_sha256` (shown in the candidate summary and `SHA256SUMS`). A changed draft is rejected.
   The assistant may do this only for the approved handoff.
   Publication re-verifies the existing bytes and monotonically increasing build number, then
   publishes the private draft as the latest release. **It does not rebuild.**
5. Open Anilili Lab to see the update prompt, or use **Settings → App → Check for updates**.
   Allow “install unknown apps” for Anilili Lab when Android asks, then confirm the update.
   Automatic checks run when opened, with a five-minute floor; manual checks bypass the floor.
   Background push notifications or silent installs are not part of this pipeline.
6. Report the displayed build number with your testing feedback. We fix, review and repeat.

The APK is checked against its manifest's SHA-256 and exact size, this app's package name,
the manifest build number, and the installed app's signing certificate. HTTPS authenticates the
GitHub feed; the checksum is a corruption check, not an independent signature. Android performs
its own package/signature verification during installation as well.

## Recovery and limitations

- To revert a bad version, release the last-good source with a **new higher build number** and
  a nondecreasing version name. Repointing to an older APK cannot downgrade installed apps.
- Failed candidate build: inspect the private workflow logs/artifact; no update was published.
  Existing draft/tag collisions fail instead of overwriting a candidate.
- Keep mapping files from every published build beyond the 90-day Actions artifact retention.
  Download the private build record and archive it securely for long-term crash diagnosis.
- GitHub's private release assets require authorization; nobody can anonymously download them.
  Once downloaded, an APK can still be copied by its recipient. No DRM is added.
- No Play Store/Firebase account, hosted backend or paid service is required for this design.
- Upstream telemetry, announcements and Nostr update fallback are disabled for Lab.
- Provider/CDN availability and the metadata `DATA_OWNER` placeholder remain separate work.
  Shared upstream OAuth callback URI schemes may show an app chooser when upstream is installed.

References: [Android app signing](https://developer.android.com/studio/publish/app-signing),
[fine-grained GitHub tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens),
[GitHub release assets API](https://docs.github.com/en/rest/releases/assets?apiVersion=2022-11-28).
