# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging
import json

import requests
import werkzeug.urls

from ast import literal_eval
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from odoo import api, release, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.models import AbstractModel
from odoo.tools.translate import _
from odoo.tools import config, misc

_logger = logging.getLogger(__name__)


PRIVATE_KEY_FACTORIES = {
    'ed25519': ed25519.Ed25519PrivateKey,
}


def _key_algorithm(private_key):
    for algorithm, key_type in PRIVATE_KEY_FACTORIES.items():
        if isinstance(private_key, key_type):
            return algorithm
    raise TypeError(f"Could not determine the algorithm from key {private_key}")


def _encode_key(private_key):
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    algorithm = _key_algorithm(private_key)
    return f'{algorithm}.{base64.b64encode(private_bytes).decode("ascii")}'


def _decode_key(encoded_key):
    if not encoded_key:
        return None

    algorithm, _, key = encoded_key.partition('.')
    if algorithm not in PRIVATE_KEY_FACTORIES:
        raise NotImplementedError(f'Signature algorithm {algorithm!r} is not supported')

    private_bytes = base64.b64decode(key, validate=True)
    return PRIVATE_KEY_FACTORIES[algorithm].from_private_bytes(private_bytes)


def _signature_object(private_key, payload):
    signature = private_key.sign(payload)
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {
        'algorithm': _key_algorithm(private_key),
        'public_key': base64.b64encode(public_key).decode('ascii'),
        'signature': base64.b64encode(signature).decode('ascii'),
    }


def _canonical_json(payload):
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode('ascii')


