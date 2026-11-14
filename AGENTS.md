# Anilili Lab working agreement

This is the Android Anilili fork. The source repository is public:
`kollikrishnarao004-hue/Anilili`. The user explicitly chose a separate testing app
with **private APKs**. Read `docs/LAB-RELEASES.md` before changing release behavior.

- Keep application ID `com.anilili.lab` and the permanent signing certificate stable.
- Signed APKs, build records and release workflows belong in private
  `kollikrishnarao004-hue/Anilili-Lab-Releases`, never the public source repository.
- Build a reviewable candidate for a handoff; publish only after the user explicitly
  approves that version/handoff. A push, successful test or draft is not approval.
- Publication promotes existing verified draft bytes, bound to the reviewed manifest
  SHA-256. Never rebuild during publication or silently replace a reviewed candidate.
- Update `version.properties` and `release-notes.md` for each new candidate. Increase
  `versionCode`; do not reuse a build number for different bytes or decrease versionName.
- Keep signing material outside Git in `~/.local/share/anilili-lab-signing/` and signing
  secrets only in the private release repository. Never print passwords or tokens.
- Phone-side GitHub access is a read-only, repository-scoped token entered in the app,
  encrypted separately from anime account profiles/backups. Never embed it in an APK.
- Keep upstream telemetry, announcements and upstream update fallback disabled in Lab.
- Check mobile release unit tests and vital release lint; check release packaging tests
  with `python3 -m unittest discover -s scripts -p test_lab_release.py`. Validate workflow
  changes with actionlint when available. Obtain code review before committing/deploying.
- Use explicit `--repo`/`-R` for GitHub commands so the upstream is never changed accidentally.

This project is not the AI gateway described by the home-directory AGENTS.md;
gateway-specific skills and deployment instructions do not apply here.
