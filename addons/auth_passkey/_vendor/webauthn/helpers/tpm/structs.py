from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Union

from ..cose import COSECRV, COSEAlgorithmIdentifier
from ..exceptions import InvalidTPMPubAreaStructure

################
#
# A whole lotta domain knowledge is captured here, with hazy connections to source
# documents. Good places to start searching for more info on these values are the
# following Trusted Computing Group TPM Library docs linked in the WebAuthn API:
#
# - https://www.trustedcomputinggroup.org/wp-content/uploads/TPM-Rev-2.0-Part-1-Architecture-01.38.pdf
# - https://www.trustedcomputinggroup.org/wp-content/uploads/TPM-Rev-2.0-Part-2-Structures-01.38.pdf
# - https://www.trustedcomputinggroup.org/wp-content/uploads/TPM-Rev-2.0-Part-3-Commands-01.38.pdf
#
################


class TPM_ST(str, Enum):
    RSP_COMMAND = "TPM_ST_RSP_COMMAND"
    NULL = "TPM_ST_NULL"
    NO_SESSIONS = "TPM_ST_NO_SESSIONS"
    SESSIONS = "TPM_ST_SESSIONS"
    ATTEST_NV = "TPM_ST_ATTEST_NV"
    ATTEST_COMMAND_AUDIT = "TPM_ST_ATTEST_COMMAND_AUDIT"
    ATTEST_SESSION_AUDIT = "TPM_ST_ATTEST_SESSION_AUDIT"
    ATTEST_CERTIFY = "TPM_ST_ATTEST_CERTIFY"
    ATTEST_QUOTE = "TPM_ST_ATTEST_QUOTE"
    ATTEST_TIME = "TPM_ST_ATTEST_TIME"
    ATTEST_CREATION = "TPM_ST_ATTEST_CREATION"
    CREATION = "TPM_ST_CREATION"
    VERIFIED = "TPM_ST_VERIFIED"
    AUTH_SECRET = "TPM_ST_AUTH_SECRET"
    HASHCHECK = "TPM_ST_HASHCHECK"
    AUTH_SIGNED = "TPM_ST_AUTH_SIGNED"
    FU_MANIFEST = "TPM_ST_FU_MANIFEST"


class TPM_ALG(str, Enum):
    ERROR = "TPM_ALG_ERROR"
    RSA = "TPM_ALG_RSA"
    SHA1 = "TPM_ALG_SHA1"
    HMAC = "TPM_ALG_HMAC"
    AES = "TPM_ALG_AES"
    MGF1 = "TPM_ALG_MGF1"
    KEYEDHASH = "TPM_ALG_KEYEDHASH"
    XOR = "TPM_ALG_XOR"
    SHA256 = "TPM_ALG_SHA256"
    SHA384 = "TPM_ALG_SHA384"
    SHA512 = "TPM_ALG_SHA512"
    NULL = "TPM_ALG_NULL"
    SM3_256 = "TPM_ALG_SM3_256"
    SM4 = "TPM_ALG_SM4"
    RSASSA = "TPM_ALG_RSASSA"
    RSAES = "TPM_ALG_RSAES"
    RSAPSS = "TPM_ALG_RSAPSS"
    OAEP = "TPM_ALG_OAEP"
    ECDSA = "TPM_ALG_ECDSA"
    ECDH = "TPM_ALG_ECDH"
    ECDAA = "TPM_ALG_ECDAA"
    SM2 = "TPM_ALG_SM2"
    ECSCHNORR = "TPM_ALG_ECSCHNORR"
    ECMQV = "TPM_ALG_ECMQV"
    KDF1_SP800_56A = "TPM_ALG_KDF1_SP800_56A"
    KDF2 = "TPM_ALG_KDF2"
    KDF1_SP800_108 = "TPM_ALG_KDF1_SP800_108"
    ECC = "TPM_ALG_ECC"
    SYMCIPHER = "TPM_ALG_SYMCIPHER"
    CAMELLIA = "TPM_ALG_CAMELLIA"
    CTR = "TPM_ALG_CTR"
    OFB = "TPM_ALG_OFB"
    CBC = "TPM_ALG_CBC"
    CFB = "TPM_ALG_CFB"
    ECB = "TPM_ALG_ECB"


class TPM_ECC_CURVE(str, Enum):
    NONE = "NONE"
    NIST_P192 = "NIST_P192"
    NIST_P224 = "NIST_P224"
    NIST_P256 = "NIST_P256"
    NIST_P384 = "NIST_P384"
    NIST_P521 = "NIST_P521"
    BN_P256 = "BN_P256"
    BN_P638 = "BN_P638"
    SM2_P256 = "SM2_P256"


