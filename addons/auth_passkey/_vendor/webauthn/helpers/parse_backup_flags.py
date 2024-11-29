from enum import Enum
from dataclasses import dataclass

from .structs import AuthenticatorDataFlags, CredentialDeviceType
from .exceptions import InvalidBackupFlags


@dataclass
class ParsedBackupFlags:
    credential_device_type: CredentialDeviceType
    credential_backed_up: bool


def parse_backup_flags(flags: AuthenticatorDataFlags) -> ParsedBackupFlags:
    """Convert backup eligibility and backup state flags into more useful representations

    Raises:
        `helpers.exceptions.InvalidBackupFlags` if an invalid backup state is detected
    """
    credential_device_type = CredentialDeviceType.SINGLE_DEVICE

    # A credential that can be backed up can typically be used on multiple devices
    if flags.be:
        credential_device_type = CredentialDeviceType.MULTI_DEVICE

    if credential_device_type == CredentialDeviceType.SINGLE_DEVICE and flags.bs:
        raise InvalidBackupFlags(
            "Single-device credential indicated that it was backed up, which should be impossible."
        )

    return ParsedBackupFlags(
        credential_device_type=credential_device_type,
        credential_backed_up=flags.bs,
    )
