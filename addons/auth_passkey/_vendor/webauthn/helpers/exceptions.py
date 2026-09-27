class InvalidRegistrationResponse(Exception):
    pass


class InvalidAuthenticationResponse(Exception):
    pass


class InvalidPublicKeyStructure(Exception):
    pass


class UnsupportedPublicKeyType(Exception):
    pass


class InvalidJSONStructure(Exception):
    pass


class InvalidAuthenticatorDataStructure(Exception):
    pass


class SignatureVerificationException(Exception):
    pass


class UnsupportedAlgorithm(Exception):
    pass


class UnsupportedPublicKey(Exception):
    pass


class UnsupportedEC2Curve(Exception):
    pass


class InvalidTPMPubAreaStructure(Exception):
    pass


class InvalidTPMCertInfoStructure(Exception):
    pass


class InvalidCertificateChain(Exception):
    pass


class InvalidBackupFlags(Exception):
    pass


class InvalidCBORData(Exception):
    pass
