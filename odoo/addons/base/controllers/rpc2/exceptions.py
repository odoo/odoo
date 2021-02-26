# Part of Odoo. See LICENSE file for full copyright and licensing details.

import enum
import logging
from odoo.exceptions import UserError
from odoo.tools import snake

_logger = logging.getLogger(__name__)


# https://xmlrpc-epi.sourceforge.net/specs/rfc.fault_codes.php
class RpcErrorCode(enum.IntEnum):
    parse_error = -32700
    unsupported_encoding = -32701
    encoding_error = -32702
    invalid_request = -32600
    method_not_found = -32601
    invalid_params = -32602
    internal_error = -32603
    application_error = -32500
    system_error = -32500
    transport_error = -32300

    odoo_user_error = -32100
    odoo_access_denied = -32101
    odoo_access_error = -32102
    odoo_missing_error = -32103
    odoo_validation_error = -32104

    @classmethod
    def from_exception(cls, exc):
        if isinstance(exc, UserError):
            snake_name = snake(type(exc).__name__)
            code = getattr(cls, f'odoo_{snake_name}', None)
            if code:
                return code

            _logger.warning("%s lacks a RPC error code, using -32100 (UserError) instead.", type(exc))
            return cls.odoo_user_error

        return cls.application_error


class RpcError(Exception):
    def __init__(self, code):
        super().__init__()
        self.code = code
