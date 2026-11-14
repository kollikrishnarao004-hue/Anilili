"""Release invariants: tamper detection, signer continuity and publication ordering."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import lab_release as lab


class LabReleaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        (self.directory / lab.APK).write_bytes(b"signed-test-apk")
        self.manifest = {
            "schemaVersion": 1, "applicationId": lab.APP_ID, "version": "0.1.85", "versionCode": 97,
            "tag": "lab-v0.1.85-build97", "commit": "a" * 40, "releaseRepositoryCommit": "b" * 40,
            "apkUrl": f"https://github.com/{lab.REPO}/releases/download/lab-v0.1.85-build97/{lab.APK}",
            "sizeBytes": 15, "sha256": lab.sha256(self.directory / lab.APK), "signerSha256": "c" * 64,
        }
        self.write_manifest()

    def write_manifest(self):
        (self.directory / lab.MANIFEST).write_text(json.dumps(self.manifest))
        (self.directory / "SHA256SUMS").write_text(
            f"{lab.sha256(self.directory / lab.APK)}  {lab.APK}\n"
            f"{lab.sha256(self.directory / lab.MANIFEST)}  {lab.MANIFEST}\n")

    def test_valid_candidate_preserves_source_and_signer(self):
        with mock.patch.object(lab, "inspect_apk", return_value="c" * 64), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(lab.verify(self.directory, self.manifest["tag"])["commit"], "a" * 40)

    def test_tampered_apk_is_rejected_before_inspection(self):
        (self.directory / lab.APK).write_bytes(b"changed-apk")
        with mock.patch.object(lab, "inspect_apk") as inspect, self.assertRaises(ValueError):
            lab.verify(self.directory, self.manifest["tag"])
        inspect.assert_not_called()

    def test_foreign_asset_url_is_rejected(self):
        self.manifest["apkUrl"] = "https://example.com/app.apk"
        self.write_manifest()
        with self.assertRaises(ValueError):
            lab.verify(self.directory, self.manifest["tag"])

    def test_manifest_signer_cannot_differ_from_verified_apk(self):
        with mock.patch.object(lab, "inspect_apk", return_value="d" * 64), self.assertRaises(ValueError):
            lab.verify(self.directory, self.manifest["tag"])

    def test_changed_manifest_cannot_be_published_under_old_approval(self):
        release = {"draft": True, "prerelease": False, "target_commitish": "b" * 40}

        def run(*args):
            if args[:2] == ("gh", "api"):
                return json.dumps(release)
            if args[:3] == ("gh", "release", "download"):
                destination = Path(args[args.index("--dir") + 1])
                (destination / lab.MANIFEST).write_text("changed since approval")
                return ""
            self.fail("Publication must not happen after a changed manifest")

        with mock.patch.object(lab, "run", side_effect=run), self.assertRaisesRegex(ValueError, "Draft changed"):
            lab.publish(self.manifest["tag"], "e" * 64)

    def test_read_failure_is_never_treated_as_empty_release_history(self):
        failed = mock.Mock(returncode=1, stderr="HTTP 403: permission denied")
        with mock.patch.object(lab.subprocess, "run", return_value=failed), self.assertRaises(RuntimeError):
            lab.check_order(self.manifest)


if __name__ == "__main__":
    unittest.main()