class TPMCertInfoClockInfo:
    """
    10.11.1 TPMS_CLOCK_INFO
    """

    clock: bytes
    reset_count: int
    restart_count: int
    safe: bool

    def __init__(self, clock_info: bytes):
        self.clock = clock_info[0:8]
        self.reset_count = int.from_bytes(clock_info[8:12], "big")
        self.restart_count = int.from_bytes(clock_info[12:16], "big")
        self.safe = bool(clock_info[16])


class TPMCertInfoAttested:
    """
    10.12.3 TPMS_CERTIFY_INFO
    """

    name_alg: TPM_ALG
    name_alg_bytes: bytes
    name: bytes
    qualified_name: bytes

    def __init__(self, attested_name: bytes, qualified_name: bytes):
        self.name_alg = TPM_ALG_MAP[attested_name[0:2]]
        self.name_alg_bytes = attested_name[0:2]
        self.name = attested_name
        self.qualified_name = qualified_name


@dataclass
class TPMCertInfo:
    """
    10.12.8 TPMS_ATTEST
    """

    magic: bytes
    type: TPM_ST
    qualified_signer: bytes
    extra_data: bytes
    clock_info: TPMCertInfoClockInfo
    firmware_version: bytes
    attested: TPMCertInfoAttested


class TPMPubAreaParametersRSA:
    """
    12.2.3.5 TPMS_RSA_PARMS
    """

    symmetric: TPM_ALG
    scheme: TPM_ALG
    key_bits: bytes
    exponent: bytes

    def __init__(self, params: bytes):
        self.symmetric = TPM_ALG_MAP[params[0:2]]
        self.scheme = TPM_ALG_MAP[params[2:4]]
        self.key_bits = params[4:6]
        self.exponent = params[6:10]


class TPMPubAreaParametersECC:
    """
    12.2.3.6 TPMS_ECC_PARMS
    """

    symmetric: TPM_ALG
    scheme: TPM_ALG
    curve_id: TPM_ECC_CURVE
    kdf: TPM_ALG

    def __init__(self, params: bytes):
        self.symmetric = TPM_ALG_MAP[params[0:2]]
        self.scheme = TPM_ALG_MAP[params[2:4]]
        self.curve_id = TPM_ECC_CURVE_MAP[params[4:6]]
        self.kdf = TPM_ALG_MAP[params[6:8]]


class TPMPubAreaObjectAttributes:
    """
    8.3 TPMA_OBJECT (Object Attributes)
    """

    fixed_tpm: bool
    st_clear: bool
    fixed_parent: bool
    sensitive_data_origin: bool
    user_with_auth: bool
    admin_with_policy: bool
    no_da: bool
    encrypted_duplication: bool
    restricted: bool
    decrypt: bool
    sign_or_encrypt: bool

    def __init__(self, object_attributes: bytes):
        attrs = int.from_bytes(object_attributes[0:4], "big")
        self.fixed_tpm = attrs & (1 << 1) != 0
        self.st_clear = attrs & (1 << 2) != 0
        self.fixed_parent = attrs & (1 << 4) != 0
        self.sensitive_data_origin = attrs & (1 << 5) != 0
        self.user_with_auth = attrs & (1 << 6) != 0
        self.admin_with_policy = attrs & (1 << 7) != 0
        self.no_da = attrs & (1 << 10) != 0
        self.encrypted_duplication = attrs & (1 << 11) != 0
        self.restricted = attrs & (1 << 16) != 0
        self.decrypt = attrs & (1 << 17) != 0
        self.sign_or_encrypt = attrs & (1 << 18) != 0


class TPMPubAreaUnique:
    """
    12.2.3.2 TPMU_PUBLIC_ID
    """

    value: bytes

    def __init__(self, unique: bytes, alg_type: TPM_ALG):
        if alg_type == TPM_ALG.RSA:
            """
            As per 11.2.4.5 TPM2B_PUBLIC_KEY_RSA, extract `unique` of dynamic length
            """
            unique_length = int.from_bytes(unique[0:2], "big")
            rsa_unique = unique[2 : 2 + unique_length]
            self.value = rsa_unique
        elif alg_type == TPM_ALG.ECC:
            """
            As per 12.2.3.2 TPMU_PUBLIC_ID, `unique` is `TPMS_ECC_POINT` when `type`
            indicates ECC.

            As per 11.2.5.2 TPMS_ECC_POINT, `x` and `y` within are
            `TPM2B_ECC_PARAMETER`, which is a uint16 `size`, followed by bytes of
            the indicated length.

            `unique`, then, is structured thusly:
            [
                [x_len, ...x_bytes],
                [y_len, ...y_bytes]
            ]

            Get `unique` to this structure for easier comparison with the output from
            `decode_credential_public_key`, which will return bytes for its `x` and `y`
            and to which this value will be compared:

            [
                x_bytes,
                y_bytes,
            ]

            """
            pointer = 0
            unique_x_len = int.from_bytes(unique[0:2], "big")
            pointer += 2
            unique_x = unique[pointer : pointer + unique_x_len]
            pointer += unique_x_len
            unique_y_len = int.from_bytes(unique[pointer : pointer + 2], "big")
            pointer += 2
            unique_y = unique[pointer : pointer + unique_y_len]

            self.value = b"".join([unique_x, unique_y])
        else:
            raise InvalidTPMPubAreaStructure(
                f'Pub Area alg type "{alg_type}" was not "{TPM_ALG.RSA}" or "{TPM_ALG.ECC}"'
            )


