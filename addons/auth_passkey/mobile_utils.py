import base64
import binascii


def _get_app_sha256_cert_fingerprints():
    return [
        ("com.odoo.mobile", [
            "D6:73:20:02:CA:2D:01:C9:FD:FC:94:73:5A:D0:73:CF:2C:36:10:29:1F:4B:F7:5D:91:C2:1D:37:B2:18:E8:91",
        ]),
    ]


def _get_apk_key_hash(sha256_fingerprint):
    return base64.urlsafe_b64encode(binascii.a2b_hex(sha256_fingerprint.replace(':', ''))).decode('utf8').replace('=', '')


_VALID_APK_KEY_HASHES = [
    f"android:apk-key-hash:{_get_apk_key_hash(fingerprint)}"
    for _, fingerprints in _get_app_sha256_cert_fingerprints()
    for fingerprint in fingerprints
]


_WEB_WELL_KNOW_ANDROID = [
    {
        "relation": [
            "delegate_permission/common.handle_all_urls",
            "delegate_permission/common.get_login_creds"
        ],
        "target": {
            "namespace": "android_app",
            "package_name": package_name,
            "sha256_cert_fingerprints": fingerprints
        }
    } for package_name, fingerprints in _get_app_sha256_cert_fingerprints()
]
