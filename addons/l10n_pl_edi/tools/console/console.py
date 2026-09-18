#!/usr/bin/env python3
# ruff: file-ignore[print]

import base64
import hashlib
import json
import logging
import os
import re
import sys
import time
import subprocess
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import ec, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from lxml import etree

try:
    import readline
except ImportError:
    readline = None

_logger = logging.getLogger(__name__)
TIMEOUT = 30
AUTH_TIMEOUT = 90
MB = 2 ** 20


# -----------------------------------------------------------------------------
# Custom Exceptions
# -----------------------------------------------------------------------------
class KSeFRateLimitError(Exception):
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class KSeFAPIError(Exception):
    pass


# -----------------------------------------------------------------------------
# Cryptography & XAdES Helpers
# -----------------------------------------------------------------------------
def b64(value):
    return base64.b64encode(value).decode()


def get_hash(value_bytes):
    return base64.b64encode(hashlib.sha256(value_bytes).digest()).decode()


def extract_nip_from_cert(filename):
    content = Path(filename).expanduser().absolute().read_bytes()
    cert = x509.load_pem_x509_certificate(content)
    subject_str = cert.subject.rfc4514_string()
    if nip_match := re.search(r"(?:TINPL|NIP)-?(\d{10})", subject_str):
        return nip_match.group(1)
    raise ValueError(f"Could not extract NIP from certificate: {filename}")


def der_to_p1363(der_bytes, curve_size=32):
    idx = 2
    assert der_bytes[idx] == 0x02
    r_len = der_bytes[idx + 1]
    r_bytes = der_bytes[idx + 2 : idx + 2 + r_len]
    idx += 2 + r_len

    assert der_bytes[idx] == 0x02
    s_len = der_bytes[idx + 1]
    s_bytes = der_bytes[idx + 2 : idx + 2 + s_len]

    r_int = int.from_bytes(r_bytes, byteorder="big")
    s_int = int.from_bytes(s_bytes, byteorder="big")

    return r_int.to_bytes(curve_size, byteorder="big") + s_int.to_bytes(
        curve_size, byteorder="big"
    )


def generate_xades_xml(challenge_str, nip, cert_path, key_path, password=None):
    cert_bytes = Path(cert_path).expanduser().absolute().read_bytes()
    key_bytes = Path(key_path).expanduser().absolute().read_bytes()

    if isinstance(password, str):
        password = password.encode("utf-8")

    cert = x509.load_pem_x509_certificate(cert_bytes)
    private_key = serialization.load_pem_private_key(key_bytes, password=password)

    cert_der = cert.public_bytes(serialization.Encoding.DER)
    cert_b64 = base64.b64encode(cert_der).decode()
    cert_digest = base64.b64encode(hashlib.sha256(cert_der).digest()).decode()

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    doc_raw = (
        f'<AuthTokenRequest xmlns="http://ksef.mf.gov.pl/auth/token/2.0">'
        f"<Challenge>{challenge_str}</Challenge>"
        f"<ContextIdentifier><Nip>{nip}</Nip></ContextIdentifier>"
        f"<SubjectIdentifierType>certificateSubject</SubjectIdentifierType>"
        f"</AuthTokenRequest>"
    )
    doc_elem = etree.fromstring(doc_raw.encode("utf-8"))
    doc_c14n = etree.tostring(doc_elem, method="c14n", exclusive=True)
    doc_digest = base64.b64encode(hashlib.sha256(doc_c14n).digest()).decode()

    sp_raw = (
        f'<xades:SignedProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" '
        f'xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="SignedProperties">'
        f"<xades:SignedSignatureProperties>"
        f"<xades:SigningTime>{now_iso}</xades:SigningTime>"
        f"<xades:SigningCertificate>"
        f"<xades:Cert>"
        f"<xades:CertDigest>"
        f'<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>'
        f"<ds:DigestValue>{cert_digest}</ds:DigestValue>"
        f"</xades:CertDigest>"
        f"<xades:IssuerSerial>"
        f"<ds:X509IssuerName>{cert.issuer.rfc4514_string()}</ds:X509IssuerName>"
        f"<ds:X509SerialNumber>{cert.serial_number}</ds:X509SerialNumber>"
        f"</xades:IssuerSerial>"
        f"</xades:Cert>"
        f"</xades:SigningCertificate>"
        f"</xades:SignedSignatureProperties>"
        f"</xades:SignedProperties>"
    )
    sp_elem = etree.fromstring(sp_raw.encode("utf-8"))
    sp_c14n = etree.tostring(sp_elem, method="c14n", exclusive=True)
    props_digest = base64.b64encode(hashlib.sha256(sp_c14n).digest()).decode()

    si_raw = (
        f'<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">'
        f'<ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        f'<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"/>'
        f'<ds:Reference URI="">'
        f"<ds:Transforms>"
        f'<ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>'
        f'<ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        f"</ds:Transforms>"
        f'<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>'
        f"<ds:DigestValue>{doc_digest}</ds:DigestValue>"
        f"</ds:Reference>"
        f'<ds:Reference URI="#SignedProperties" Type="http://uri.etsi.org/01903#SignedProperties">'
        f"<ds:Transforms>"
        f'<ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        f"</ds:Transforms>"
        f'<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>'
        f"<ds:DigestValue>{props_digest}</ds:DigestValue>"
        f"</ds:Reference>"
        f"</ds:SignedInfo>"
    )
    si_elem = etree.fromstring(si_raw.encode("utf-8"))
    si_c14n = etree.tostring(si_elem, method="c14n", exclusive=True)

    der_signature = private_key.sign(si_c14n, ec.ECDSA(hashes.SHA256()))
    raw_signature = der_to_p1363(der_signature)
    sig_b64 = base64.b64encode(raw_signature).decode()

    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<AuthTokenRequest xmlns="http://ksef.mf.gov.pl/auth/token/2.0">'
        f"<Challenge>{challenge_str}</Challenge>"
        f"<ContextIdentifier><Nip>{nip}</Nip></ContextIdentifier>"
        f"<SubjectIdentifierType>certificateSubject</SubjectIdentifierType>"
        f'<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="Signature">'
        f'{si_c14n.decode("utf-8")}'
        f"<ds:SignatureValue>{sig_b64}</ds:SignatureValue>"
        f"<ds:KeyInfo>"
        f"<ds:X509Data>"
        f"<ds:X509Certificate>{cert_b64}</ds:X509Certificate>"
        f"</ds:X509Data>"
        f"</ds:KeyInfo>"
        f"<ds:Object>"
        f'<xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Target="#Signature">'
        f'{sp_c14n.decode("utf-8")}'
        f"</xades:QualifyingProperties>"
        f"</ds:Object>"
        f"</ds:Signature>"
        f"</AuthTokenRequest>"
    )


