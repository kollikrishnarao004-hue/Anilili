#!/usr/bin/env python3
"""Create/reuse the permanent Lab key outside Git and configure fork Actions secrets."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import secrets
import subprocess

REPO = "kollikrishnarao004-hue/Anilili-Lab-Releases"
ROOT = Path(__file__).resolve().parents[1]
STORE = Path.home() / ".local/share/anilili-lab-signing"


def main() -> None:
    os.umask(0o077)
    STORE.mkdir(mode=0o700, parents=True, exist_ok=True)
    STORE.chmod(0o700)
    credentials = STORE / "credentials.json"
    keystore = STORE / "anilili-lab.jks"
    if credentials.exists() != keystore.exists():
        raise RuntimeError("Incomplete signing material; restore the original backup instead of rotating the key")
    if not keystore.exists():
        config = {"storePassword": secrets.token_urlsafe(36), "keyPassword": secrets.token_urlsafe(36), "keyAlias": "anilili-lab"}
        env = {**os.environ, "LAB_STORE_PASS": config["storePassword"], "LAB_KEY_PASS": config["keyPassword"]}
        subprocess.run(["keytool", "-genkeypair", "-noprompt", "-storetype", "JKS", "-keystore", str(keystore),
                        "-alias", config["keyAlias"], "-keyalg", "RSA", "-keysize", "4096", "-validity", "10000",
                        "-dname", "CN=Anilili Lab", "-storepass:env", "LAB_STORE_PASS", "-keypass:env", "LAB_KEY_PASS"],
                       env=env, check=True, capture_output=True)
        credentials.write_text(json.dumps(config, indent=2) + "\n")
    config = json.loads(credentials.read_text())
    for file in (keystore, credentials):
        file.chmod(0o600)
    env = {**os.environ, "LAB_STORE_PASS": config["storePassword"]}
    certificate = subprocess.check_output(["keytool", "-list", "-v", "-keystore", str(keystore),
                                          "-alias", config["keyAlias"], "-storepass:env", "LAB_STORE_PASS"], env=env, text=True)
    fingerprint = re.search(r"SHA256: ([0-9A-F:]+)", certificate).group(1).replace(":", "").lower()
    public = ROOT / "signing-certificate.sha256"
    if public.exists() and public.read_text().strip() != fingerprint:
        raise RuntimeError("Existing signing certificate differs; refusing to replace the permanent key")
    public.write_text(fingerprint + "\n")
    for name, value in {
        "LAB_KEYSTORE_BASE64": base64.b64encode(keystore.read_bytes()).decode(),
        "LAB_KEYSTORE_PASSWORD": config["storePassword"],
        "LAB_KEY_ALIAS": config["keyAlias"], "LAB_KEY_PASSWORD": config["keyPassword"],
    }.items():
        subprocess.run(["gh", "secret", "set", name, "--repo", REPO], input=value, text=True, check=True, capture_output=True)
    print(f"Permanent signing material: {STORE} (keep a secure independent backup)")
    print(f"Public certificate SHA-256: {fingerprint}")
    print("Four signing secrets configured on the private release repository; no private key was written inside the checkout.")


if __name__ == "__main__":
    main()
