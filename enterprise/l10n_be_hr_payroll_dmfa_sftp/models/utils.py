# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

import xml.etree.ElementTree as ET

from contextlib import contextmanager
from io import StringIO

from odoo import modules, tools, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

try:
    import paramiko
except ImportError:
    _logger.warning("The paramiko python library is not installed, DmfA synchronization won't work.")
    paramiko = None

SFTP_HOST = "sftp.socialsecurity.be"
SFTP_PORT = 8022


def xml_str_to_dict(xml_str):
    def etree_to_dict(elem):
        result = {}
        # Handle Attributes
        if elem.attrib:
            result.update({f"@{k}": v for k, v in elem.attrib.items()})

        # Handle Children
        children = list(elem)
        if children:
            # Regroup children by tag
            children_result = {}
            for child in children:
                child_dict = etree_to_dict(child)
                tag = child.tag
                if tag not in children_result:
                    children_result[tag] = []
                children_result[tag].append(child_dict)

            # Simplify single element lists
            for k, v in children_result.items():
                if len(v) == 1:
                    children_result[k] = v[0]
            result.update(children_result)
        else:
            # Plain text
            text = elem.text.strip() if elem.text else ''
            if text:
                if result:
                    result["#text"] = text
                else:
                    result = text
        return result

    root = ET.fromstring(xml_str)
    data_dict = {root.tag: etree_to_dict(root)}
    return data_dict


@contextmanager
def open_sftp_connection(ssh_key, username):
    if not paramiko:
        raise UserError(_("Paramiko python library is not installed."))
    if tools.config['test_enable'] or modules.module.current_test:
        raise UserError(_("SFTP Connection disabled in testing environment."))
    if not username:
        raise UserError(_("No ONSS technical user name defined on the payroll configuration"))
    if not ssh_key:
        raise UserError(_("No ONSS technical user private key defined on the payroll configuration"))
    try:
        # Decode the base64 binary field to get raw PEM key
        key_data = base64.b64decode(ssh_key.content)

        # Convert to StringIO so Paramiko can read it
        key_stream = StringIO(key_data.decode())

        # Load private key from memory
        _logger.info("Loading private key from attachment...")
        try:
            pkey = paramiko.RSAKey.from_private_key(
                key_stream,
                password=ssh_key.password)
        except paramiko.PasswordRequiredException:
            raise UserError(_("The key is encrypted but no passphrase was provided."))
        except paramiko.SSHException as e:
            raise UserError(_("Incorrect passphrase or invalid RSA key: %s", e))

        # SSH client setup
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        _logger.info("Connecting to %s:%s with key auth...", SFTP_HOST, SFTP_PORT)
        # Rationale for disabled_algorithms parameter:
        # The SFTP server only supports the legacy 'ssh-rsa' public key algorithm for authentication.
        # By default, Paramiko may prefer more secure algorithms like 'rsa-sha2-512' or 'rsa-sha2-256',
        # which could lead to negotiation failure with older servers.
        # This disables the newer algorithms so Paramiko will fall back to 'ssh-rsa',
        # allowing compatibility with servers that do not support the newer SHA2-based algorithms.
        client.connect(
            hostname=SFTP_HOST,
            port=SFTP_PORT,
            username=username,
            pkey=pkey,
            timeout=10,  # TCP socket timeout
            banner_timeout=5,  # Timeout for SSH banner
            auth_timeout=5,    # Timeout for authentication
            disabled_algorithms={'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']}
        )

        # Open SFTP session
        sftp = client.open_sftp()
        _logger.info("SFTP connection established with key.")
        yield sftp
    except Exception as e:  # noqa: BLE001
        error_msg = _("SFTP Connection Failed: %s", e)
        _logger.error(error_msg)
        raise UserError(error_msg)
    finally:
        sftp.close()
        client.close()
        _logger.info("Connection closed successfully.")