# -----------------------------------------------------------------------------
# Standalone KSeF API Service
# -----------------------------------------------------------------------------
class KsefApiService:
    def __init__(self, mode="test", cache_dir="."):
        assert mode != "prod"  # FFS, dont use in production

        self.script_dir = Path(__file__).resolve().parent
        self.cert_dir = self.script_dir.parent.parent / "tests" / "certificate"
        self.cert_path = self.cert_dir / "l10n_pl_edi_test.pem"
        self.key_path = self.cert_dir / "l10n_pl_edi_test.key"

        self.mode = mode
        self.api_url = (
            "https://api.ksef.mf.gov.pl/v2"
            if mode == "prod"
            else "https://api-test.ksef.mf.gov.pl/v2"
        )
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / ".ksef_app_cache.json"
        self.load_cache()

    def save_cache(self):
        data = {
            "access_token": self.access_token,
            "vat_whitelist": str(self.vat_whitelist),
            "refresh_token": self.refresh_token,
            "session_id": self.session_id,
            "raw_symmetric_key_b64": b64(self.raw_symmetric_key) if self.raw_symmetric_key else None,
            "raw_iv_b64": b64(self.raw_iv) if self.raw_iv else None,
            "export_symmetric_key_b64": b64(self.export_symmetric_key) if self.export_symmetric_key else None,
            "export_iv_b64": b64(self.export_iv) if self.export_iv else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "nip": extract_nip_from_cert(self.cert_path),
            "script_dir": str(self.script_dir),
            "cert_dir": str(self.cert_dir),
            "cert_path": str(self.cert_path),
            "key_path": str(self.key_path),
        }
        self.cache_file.write_text(json.dumps(data, indent=2))

    def load_cache(self):
        self.clear_cache()
        if not self.cache_file.exists():
            return
        data = json.loads(self.cache_file.read_text())
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")
        self.session_id = data.get("session_id")
        self.nip = data.get("nip")
        if vat_whitelist := data.get("vat_whitelist"):
            self.vat_whitelist = Path(vat_whitelist)
        if data.get("raw_symmetric_key_b64"):
            self.raw_symmetric_key = base64.b64decode(data["raw_symmetric_key_b64"])
        if data.get("raw_iv_b64"):
            self.raw_iv = base64.b64decode(data["raw_iv_b64"])
        if data.get("export_symmetric_key_b64"):
            self.export_symmetric_key = base64.b64decode(data["export_symmetric_key_b64"])
        if data.get("export_iv_b64"):
            self.export_iv = base64.b64decode(data["export_iv_b64"])

    def read_cache_text(self):
        if not self.cache_file.exists():
            return None
        return self.cache_file.read_text()

    def clear_cache(self):
        self.access_token = None
        self.refresh_token = None
        self.session_id = None
        self.raw_symmetric_key = None
        self.raw_iv = None
        self.batch_reference = None
        self.export_symmetric_key = None
        self.export_iv = None
        self.vat_whitelist = None

    def _make_headers(self, token=None):
        headers = {"Content-Type": "application/json"}
        auth_token = token or self.access_token
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        return headers

    def _execute_network_request(self, method, endpoint, **kwargs):
        try:
            return requests.request(method, endpoint, **kwargs)
        except requests.exceptions.RequestException as e:
            error_text = e.response.text if e.response is not None else str(e)
            _logger.exception("KSeF API request failed: %s", error_text)
            raise KSeFAPIError(f"KSeF API Request Error: {error_text}") from e

    def _make_request(self, method, endpoint, is_auth_retry=False, **kwargs):
        kwargs.setdefault("headers", {})
        kwargs.setdefault("timeout", TIMEOUT)

        if "Authorization" not in kwargs["headers"] and self.access_token:
            kwargs["headers"].update(self._make_headers())

        response = self._execute_network_request(method, endpoint, **kwargs)

        if response.status_code == 401 and not is_auth_retry:
            self.refresh_access_token()
            kwargs["headers"].update(self._make_headers())
            return self._make_request(method, endpoint, is_auth_retry=True, **kwargs)

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After") or "5"
            raise KSeFRateLimitError("Too Many Requests", retry_after=retry_after)

        if not response.ok:
            raise KSeFAPIError(f"KSeF Error [{response.status_code}]: {response.text}")

        return response

    def fetch_public_keys(self):
        certs_data = self._make_request(
            "GET",
            f"{self.api_url}/security/public-key-certificates",
            headers={"Accept": "application/json"},
        ).json()

        public_keys = {"symmetric": None, "token": None}
        for cert_info in certs_data:
            usage = cert_info.get("usage", [])
            if not set(usage) & {"SymmetricKeyEncryption", "KsefTokenEncryption"}:
                continue

            cert_der = base64.b64decode(cert_info["certificate"])
            cert = x509.load_der_x509_certificate(cert_der)
            public_key_pem = cert.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()

            if "SymmetricKeyEncryption" in usage:
                public_keys["symmetric"] = public_key_pem
            if "KsefTokenEncryption" in usage:
                public_keys["token"] = public_key_pem

        if not public_keys["symmetric"] or not public_keys["token"]:
            raise KSeFAPIError("Could not find required KSeF public keys.")
        return public_keys

    def open_ksef_session(self):
        if self.session_id:
            status = self.get_session_status()
            if status.get("status", {}).get("code") == 100:
                return self.session_id

        self.raw_symmetric_key = os.urandom(32)
        self.raw_iv = os.urandom(16)

        ksef_public_key_pem = self.fetch_public_keys().get("symmetric")
        public_key = serialization.load_pem_public_key(ksef_public_key_pem.encode())
        encrypted_symmetric_key = public_key.encrypt(
            self.raw_symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        response = self._make_request(
            "POST",
            f"{self.api_url}/sessions/online",
            headers={"Content-Type": "application/json"},
            json={
                "formCode": {
                    "systemCode": "FA (3)",
                    "schemaVersion": "1-0E",
                    "value": "FA",
                },
                "encryption": {
                    "encryptedSymmetricKey": b64(encrypted_symmetric_key),
                    "initializationVector": b64(self.raw_iv),
                },
            },
        ).json()

        self.session_id = response.get("referenceNumber")
        self.save_cache()
        return self.session_id

    def close_ksef_session(self):
        if not self.session_id:
            raise KSeFAPIError("No active online session reference found.")

        endpoint = f"{self.api_url}/sessions/online/{self.session_id}/close"
        self._make_request("POST", endpoint)

        self.session_id = None
        self.raw_symmetric_key = None
        self.raw_iv = None
        self.batch_reference = None
        self.export_symmetric_key = None
        self.export_iv = None
        self.save_cache()

        for path in Path(".").glob("*.zip*"):
            path.unlink(missing_ok=True)

    def get_session_status(self):
        if not self.session_id:
            raise KSeFAPIError("No active KSeF session found.")
        return self._make_request("GET", f"{self.api_url}/sessions/{self.session_id}").json()

    def get_challenge(self):
        return self._make_request("POST", f"{self.api_url}/auth/challenge").json()

    def authenticate_xades(self, signed_xml):
        data = signed_xml.encode("utf-8") if isinstance(signed_xml, str) else signed_xml
        return self._make_request(
            "POST",
            f"{self.api_url}/auth/xades-signature",
            data=data,
            headers={"Content-Type": "application/xml"},
            timeout=AUTH_TIMEOUT,
        ).json()

    def check_auth_status(self, ref_number, temp_token):
        endpoint = f"{self.api_url}/auth/{ref_number}"
        headers = self._make_headers(temp_token)

        for _ in range(30):
            response_data = self._make_request("GET", endpoint, headers=headers).json()
            status_code = response_data.get("status", {}).get("code")

            if status_code == 200:
                return response_data
            if status_code != 100:
                raise KSeFAPIError(f"KSeF Auth failed [{status_code}]")
            time.sleep(2)

        raise KSeFAPIError("KSeF Authentication timed out.")

    def redeem_token(self, temp_token):
        endpoint = f"{self.api_url}/auth/token/redeem"
        headers = {
            "Authorization": f"Bearer {temp_token}",
            "Accept": "application/json",
        }
        response = self._make_request("POST", endpoint, headers=headers).json()

        self.access_token = response.get("accessToken", {}).get("token")
        self.refresh_token = response.get("refreshToken", {}).get("token")
        if self.access_token:
            self.save_cache()

        return response

    def refresh_access_token(self):
        if not hasattr(self, "refresh_token") or not self.refresh_token:
            self.access_token = None
            self.refresh_token = None
            self.save_cache()
            raise KSeFAPIError("No refresh token available. Please re-authenticate.")

        endpoint = f"{self.api_url}/auth/refresh"
        headers = {"Authorization": f"Bearer {self.refresh_token}"}
        resp = requests.post(endpoint, headers=headers, timeout=TIMEOUT)

        if resp.status_code == 200:
            data = resp.json()
            self.access_token = data.get("token")
            self.save_cache()
            return self.access_token

        self.access_token = None
        self.refresh_token = None
        self.save_cache()
        raise KSeFAPIError("Refresh token expired. Please re-authenticate.")

    def get_request_download_batch(self, date_from, date_to, subject_type="Subject1"):
        endpoint = f"{self.api_url}/invoices/exports"

        raw_symmetric_key = os.urandom(32)
        raw_iv = os.urandom(16)

        ksef_public_key_pem = self.fetch_public_keys().get("symmetric")
        public_key = serialization.load_pem_public_key(ksef_public_key_pem.encode())
        encrypted_symmetric_key = public_key.encrypt(
            raw_symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        self.export_symmetric_key = raw_symmetric_key
        self.export_iv = raw_iv

        json_data = {
            "encryption": {
                "encryptedSymmetricKey": b64(encrypted_symmetric_key),
                "initializationVector": b64(raw_iv),
            },
            "filters": {
                "subjectType": subject_type,
                "dateRange": {
                    "from": date_from.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "to": date_to.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "dateType": "Invoicing",
                },
            },
        }
        print(f"get_request_download_batch: {json.dumps(json_data, indent=4)}")
        res = self._make_request("POST", endpoint, json=json_data).json()
        self.batch_reference = res.get("referenceNumber")
        self.save_cache()
        return res

    def save_batch_metadata_file(self, batch_ref, status_response):
        """Saves the status response containing part details to <batch_ref>.json."""
        if not batch_ref:
            return None
        meta_file = Path(".") / f"{batch_ref}.json"
        meta_file.write_text(json.dumps(status_response, indent=2))
        return meta_file

    def get_batch_status(self, batch_reference):
        return self._make_request("GET", f"{self.api_url}/invoices/exports/{batch_reference}").json()

    def stream_download_part(self, download_url, dest_path, chunk_size=MB, break_at_byte=0):
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        downloaded_bytes = dest_path.stat().st_size if dest_path.exists() else 0

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        # Fetch total content length using GET headers if HEAD fails
        total_bytes = 0
        head_headers = headers.copy()
        head_resp = requests.head(download_url, headers=head_headers, timeout=10)
        if head_resp.status_code in (200, 206):
            total_bytes = int(head_resp.headers.get("content-length", 0))
            if downloaded_bytes > 0 and "Content-Range" in head_resp.headers:
                # Content-Range format: "bytes 1000-4999/5000"
                total_bytes = int(head_resp.headers.get("Content-Range").split("/")[-1])

        # Apply Range header for actual payload streaming (resume support)
        if downloaded_bytes > 0:
            headers["Range"] = f"bytes={downloaded_bytes}-"

        response = requests.get(download_url, headers=headers, stream=True, timeout=30)

        if response.status_code == 416:
            return downloaded_bytes, True
        if response.status_code not in (200, 206):
            raise KSeFAPIError(f"Download failed ({response.status_code}): {response.text}")

        # Extract total_bytes if absent from HEAD
        if total_bytes == 0 and "content-length" in response.headers:
            total_bytes = downloaded_bytes + int(response.headers["content-length"])

        mode = "ab" if response.status_code == 206 else "wb"
        if response.status_code == 200:
            downloaded_bytes = 0

        print("  └ Initiating data stream...", flush=True)

        stream_start = time.perf_counter()
        session_start_bytes = downloaded_bytes

        with dest_path.open(mode) as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded_bytes += len(chunk)

                # Performance & Bandwidth Calculations
                elapsed = max(time.perf_counter() - stream_start, 0.001)
                bytes_this_session = downloaded_bytes - session_start_bytes
                speed_mbps = (bytes_this_session / MB) / elapsed
                ram_mb = get_process_memory_mb()

                if total_bytes > 0:
                    pct = min(100.0, (downloaded_bytes / total_bytes) * 100)
                    dots_count = int((pct / 100) * 30)
                    dots = "." * dots_count
                    spaces = " " * (30 - dots_count)

                    remaining_bytes = max(total_bytes - downloaded_bytes, 0)
                    eta_sec = (remaining_bytes / MB) / speed_mbps if speed_mbps > 0 else 0

                    sys.stdout.write(
                        f"\r  └ Progress: [{dots}{spaces}] {pct:5.1f}% "
                        f"({downloaded_bytes / MB:6.1f} / {total_bytes / MB:6.1f} MB) "
                        f"[{speed_mbps:5.2f} MB/s | ETA: {eta_sec:4.0f}s | RAM: {ram_mb:5.1f} MB]"
                    )
                else:
                    sys.stdout.write(
                        f"\r  └ Downloaded: {downloaded_bytes / MB:6.1f} MB... "
                        f"[{speed_mbps:5.2f} MB/s | RAM: {ram_mb:5.1f} MB]"
                    )
                sys.stdout.flush()

                if break_at_byte > 0 and downloaded_bytes >= break_at_byte:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    raise KSeFAPIError(f"Simulated break reached at {downloaded_bytes} bytes")

            sys.stdout.write("\n")
            sys.stdout.flush()
            return downloaded_bytes, False


# -----------------------------------------------------------------------------
# General Helpers
# -----------------------------------------------------------------------------
def setup_readline_completer(options):
    if not readline:
        return

    def completer(text, state):
        matches = [opt for opt in options if opt.startswith(text)]
        if state < len(matches):
            return matches[state]
        return None

    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")


def select_batch_folder_or_file(service, items, prompt_label="Select item", default_item=None):
    """
    Generic interactive prompt supporting numbers and readline tab-completion.
    'items' should be a list of strings (folder names or batch prefixes).
    """
    if not items:
        return None

    sorted_items = sorted(items)

    if not default_item or default_item not in sorted_items:
        default_item = sorted_items[0]

    print(f"\n--- Available {prompt_label}s ---")
    for idx, item in enumerate(sorted_items, 1):
        marker = " (default)" if item == default_item else ""
        print(f" {idx:>2}. {item}{marker}")

    setup_readline_completer(sorted_items)
    try:
        user_input = input(f"\n{prompt_label} number or type name [{default_item}]: ").strip()
    finally:
        if readline:
            readline.set_completer(None)

    if not user_input:
        return default_item
    elif user_input.isdigit() and 1 <= int(user_input) <= len(sorted_items):
        return sorted_items[int(user_input) - 1]

    return user_input


def discover_disk_batch_references():
    """
    Scans working directory for batch metadata JSONs and returns ONLY those
    that have missing or incomplete part files (*-001.zip.aes).
    Fully downloaded parts, merged .zip.aes, decrypted .zip, or unpacked directories
    are explicitly excluded.
    """
    pending_batches = set()
    chunk_pattern = r"-\d{3,}\.zip\.aes$"

    for json_file in Path(".").glob("*.json"):
        if json_file.name.startswith("."):
            continue

        batch_ref = json_file.stem

        # Hard stop if batch moved to next pipeline stages
        if (Path(".") / f"{batch_ref}.zip.aes").exists() or \
           (Path(".") / f"{batch_ref}.zip").exists() or \
           (Path(".") / batch_ref).is_dir():
            continue

        try:
            meta = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        parts = meta.get("package", {}).get("parts", [])
        if not parts:
            continue

        is_incomplete = False
        for part in parts:
            part_name = part.get("partName")
            expected_size = part.get("partSize") or part.get("plainPartSize")
            if not part_name:
                continue

            local_part = Path(".") / part_name

            # If part file doesn't exist or is an empty 0-byte placeholder
            if not local_part.exists():
                is_incomplete = True
                break

            local_size = local_part.stat().st_size
            if local_size == 0:
                is_incomplete = True
                break

            # If KSeF specified expected size, ensure we reached it
            if expected_size is not None and local_size < expected_size:
                is_incomplete = True
                break

        if is_incomplete:
            pending_batches.add(batch_ref)

    # Fallback: catch unmerged orphan chunks without JSON metadata
    for path in Path(".").glob("*.zip.aes"):
        if re.search(chunk_pattern, path.name):
            batch_ref = re.sub(chunk_pattern, "", path.name)
            zip_file = Path(".") / f"{batch_ref}.zip"
            zip_aes = Path(".") / f"{batch_ref}.zip.aes"
            unpacked_dir = Path(".") / batch_ref

            # Include only if the chunk itself is empty (0 bytes) and batch isn't finished
            if path.stat().st_size == 0 and not zip_file.exists() and not zip_aes.exists() and not unpacked_dir.is_dir():
                pending_batches.add(batch_ref)

    return sorted(pending_batches)


# -----------------------------------------------------------------------------
# Action Functions
# -----------------------------------------------------------------------------
def action_print_cache(service):
    content = service.read_cache_text()
    if not content:
        print("\n[!] Unified cache file does not exist.")
        return
    print(f"\n=== Consolidated Cache File: {service.cache_file.name} ===")
    print(content)


def action_clear_cache(service):
    service.clear_cache()
    print("\n[+] Unified cache file cleared successfully.")


def action_get_token(service, cert_path, key_path, password):
    print("\n[+] Starting full KSeF XAdES authentication...")
    nip = extract_nip_from_cert(cert_path)
    challenge_resp = service.get_challenge()
    challenge = challenge_resp.get("challenge")

    print(f"  └ NIP: {nip} | Challenge: {challenge}")
    signed_xml = generate_xades_xml(challenge, nip, cert_path, key_path, password)

    auth_resp = service.authenticate_xades(signed_xml)
    ref_num = auth_resp.get("referenceNumber")
    temp_token = auth_resp.get("authenticationToken", {}).get("token")

    print(f"  └ Auth Requested (Ref: {ref_num}). Waiting for approval...")
    service.check_auth_status(ref_num, temp_token)

    print("  └ Redeeming session token...")
    service.redeem_token(temp_token)
    print("-> Authentication successful! Access token saved to cache.")


def action_start_session(service):
    session_id = service.open_ksef_session()
    print(f"\n[+] Online Session Ready: {session_id}")


def action_close_session(service):
    service.close_ksef_session()
    print("\n[+] Session closed and local file artifacts (.zip, .zip.aes) purged.")


def action_refresh_token(service):
    service.refresh_access_token()
    print("\n[+] Access token successfully refreshed.")


def action_ask_invoices(service, days_back_default=30):
    if not service.access_token:
        print("\n[!] Access token required. Authenticate first.")
        return

    days_str = input(f"Enter days back for search range [{days_back_default}]: ").strip()
    days_back = int(days_str) if days_str.isdigit() else days_back_default

    current_to = datetime.now(timezone.utc)
    current_from = current_to - timedelta(days=days_back)

    print(f"\n[+] Requesting Invoice Batch Export ({current_from.date()} to {current_to.date()})...")
    export_resp = service.get_request_download_batch(current_from, current_to)

    batch_ref = export_resp.get("referenceNumber")
    print(f"-> Batch Requested! Reference Number: {batch_ref}")

    print("[+] Polling KSeF for batch generation status...")
    for _ in range(12):
        status_resp = service.get_batch_status(batch_ref)
        code = status_resp.get("status", {}).get("code")
        if code == 200:
            print("-> Batch export ready on KSeF!")
            meta_file = service.save_batch_metadata_file(batch_ref, status_resp)
            if meta_file:
                print(f"  └ Saved batch metadata: {meta_file.name}")

            parts = status_resp.get("package", {}).get("parts", [])
            for part in parts:
                empty_file = Path(".") / part["partName"]
                if not empty_file.exists():
                    empty_file.touch()
                    print(f"  └ Created placeholder file on disk: {empty_file.name}")
            return
        if code == 100:
            print("  └ Batch build in progress (Status 100). Waiting 5s...")
            time.sleep(5)
        else:
            print(f"[!] Batch creation failed with status {code}: {status_resp}")
            return
    print("[!] Batch generation timed out on KSeF.")


def action_download_parts(service):
    disk_batches = discover_disk_batch_references()

    if not disk_batches:
        print("\n[!] No pending or incomplete batch downloads found.")
        return

    selected_batch = select_batch_folder_or_file(
        service,
        items=disk_batches,
        prompt_label="Batch Reference to Download",
        default_item=service.batch_reference if service.batch_reference in disk_batches else disk_batches[0],
    )

    if not selected_batch:
        return

    service.batch_reference = selected_batch
    status_resp = service.get_batch_status(service.batch_reference)
    if status_resp.get("status", {}).get("code") != 200:
        print(f"\n[!] Batch not ready yet. Status: {status_resp.get('status')}")
        return

    meta_file = service.save_batch_metadata_file(service.batch_reference, status_resp)
    if meta_file:
        print(f"\n[+] Saved batch metadata file: {meta_file.name}")

    break_str = input("Enter byte count threshold to trigger break (0 = don't break, finish download): ").strip()
    break_at_byte = int(break_str) if break_str.isdigit() else 0

    parts = status_resp.get("package", {}).get("parts", [])
    for part in parts:
        part_name = part["partName"]
        part_url = part["url"]
        enc_file = Path(".") / part_name

        print(f"\n  └ Streaming download for part: {enc_file.name}")
        try:
            downloaded_bytes, is_complete = service.stream_download_part(
                part_url, enc_file, break_at_byte=break_at_byte
            )
            if is_complete:
                print("  └ Local chunk already fully downloaded.")
            else:
                print(f"  └ Downloaded {downloaded_bytes} bytes successfully.")
        except KSeFAPIError as err:
            if "403" not in str(err) and "AuthenticationFailed" not in str(err):
                print(f"  └ Stopped: {err}")
                return
            print("  └ SAS URL expired. Fetching fresh status...")
            fresh_status = service.get_batch_status(service.batch_reference)
            service.save_batch_metadata_file(service.batch_reference, fresh_status)
            fresh_part = next(p for p in fresh_status["package"]["parts"] if p["partName"] == part_name)
            downloaded_bytes, _ = service.stream_download_part(
                fresh_part["url"], enc_file, break_at_byte=break_at_byte
            )
            print(f"  └ Downloaded {downloaded_bytes} bytes successfully.")


def action_concatenate_parts(service):
    pattern = r"-\d{3,}\.zip\.aes$"
    all_part_files = [p for p in Path(".").glob("*.zip.aes") if re.search(pattern, p.name)]

    if not all_part_files:
        print("\n[!] No chunked part files (*-001.zip.aes) found to concatenate.")
        return

    batch_prefixes = sorted({re.sub(pattern, "", p.name) for p in all_part_files})

    selected_batch = select_batch_folder_or_file(
        service,
        items=batch_prefixes,
        prompt_label="Batch to Concatenate",
        default_item=service.batch_reference if service.batch_reference in batch_prefixes else None,
    )

    if not selected_batch:
        print("\n[!] No batch selected.")
        return

    matching_parts = [p for p in all_part_files if p.name.startswith(selected_batch)]

    if not matching_parts:
        print(f"\n[!] No part files found matching selection '{selected_batch}'.")
        return

    sorted_parts = sorted(
        matching_parts,
        key=lambda p: int(re.search(r"-(\d+)\.zip\.aes$", p.name).group(1)),
    )

    combined_file = Path(".") / f"{selected_batch}.zip.aes"

    print(f"\n[+] Concatenating {len(sorted_parts)} parts into: {combined_file.name}")
    try:
        with combined_file.open("wb") as outfile:
            for part in sorted_parts:
                print(f"  └ Appending: {part.name} ({part.stat().st_size} bytes)")
                outfile.write(part.read_bytes())

        for part in sorted_parts:
            part.unlink(missing_ok=True)

        print(f"-> Concatenation complete! Combined archive size: {combined_file.stat().st_size} bytes")
    except OSError as err:
        print(f"[!] File I/O error during concatenation: {err}")


def action_decrypt_parts(service):
    if not service.export_symmetric_key or not service.export_iv:
        print("\n[!] AES symmetric key/IV missing from session cache.")
        return

    chunk_pattern = r"-\d{3,}\.zip\.aes$"
    merged_enc_files = [
        p for p in Path(".").glob("*.zip.aes") if not re.search(chunk_pattern, p.name)
    ]

    if not merged_enc_files:
        print("\n[!] No concatenated .zip.aes archives found to decrypt. Concatenate parts first.")
        return

    batch_names = [p.name.replace(".zip.aes", "") for p in merged_enc_files]
    selected_batch = select_batch_folder_or_file(
        service,
        items=batch_names,
        prompt_label="Batch Archive to Decrypt",
        default_item=service.batch_reference if service.batch_reference in batch_names else batch_names[0],
    )

    if not selected_batch:
        return

    enc_file = Path(".") / f"{selected_batch}.zip.aes"
    zip_file = Path(".") / f"{selected_batch}.zip"

    print(f"\n[+] Decrypting: {enc_file.name} -> {zip_file.name}")
    enc_bytes = enc_file.read_bytes()
    cipher = Cipher(algorithms.AES(service.export_symmetric_key), modes.CBC(service.export_iv))
    unpadder = sym_padding.PKCS7(128).unpadder()
    decryptor = cipher.decryptor()

    try:
        decrypted_padded = decryptor.update(enc_bytes) + decryptor.finalize()
        zip_bytes = unpadder.update(decrypted_padded) + unpadder.finalize()
        zip_file.write_bytes(zip_bytes)
        enc_file.unlink(missing_ok=True)
        print(f"  └ Successfully decrypted & saved archive ({len(zip_bytes)} bytes)")
    except (ValueError, TypeError, OSError) as e:
        print(f"  └ [!] Decryption failed (invalid PKCS7 padding or truncated file): {e}")


def action_unzip_files(service):
    """Prompts the user to select a zip archive, defaulting to the newest file on disk."""
    # Find all .zip files sorted by modification time (latest first)
    zip_paths = sorted(
        [p for p in Path(".").glob("*.zip") if not p.name.startswith(".")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not zip_paths:
        print("\n[!] No .zip archives found to extract.")
        return

    zip_files = [p.name for p in zip_paths]

    selected_zip = select_batch_folder_or_file(
        service,
        items=zip_files,
        prompt_label="Zip Archive to Extract",
        default_item=zip_files[0],  # Defaults to the newest archive
    )

    if not selected_zip:
        return

    archive_path = Path(".") / selected_zip
    target_dir = Path(".") / archive_path.stem

    print(f"\n  └ Extracting {archive_path.name} -> {target_dir.name}/")
    try:
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(target_dir)
        print(f"  └ Successfully extracted batch to {target_dir.name}/")
    except (zipfile.BadZipFile, OSError) as err:
        print(f"  └ Extraction failed: {err}")


def action_prettify_xml_json(service):
    subdirs = [p.name for p in Path(".").iterdir() if p.is_dir() and not p.name.startswith(".")]
    root_json_files = list(Path(".").glob("*.json"))

    if not subdirs and not root_json_files:
        print("\n[!] No subdirectories or JSON metadata files found in current working directory.")
        return

    options = subdirs or ["."]
    default_dir = service.batch_reference if service.batch_reference in subdirs else options[0]

    selected_dir = select_batch_folder_or_file(
        service,
        items=options,
        prompt_label="Folder",
        default_item=default_dir,
    )

    if not selected_dir:
        return

    target_dir = Path(".") / selected_dir
    if not target_dir.exists():
        print(f"\n[!] Target directory '{selected_dir}' does not exist.")
        return

    xml_files = list(target_dir.glob("*.xml"))
    json_files = list(target_dir.glob("*.json"))

    if service.batch_reference:
        root_batch_json = Path(".") / f"{service.batch_reference}.json"
        if root_batch_json.exists() and root_batch_json not in json_files:
            json_files.append(root_batch_json)

    if not xml_files and not json_files:
        print(f"\n[!] No XML or JSON files found in '{selected_dir}'.")
        return

    parser = etree.XMLParser(remove_blank_text=True)
    for xml_file in xml_files:
        try:
            tree = etree.parse(str(xml_file), parser)
            pretty_bytes = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding="utf-8")
            xml_file.write_bytes(pretty_bytes)
            print(f"[+] Prettified XML: {xml_file.name}")
        except (etree.XMLSyntaxError, etree.LxmlError, OSError) as e:
            print(f"[!] Failed to format {xml_file.name}: {e}")

    for json_file in json_files:
        try:
            content = json.loads(json_file.read_text(encoding="utf-8"))
            json_file.write_text(json.dumps(content, indent=2), encoding="utf-8")
            print(f"[+] Prettified JSON: {json_file.name}")
        except (json.JSONDecodeError, OSError) as e:
            print(f"[!] Failed to format {json_file.name}: {e}")


def action_list_directory(service):
    """Prints a clean 'll' style listing matching standard terminal colors."""
    def rgb(text, r, g, b, bold=False):
        style = f"1;38;2;{r};{g};{b}" if bold else f"38;2;{r};{g};{b}"
        return f"\033[{style}m{text}\033[0m"

    cwd = Path(".")
    items = sorted(cwd.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))

    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dec"]

    print()
    for path in items:
        if path.name.startswith("."):
            continue

        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime)
        mtime_str = f"{mtime.day:>2} {months[mtime.month - 1]} {mtime.strftime('%H.%M')}"

        # Standard 'll' coloring: Blue for dirs, Green for executables, default for regular files
        if path.is_dir():
            name = rgb(path.name, 90, 120, 255, bold=True)       # Directory Blue
        elif os.access(path, os.X_OK):
            name = rgb(path.name, 50, 205, 50, bold=True)        # Executable Green
        else:
            name = path.name                                     # Standard file text

        print(f"{stat.st_size:>8} {mtime_str} {name}")


def get_process_memory_mb():
    """Returns current process Resident Set Size (RSS) memory in MB."""
    try:
        import psutil  # ruff: ignore [import-outside-top-level]
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        import resource  # ruff: ignore [import-outside-top-level]
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return usage / 1024 if sys.platform != "darwin" else usage / (1024 * 1024)


def action_download_vat_whitelist(service):
    """
    PHASE 1: Download/Resume Polish VAT Whitelist archive using service.stream_download_part.
    Saves temporary file path metadata into service.cache_file.
    """
    start_time = time.perf_counter()
    today_str = datetime.now().strftime("%Y%m%d")
    url = f"https://plikplaski.mf.gov.pl/pliki/{today_str}.7z"
    temp_archive_path = Path(f"vat_whitelist_flat_{today_str}.json.7z")

    print(f"\n[+] OS Temporary Archive Target: {temp_archive_path.resolve()}")
    print(f"    Initial RAM Usage: {get_process_memory_mb():.1f} MB")

    service.vat_whitelist = temp_archive_path.resolve()
    service.save_cache()

    break_mb_input = input(
        "Enter MB threshold to simulate download break (0 = finish download): "
    ).strip()
    break_at_byte = (int(break_mb_input) * MB) if break_mb_input.isdigit() else 0

    downloaded_bytes = 0
    is_complete = False

    try:
        downloaded_bytes, is_complete = service.stream_download_part(
            download_url=url,
            dest_path=service.vat_whitelist,
            chunk_size=MB,
            break_at_byte=break_at_byte,
        )
    except KSeFAPIError as err:
        elapsed = time.perf_counter() - start_time
        avg_speed = (downloaded_bytes / MB) / max(elapsed, 0.001)
        print(f"\n[!] Download paused/interrupted: {err}")
        print(f"    Progress preserved at: {service.vat_whitelist.name}. Re-run to resume.")
        print(
            f"    Final Stats: {downloaded_bytes / MB:.1f} MB downloaded | "
            f"Avg Speed: {avg_speed:.2f} MB/s | RAM: {get_process_memory_mb():.1f} MB | Elapsed: {elapsed:.2f}s"
        )
        return

    elapsed = time.perf_counter() - start_time
    avg_speed = (downloaded_bytes / MB) / max(elapsed, 0.001)

    if is_complete:
        print(
            f"  └ Archive already fully downloaded ({downloaded_bytes / MB:.1f} MB). "
            f"[RAM: {get_process_memory_mb():.1f} MB] (Took {elapsed:.2f}s)"
        )
    else:
        print(
            f"  └ Phase 1 Complete: Saved {downloaded_bytes / MB:.1f} MB to {service.vat_whitelist.name} "
            f"[{avg_speed:.2f} MB/s | RAM: {get_process_memory_mb():.1f} MB | Elapsed: {elapsed:.2f}s]"
        )


def action_extract_vat_whitelist(service):
    """
    PHASE 2: Extract downloaded local archive line-by-line via 7z,
    splitting records into 3 flat TSV files ready for PostgreSQL COPY.
    """
    start_time = time.perf_counter()

    if not service.vat_whitelist or not service.vat_whitelist.exists():
        print("\n[!] Archive file not found.")
        print("    Run Phase 1 (Download) first.")
        return

    today_str = datetime.now().strftime("%Y%m%d")
    output_dir = Path(f"vat_whitelist_output_{today_str}")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["7z"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except FileNotFoundError:
        print("[!] Error: '7z' executable not found in PATH. Install p7zip / 7-Zip first.")
        return

    print(f"\n[+] Processing archive from disk: {service.vat_whitelist.name}")
    print(f"    Initial RAM Usage: {get_process_memory_mb():.1f} MB")

    proc = subprocess.Popen(
        ["7z", "e", str(service.vat_whitelist), "-so"],
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    open_files = {}
    current_key = "default"
    current_file = None
    line_count = 0

    try:
        for line in proc.stdout:
            line_str = line.strip()

            if ":" in line_str and ("[" in line_str or "array" in line_str.lower()):
                raw_key = line_str.split(":")[0].strip(" '\"{}:")
                if raw_key:
                    current_key = raw_key
                    if current_key not in open_files:
                        target_file = output_dir / f"{current_key}.txt"
                        open_files[current_key] = target_file.open("w", encoding="utf-8")
                        print(f"  └ Initialized text file: {target_file.name}")
                    current_file = open_files[current_key]
                continue

            cleaned_hash = line_str.strip(" '\",[]{}")
            if len(cleaned_hash) >= 32 and current_file:
                current_file.write(f"{cleaned_hash}\n")
                line_count += 1

                if line_count % 100_000 == 0:
                    elapsed = time.perf_counter() - start_time
                    ram_mb = get_process_memory_mb()
                    print(f"  └ Extracted {line_count:,} records... [RAM: {ram_mb:.1f} MB] [Time: {elapsed:.1f}s]")

        proc.wait()

    finally:
        for handle in open_files.values():
            handle.close()

    total_time = time.perf_counter() - start_time
    final_ram = get_process_memory_mb()
    print(
        f"\n[+] Extraction finished! Extracted {line_count:,} total records into: '{output_dir.name}/'\n"
        f"    Final RAM Usage: {final_ram:.1f} MB | Total Time: {total_time:.2f}s"
    )


# -----------------------------------------------------------------------------
# Console Menu Engine using Dictionary Dispatch
# -----------------------------------------------------------------------------
def get_menu_actions(service, cert_path, key_path, password):
    return [
        {"desc": "Print cache JSON", "action": lambda: action_print_cache(service)},
        {"desc": "Download VAT whitelist", "action": lambda: action_download_vat_whitelist(service)},
        {"desc": "Extract VAT whitelist", "action": lambda: action_extract_vat_whitelist(service)},
        {"desc": "Get access token (XAdES Auth)", "action": lambda: action_get_token(service, cert_path, key_path, password)},
        {"desc": "Start session", "action": lambda: action_start_session(service)},
        {"desc": "Ask for invoices (create part placeholders)", "action": lambda: action_ask_invoices(service)},
        {"desc": "Download parts (specify break threshold)", "action": lambda: action_download_parts(service)},
        {"desc": "Concatenate downloaded parts (-nnn.zip.aes -> .zip.aes)", "action": lambda: action_concatenate_parts(service)},
        {"desc": "Decrypt encrypted archive (.zip.aes -> .zip)", "action": lambda: action_decrypt_parts(service)},
        {"desc": "Unzip downloaded archive into batch directory", "action": lambda: action_unzip_files(service)},
        {"desc": "Prettify extracted XMLs and JSON metadata", "action": lambda: action_prettify_xml_json(service)},
        {"desc": "List working directory contents (ls)", "action": lambda: action_list_directory(service)},
        {"desc": "Refresh access token", "action": lambda: action_refresh_token(service)},
        {"desc": "Close session (keep token, clear local zip/parts)", "action": lambda: action_close_session(service)},
        {"desc": "Clear cache JSON", "action": lambda: action_clear_cache(service)},
    ]


def print_menu(menu_actions):
    print("\n" + "=" * 50)
    print("      KSeF 2.0 Interactive Test Console")
    print("=" * 50)
    for idx, item in enumerate(menu_actions, 1):
        print(f"{idx:>2}. {item['desc']}")
    print(" 0. Exit")
    print("=" * 50)


def main():
    service = KsefApiService(mode="test")
    password = "Qwertyuiop@12345"

    menu_actions = get_menu_actions(service, service.cert_path, service.key_path, password)

    os.system("clear")
    while True:
        actions_no = len(menu_actions)

        print_menu(menu_actions)
        choice = input(f"Select an option [0-{actions_no}]: ").strip()
        if not choice or choice == "0":
            print("\n[+] Exiting test console.")
            sys.exit(0)
        if not choice.isdigit():
            continue

        choice_idx = int(choice) - 1
        if choice_idx < 0 or choice_idx >= actions_no:
            print("\n[!] Invalid selection.")
            continue

        menu_item = menu_actions[choice_idx]
        try:
            menu_item["action"]()
        except KSeFAPIError as err:
            print(f"\n[!] KSeF API Error: {err}")
        except Exception as err:
            print(f"\n[!] Execution error ({type(err).__name__}): {err}")
            raise


if __name__ == "__main__":
    main()