@dataclass
class TPMPubArea:
    """
    12.2.4 TPMT_PUBLIC
    """

    type: TPM_ALG
    name_alg: TPM_ALG
    object_attributes: TPMPubAreaObjectAttributes
    auth_policy: bytes
    parameters: Union[TPMPubAreaParametersRSA, TPMPubAreaParametersECC]
    unique: TPMPubAreaUnique


@dataclass
class TPMManufacturerInfo:
    name: str
    id: str


"""
6.9 TPM_ST (Structure Tags)
"""
TPM_ST_MAP: Mapping[bytes, TPM_ST] = {
    b"\x00\xc4": TPM_ST.RSP_COMMAND,
    b"\x80\x00": TPM_ST.NULL,
    b"\x80\x01": TPM_ST.NO_SESSIONS,
    b"\x80\x02": TPM_ST.SESSIONS,
    b"\x80\x14": TPM_ST.ATTEST_NV,
    b"\x80\x15": TPM_ST.ATTEST_COMMAND_AUDIT,
    b"\x80\x16": TPM_ST.ATTEST_SESSION_AUDIT,
    b"\x80\x17": TPM_ST.ATTEST_CERTIFY,
    b"\x80\x18": TPM_ST.ATTEST_QUOTE,
    b"\x80\x19": TPM_ST.ATTEST_TIME,
    b"\x80\x1a": TPM_ST.ATTEST_CREATION,
    b"\x80\x21": TPM_ST.CREATION,
    b"\x80\x22": TPM_ST.VERIFIED,
    b"\x80\x23": TPM_ST.AUTH_SECRET,
    b"\x80\x24": TPM_ST.HASHCHECK,
    b"\x80\x25": TPM_ST.AUTH_SIGNED,
    b"\x80\x29": TPM_ST.FU_MANIFEST,
}


"""
6.3 TPM_ALG_ID
"""
TPM_ALG_MAP: Mapping[bytes, TPM_ALG] = {
    b"\x00\x00": TPM_ALG.ERROR,
    b"\x00\x01": TPM_ALG.RSA,
    b"\x00\x04": TPM_ALG.SHA1,
    b"\x00\x05": TPM_ALG.HMAC,
    b"\x00\x06": TPM_ALG.AES,
    b"\x00\x07": TPM_ALG.MGF1,
    b"\x00\x08": TPM_ALG.KEYEDHASH,
    b"\x00\x0a": TPM_ALG.XOR,
    b"\x00\x0b": TPM_ALG.SHA256,
    b"\x00\x0c": TPM_ALG.SHA384,
    b"\x00\x0d": TPM_ALG.SHA512,
    b"\x00\x10": TPM_ALG.NULL,
    b"\x00\x12": TPM_ALG.SM3_256,
    b"\x00\x13": TPM_ALG.SM4,
    b"\x00\x14": TPM_ALG.RSASSA,
    b"\x00\x15": TPM_ALG.RSAES,
    b"\x00\x16": TPM_ALG.RSAPSS,
    b"\x00\x17": TPM_ALG.OAEP,
    b"\x00\x18": TPM_ALG.ECDSA,
    b"\x00\x19": TPM_ALG.ECDH,
    b"\x00\x1a": TPM_ALG.ECDAA,
    b"\x00\x1b": TPM_ALG.SM2,
    b"\x00\x1c": TPM_ALG.ECSCHNORR,
    b"\x00\x1d": TPM_ALG.ECMQV,
    b"\x00\x20": TPM_ALG.KDF1_SP800_56A,
    b"\x00\x21": TPM_ALG.KDF2,
    b"\x00\x22": TPM_ALG.KDF1_SP800_108,
    b"\x00\x23": TPM_ALG.ECC,
    b"\x00\x25": TPM_ALG.SYMCIPHER,
    b"\x00\x26": TPM_ALG.CAMELLIA,
    b"\x00\x40": TPM_ALG.CTR,
    b"\x00\x41": TPM_ALG.OFB,
    b"\x00\x42": TPM_ALG.CBC,
    b"\x00\x43": TPM_ALG.CFB,
    b"\x00\x44": TPM_ALG.ECB,
}


