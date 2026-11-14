#!/usr/bin/env python3
"""Package and verify exact Lab release bytes. Uses only the Python standard library."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPO = "kollikrishnarao004-hue/Anilili-Lab-Releases"
APP_ID = "com.anilili.lab"
APK = "Anilili-Lab.apk"
MANIFEST = "lab-update.json"


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True, cwd=ROOT).strip()


def version() -> dict:
    props = dict(line.split("=", 1) for line in (ROOT / "version.properties").read_text().splitlines() if "=" in line)
    name, code = props["versionName"], int(props["versionCode"])
    if not re.fullmatch(r"\d+\.\d+\.\d+", name) or not 1 <= code <= 2_100_000_000:
        raise ValueError("Invalid version.properties")
    return {"version": name, "versionCode": code, "tag": f"lab-v{name}-build{code}", "commit": run("git", "rev-parse", "HEAD")}


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def inspect_apk(path: Path, expected: dict) -> str:
    sdk = Path(os.environ.get("ANDROID_HOME", os.environ.get("ANDROID_SDK_ROOT", "")))
    tools = sdk / "build-tools" / "35.0.1"
    badging = run(str(tools / "aapt"), "dump", "badging", str(path.resolve()))
    package = re.search(r"package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", badging)
    if not package or package.groups() != (APP_ID, str(expected["versionCode"]), expected["version"]):
        raise ValueError("APK package/version does not match the release")
    signature = run(str(tools / "apksigner"), "verify", "--verbose", "--print-certs", str(path.resolve()))
    certs = re.findall(r"Signer #\d+ certificate SHA-256 digest: ([a-fA-F0-9]+)", signature)
    expected_cert = (ROOT / "signing-certificate.sha256").read_text().strip().lower()
    if len(certs) != 1 or certs[0].lower() != expected_cert:
        raise ValueError("APK is not signed by the permanent Lab signing certificate")
    return expected_cert


def prepare(apk: Path, output: Path) -> None:
    metadata = version()
    certificate = inspect_apk(apk, metadata)
    output.mkdir(parents=True, exist_ok=True)
    target = output / APK
    shutil.copyfile(apk, target)
    digest = sha256(target)
    manifest = {
        "schemaVersion": 1, "applicationId": APP_ID, **metadata,
        "releaseRepositoryCommit": os.environ.get("LAB_RELEASE_WORKFLOW_SHA", metadata["commit"]),
        "apkUrl": f"https://github.com/{REPO}/releases/download/{metadata['tag']}/{APK}",
        "sizeBytes": target.stat().st_size, "sha256": digest,
        "signerSha256": certificate, "changelog": (ROOT / "release-notes.md").read_text().strip(),
    }
    (output / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "SHA256SUMS").write_text(f"{digest}  {APK}\n{sha256(output / MANIFEST)}  {MANIFEST}\n")
    print(json.dumps(manifest, indent=2))


def verify(directory: Path, tag: str) -> dict:
    manifest = json.loads((directory / MANIFEST).read_text())
    if not re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]):
        raise ValueError("Invalid release version")
    expected_tag = f"lab-v{manifest['version']}-build{manifest['versionCode']}"
    if tag != expected_tag or manifest["tag"] != tag or manifest["applicationId"] != APP_ID or manifest["schemaVersion"] != 1:
        raise ValueError("Release identity mismatch")
    expected_url = f"https://github.com/{REPO}/releases/download/{tag}/{APK}"
    if manifest["apkUrl"] != expected_url or not re.fullmatch(r"[0-9a-f]{40}", manifest["commit"]):
        raise ValueError("Release source mismatch")
    apk = directory / APK
    if apk.stat().st_size != manifest["sizeBytes"] or sha256(apk) != manifest["sha256"]:
        raise ValueError("Release APK hash/size mismatch")
    certificate = inspect_apk(apk, manifest)
    if certificate != manifest["signerSha256"]:
        raise ValueError("Manifest signing certificate mismatch")
    expected_sums = f"{sha256(apk)}  {APK}\n{sha256(directory / MANIFEST)}  {MANIFEST}\n"
    if (directory / "SHA256SUMS").read_text() != expected_sums:
        raise ValueError("Release checksum list mismatch")
    print(f"Verified {tag}: {APP_ID}, signer {certificate}, commit {manifest['commit']}")
    return manifest


def check_order(manifest: dict) -> None:
    # Only 404 means no previous release; auth/network failures must stop publishing.
    result = subprocess.run(["gh", "api", f"repos/{REPO}/releases/latest"], text=True, capture_output=True)
    if result.returncode:
        if "(HTTP 404)" in result.stderr:
            return
        raise RuntimeError("Cannot inspect previous release: " + result.stderr)
    previous = json.loads(result.stdout)
    with tempfile.TemporaryDirectory() as temp:
        run("gh", "release", "download", previous["tag_name"], "--repo", REPO, "--pattern", MANIFEST, "--dir", temp)
        older = json.loads((Path(temp) / MANIFEST).read_text())
    old_name = tuple(map(int, older["version"].split(".")))
    new_name = tuple(map(int, manifest["version"].split(".")))
    if manifest["versionCode"] <= older["versionCode"] or new_name < old_name:
        raise ValueError("Publication must increase versionCode and must not decrease versionName")


def publish(tag: str, expected_manifest_sha256: str) -> None:
    if not re.fullmatch(r"lab-v\d+\.\d+\.\d+-build\d+", tag):
        raise ValueError("Invalid Lab release tag")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256):
        raise ValueError("The reviewed manifest SHA-256 is required")
    # Draft tags do not exist as git refs yet; the REST /releases/tags endpoint returns 404.
    # gh release view resolves the owner's draft through the release listing instead.
    release = json.loads(run("gh", "release", "view", tag, "--repo", REPO,
                             "--json", "isDraft,isPrerelease,targetCommitish,tagName"))
    if release["tagName"] != tag or not release["isDraft"] or release["isPrerelease"]:
        raise ValueError("Only a prepared Lab draft can be published")
    with tempfile.TemporaryDirectory() as temp:
        run("gh", "release", "download", tag, "--repo", REPO, "--dir", temp,
            "--pattern", APK, "--pattern", MANIFEST, "--pattern", "SHA256SUMS")
        if sha256(Path(temp) / MANIFEST) != expected_manifest_sha256:
            raise ValueError("Draft changed since review; approve its exact manifest hash before publication")
        manifest = verify(Path(temp), tag)
        if release["targetCommitish"] != manifest["releaseRepositoryCommit"]:
            raise ValueError("Draft target commit does not match the built APK manifest")
        check_order(manifest)
    # This is the sole step that advances /releases/latest/download for phones.
    run("gh", "release", "edit", tag, "--repo", REPO, "--draft=false", "--latest")
    print(f"Published https://github.com/{REPO}/releases/tag/{tag}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    v = commands.add_parser("version")
    v.add_argument("--github-output", type=Path)
    p = commands.add_parser("prepare")
    p.add_argument("--apk", type=Path, required=True)
    p.add_argument("--output", type=Path, default=ROOT / "build/lab-release")
    v = commands.add_parser("verify")
    v.add_argument("--directory", type=Path, required=True)
    v.add_argument("--tag", required=True)
    p = commands.add_parser("publish")
    p.add_argument("--tag", required=True)
    p.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    if args.command == "version":
        metadata = version()
        print(json.dumps(metadata))
        if args.github_output:
            with args.github_output.open("a") as output:
                for key, value in metadata.items():
                    output.write(f"{key}={value}\n")
    elif args.command == "prepare":
        prepare(args.apk.resolve(), args.output.resolve())
    elif args.command == "verify":
        verify(args.directory.resolve(), args.tag)
    else:
        publish(args.tag, args.expected_manifest_sha256)


if __name__ == "__main__":
    main()