class PublisherWarrantyContract(AbstractModel):
    _name = "publisher_warranty.contract"
    _description = 'Publisher Warranty Contract'

    @api.model
    def _get_message(self):
        Users = self.env['res.users']
        IrParamSudo = self.env['ir.config_parameter'].sudo()

        dbuuid = IrParamSudo.get_param('database.uuid')
        db_create_date = IrParamSudo.get_param('database.create_date')
        limit_date = datetime.datetime.now()
        limit_date = limit_date - datetime.timedelta(15)
        limit_date_str = limit_date.strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT)
        nbr_users = Users.search_count([('active', '=', True)])
        nbr_active_users = Users.search_count([("login_date", ">=", limit_date_str), ('active', '=', True)])
        nbr_share_users = 0
        nbr_active_share_users = 0
        if "share" in Users._fields:
            nbr_share_users = Users.search_count([("share", "=", True), ('active', '=', True)])
            nbr_active_share_users = Users.search_count([("share", "=", True), ("login_date", ">=", limit_date_str), ('active', '=', True)])
        user = self.env.user
        domain = [('application', '=', True), ('state', 'in', ['installed', 'to upgrade', 'to remove'])]
        apps = self.env['ir.module.module'].sudo().search_read(domain, ['name'])

        enterprise_code = IrParamSudo.get_param('database.enterprise_code')

        web_base_url = IrParamSudo.get_param('web.base.url')
        msg = {
            "dbuuid": dbuuid,
            "nbr_users": nbr_users,
            "nbr_active_users": nbr_active_users,
            "nbr_share_users": nbr_share_users,
            "nbr_active_share_users": nbr_active_share_users,
            "dbname": self._cr.dbname,
            "db_create_date": db_create_date,
            "version": release.version,
            "language": user.lang,
            "web_base_url": web_base_url,
            "apps": [app['name'] for app in apps],
            "enterprise_code": enterprise_code,
        }
        if user.partner_id.company_id:
            company_id = user.partner_id.company_id
            msg.update(company_id.read(["name", "email", "phone"])[0])
        return msg

    @api.model
    def _sign_msg(self, unsigned_msg):
        with self.pool.cursor() as cr:
            needs_commit = False

            IrParamSudo = self.env(cr=cr)['ir.config_parameter'].sudo()
            signing_key = _decode_key(IrParamSudo.get_param('database.update_notification.key'))
            previous_signing_key = _decode_key(IrParamSudo.get_param('database.update_notification.previous_key'))

            if not previous_signing_key and signing_key and not isinstance(signing_key, ed25519.Ed25519PrivateKey):
                # Perform a key rotation
                IrParamSudo.set_param('database.update_notification.previous_key', _encode_key(signing_key))
                needs_commit = True
                previous_signing_key, signing_key = signing_key, None

            if not signing_key:
                # No key yet (or rotation), let's create one on-the-fly
                signing_key = ed25519.Ed25519PrivateKey.generate()
                IrParamSudo.set_param('database.update_notification.key', _encode_key(signing_key))
                needs_commit = True

            if needs_commit:
                cr.commit()

        msg = dict(unsigned_msg)
        canonical_json = _canonical_json(unsigned_msg)
        msg['signature'] = _signature_object(signing_key, canonical_json)
        if previous_signing_key:
            msg['old_signature'] = _signature_object(previous_signing_key, canonical_json)

        return msg

    @api.model
    def _get_sys_logs(self):
        """
        Utility method to send a publisher warranty get logs messages.
        """
        unsigned_msg = self._get_message()
        msg = self._sign_msg(unsigned_msg)
        arguments = {'arg0': json.dumps(msg), "action": "update"}

        url = config.get("publisher_warranty_url")

        r = requests.post(url, data=arguments, timeout=30)
        r.raise_for_status()
        result = literal_eval(r.text)
        signature_key = result.pop('signature_key', None)
        if signature_key:
            with self.pool.cursor() as cr:
                IrParamSudo = self.env(cr=cr)['ir.config_parameter'].sudo()
                signing_key = _decode_key(IrParamSudo.get_param('database.update_notification.key'))
                if signing_key:
                    public_key = signing_key.public_key().public_bytes(
                        encoding=serialization.Encoding.Raw,
                        format=serialization.PublicFormat.Raw,
                    ).hex()
                    if signature_key == public_key:
                        # clear the previous key as the server accepted the new one
                        IrParamSudo.set_param('database.update_notification.previous_key', None)
                        cr.commit()
        return result

    def update_notification(self, cron_mode=True):
        """
        Send a message to Odoo's publisher warranty server to check the
        validity of the contracts, get notifications, etc...

        @param cron_mode: If true, catch all exceptions (appropriate for usage in a cron).
        @type cron_mode: boolean
        """
        try:
            try:
                result = self._get_sys_logs()
            except Exception:
                if cron_mode:   # we don't want to see any stack trace in cron
                    return False
                _logger.debug("Exception while sending a get logs messages", exc_info=1)
                raise UserError(_("Error during communication with the publisher warranty server."))
            # old behavior based on res.log; now on mail.message, that is not necessarily installed
            user = self.env['res.users'].sudo().browse(SUPERUSER_ID)
            poster = self.sudo().env.ref('mail.channel_all_employees')
            for message in result["messages"]:
                try:
                    poster.message_post(body=message, subtype_xmlid='mail.mt_comment', partner_ids=[user.partner_id.id])
                except Exception:
                    pass
            if result.get('enterprise_info'):
                # Update expiration date
                set_param = self.env['ir.config_parameter'].sudo().set_param
                set_param('database.expiration_date', result['enterprise_info'].get('expiration_date'))
                set_param('database.expiration_reason', result['enterprise_info'].get('expiration_reason', 'trial'))
                set_param('database.enterprise_code', result['enterprise_info'].get('enterprise_code'))
                set_param('database.already_linked_subscription_url', result['enterprise_info'].get('database_already_linked_subscription_url'))
                set_param('database.already_linked_email', result['enterprise_info'].get('database_already_linked_email'))
                set_param('database.already_linked_send_mail_url', result['enterprise_info'].get('database_already_linked_send_mail_url'))

        except Exception:
            if cron_mode:
                return False    # we don't want to see any stack trace in cron
            else:
                raise
        return True