"""
6.4 TPM_ECC_CURVE
"""
TPM_ECC_CURVE_MAP: Mapping[bytes, TPM_ECC_CURVE] = {
    b"\x00\x00": TPM_ECC_CURVE.NONE,
    b"\x00\x01": TPM_ECC_CURVE.NIST_P192,
    b"\x00\x02": TPM_ECC_CURVE.NIST_P224,
    b"\x00\x03": TPM_ECC_CURVE.NIST_P256,
    b"\x00\x04": TPM_ECC_CURVE.NIST_P384,
    b"\x00\x05": TPM_ECC_CURVE.NIST_P521,
    b"\x00\x10": TPM_ECC_CURVE.BN_P256,
    b"\x00\x11": TPM_ECC_CURVE.BN_P638,
    b"\x00\x20": TPM_ECC_CURVE.SM2_P256,
}


# Intentionally omit curves we can't map so a KeyError gets thrown
TPM_ECC_CURVE_COSE_CRV_MAP: Mapping[TPM_ECC_CURVE, COSECRV] = {
    TPM_ECC_CURVE.NIST_P256: COSECRV.P256,
    TPM_ECC_CURVE.NIST_P384: COSECRV.P384,
    TPM_ECC_CURVE.NIST_P521: COSECRV.P521,
    TPM_ECC_CURVE.BN_P256: COSECRV.P256,
    TPM_ECC_CURVE.SM2_P256: COSECRV.P256,
}


# Intentionally omit algs we can't map so a KeyError gets thrown
TPM_ALG_COSE_ALG_MAP: Mapping[TPM_ALG, COSEAlgorithmIdentifier] = {
    TPM_ALG.SHA256: COSEAlgorithmIdentifier.RSASSA_PSS_SHA_256,
    TPM_ALG.SHA384: COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_384,
    TPM_ALG.SHA512: COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_512,
    TPM_ALG.SHA1: COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_1,
}


# Sourced from https://trustedcomputinggroup.org/resource/vendor-id-registry/
# Latest version: https://trustedcomputinggroup.org/wp-content/uploads/TCG-TPM-Vendor-ID-Registry-Version-1.02-Revision-1.00.pdf
TPM_MANUFACTURERS: Mapping[str, TPMManufacturerInfo] = {
    "id:414D4400": TPMManufacturerInfo(name="AMD", id="AMD"),
    "id:41544D4C": TPMManufacturerInfo(name="Atmel", id="ATML"),
    "id:4252434D": TPMManufacturerInfo(name="Broadcom", id="BRCM"),
    "id:4353434F": TPMManufacturerInfo(name="Cisco", id="CSCO"),
    "id:464C5953": TPMManufacturerInfo(name="Flyslice Technologies", id="FLYS"),
    "id:48504500": TPMManufacturerInfo(name="HPE", id="HPE"),
    "id:49424d00": TPMManufacturerInfo(name="IBM", id="IBM"),
    "id:49465800": TPMManufacturerInfo(name="Infineon", id="IFX"),
    "id:494E5443": TPMManufacturerInfo(name="Intel", id="INTC"),
    "id:4C454E00": TPMManufacturerInfo(name="Lenovo", id="LEN"),
    "id:4D534654": TPMManufacturerInfo(name="Microsoft", id="MSFT"),
    "id:4E534D20": TPMManufacturerInfo(name="National Semiconductor", id="NSM"),
    "id:4E545A00": TPMManufacturerInfo(name="Nationz", id="NTZ"),
    "id:4E544300": TPMManufacturerInfo(name="Nuvoton Technology", id="NTC"),
    "id:51434F4D": TPMManufacturerInfo(name="Qualcomm", id="QCOM"),
    "id:534D5343": TPMManufacturerInfo(name="SMSC", id="SMSC"),
    "id:53544D20": TPMManufacturerInfo(name="ST Microelectronics", id="STM"),
    "id:534D534E": TPMManufacturerInfo(name="Samsung", id="SMSN"),
    "id:534E5300": TPMManufacturerInfo(name="Sinosun", id="SNS"),
    "id:54584E00": TPMManufacturerInfo(name="Texas Instruments", id="TXN"),
    "id:57454300": TPMManufacturerInfo(name="Winbond", id="WEC"),
    "id:524F4343": TPMManufacturerInfo(name="Fuzhou Rockchip", id="ROCC"),
    "id:474F4F47": TPMManufacturerInfo(name="Google", id="GOOG"),
}
