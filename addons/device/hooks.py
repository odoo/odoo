import logging

_logger = logging.getLogger(__name__)


def uninstall_hook(env):
    _logger.warning(
        "Remote module uninstall: Device credentials will remain in credential.credential"
    )
    _logger.warning(
        "To delete credentials, manually delete records in Settings → Technical → Credential Manager"
    )
