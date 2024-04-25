from enum import Enum

from asn1crypto.core import (
    Boolean,
    Enumerated,
    Integer,
    Null,
    OctetString,
    Sequence,
    SetOf,
)


class Integers(SetOf):
    _child_spec = Integer


class SecurityLevel(Enumerated):
    _map = {
        0: "Software",
        1: "TrustedEnvironment",
        2: "StrongBox",
    }


class VerifiedBootState(Enumerated):
    _map = {
        0: "Verified",
        1: "SelfSigned",
        2: "Unverified",
        3: "Failed",
    }


class RootOfTrust(Sequence):
    _fields = [
        ("verifiedBootKey", OctetString),
        ("deviceLocked", Boolean),
        ("verifiedBootState", VerifiedBootState),
        ("verifiedBootHash", OctetString),
    ]


class AuthorizationList(Sequence):
    _fields = [
        ("purpose", Integers, {"explicit": 1, "optional": True}),
        ("algorithm", Integer, {"explicit": 2, "optional": True}),
        ("keySize", Integer, {"explicit": 3, "optional": True}),
        ("digest", Integers, {"explicit": 5, "optional": True}),
        ("padding", Integers, {"explicit": 6, "optional": True}),
        ("ecCurve", Integer, {"explicit": 10, "optional": True}),
        ("rsaPublicExponent", Integer, {"explicit": 200, "optional": True}),
        ("rollbackResistance", Null, {"explicit": 303, "optional": True}),
        ("activeDateTime", Integer, {"explicit": 400, "optional": True}),
        ("originationExpireDateTime", Integer, {"explicit": 401, "optional": True}),
        ("usageExpireDateTime", Integer, {"explicit": 402, "optional": True}),
        ("noAuthRequired", Null, {"explicit": 503, "optional": True}),
        ("userAuthType", Integer, {"explicit": 504, "optional": True}),
        ("authTimeout", Integer, {"explicit": 505, "optional": True}),
        ("allowWhileOnBody", Null, {"explicit": 506, "optional": True}),
        ("trustedUserPresenceRequired", Null, {"explicit": 507, "optional": True}),
        ("trustedConfirmationRequired", Null, {"explicit": 508, "optional": True}),
        ("unlockedDeviceRequired", Null, {"explicit": 509, "optional": True}),
        ("allApplications", Null, {"explicit": 600, "optional": True}),
        ("applicationId", OctetString, {"explicit": 601, "optional": True}),
        ("creationDateTime", Integer, {"explicit": 701, "optional": True}),
        ("origin", Integer, {"explicit": 702, "optional": True}),
        ("rollbackResistant", Null, {"explicit": 703, "optional": True}),
        ("rootOfTrust", RootOfTrust, {"explicit": 704, "optional": True}),
        ("osVersion", Integer, {"explicit": 705, "optional": True}),
        ("osPatchLevel", Integer, {"explicit": 706, "optional": True}),
        ("attestationApplicationId", OctetString, {"explicit": 709, "optional": True}),
        ("attestationIdBrand", OctetString, {"explicit": 710, "optional": True}),
        ("attestationIdDevice", OctetString, {"explicit": 711, "optional": True}),
        ("attestationIdProduct", OctetString, {"explicit": 712, "optional": True}),
        ("attestationIdSerial", OctetString, {"explicit": 713, "optional": True}),
        ("attestationIdImei", OctetString, {"explicit": 714, "optional": True}),
        ("attestationIdMeid", OctetString, {"explicit": 715, "optional": True}),
        ("attestationIdManufacturer", OctetString, {"explicit": 716, "optional": True}),
        ("attestationIdModel", OctetString, {"explicit": 717, "optional": True}),
        ("vendorPatchLevel", Integer, {"explicit": 718, "optional": True}),
        ("bootPatchLevel", Integer, {"explicit": 719, "optional": True}),
    ]


class KeyDescription(Sequence):
    """Attestation extension content as ASN.1 schema (DER-encoded)

    Corresponds to X.509 certificate extension with the following OID:

    `1.3.6.1.4.1.11129.2.1.17`

    See https://source.android.com/security/keystore/attestation#schema
    """

    _fields = [
        ("attestationVersion", Integer),
        ("attestationSecurityLevel", SecurityLevel),
        ("keymasterVersion", Integer),
        ("keymasterSecurityLevel", SecurityLevel),
        ("attestationChallenge", OctetString),
        ("uniqueId", OctetString),
        ("softwareEnforced", AuthorizationList),
        ("teeEnforced", AuthorizationList),
    ]


class KeyOrigin(int, Enum):
    """`Tag::ORIGIN`

    See https://source.android.com/security/keystore/tags#origin
    """

    GENERATED = 0
    DERIVED = 1
    IMPORTED = 2
    UNKNOWN = 3


class KeyPurpose(int, Enum):
    """`Tag::PURPOSE`

    See https://source.android.com/security/keystore/tags#purpose
    """

    ENCRYPT = 0
    DECRYPT = 1
    SIGN = 2
    VERIFY = 3
    DERIVE_KEY = 4
    WRAP_KEY = 5
