import base64
from werkzeug.urls import url_parse

from odoo import api, fields, models, _
from odoo.exceptions import AccessDenied
from odoo.tools import sql
from odoo.addons.base.models.res_users import check_identity

from ..lib.duo_labs.webauthn import base64url_to_bytes, generate_authentication_options, verify_authentication_response, generate_registration_options, verify_registration_response
from ..lib.duo_labs.webauthn.helpers.structs import AuthenticatorSelectionCriteria, ResidentKeyRequirement, UserVerificationRequirement


class PassKey(models.Model):
    _name = 'auth.passkey.key'
    _description = 'Passkey'
    _order = 'id desc'

    name = fields.Char(required=True)
    credential_identifier = fields.Char(required=True, groups='base.group_system')
    public_key = fields.Char(required=True, groups='base.group_system', compute='_compute_public_key', inverse='_inverse_public_key')
    sign_count = fields.Integer(default=0, groups='base.group_system')

    _sql_constraints = [
        ('unique_identifier', 'UNIQUE(credential_identifier)', 'The credential identifier should be unique.'),
    ]

    def init(self):
        super().init()
        if not sql.column_exists(self.env.cr, self._table, 'public_key'):
            self.env.cr.execute('ALTER TABLE %s ADD COLUMN public_key varchar' % self._table)

    def _compute_public_key(self):
        query = 'SELECT public_key FROM %s WHERE id = %%s' % self._table
        for passkey in self:
            self.env.cr.execute(query, [passkey.id])
            public_key = self.env.cr.fetchone()[0]
            passkey.public_key = public_key

    def _inverse_public_key(self):
        pass

    @api.model
    def _get_passkey_by_credential_id(self, identifier):
        identifier = base64.urlsafe_b64decode(identifier + '===').hex()
        result = self.sudo().search([('credential_identifier', '=', identifier)], limit=1)
        return result

    @api.model
    def _start_auth(self):
        return generate_authentication_options(
            rp_id=url_parse(self.get_base_url()).host,
            user_verification=UserVerificationRequirement.REQUIRED,
        )

    @api.model
    def _verify_auth(self, auth, challenge):
        parsed_url = url_parse(self.get_base_url())
        auth_key = self._get_passkey_by_credential_id(auth['id'])
        if not auth_key:
            raise AccessDenied(_('This Passkey is not registered in this database.'))
        auth_verification = verify_authentication_response(
            credential=auth,
            expected_challenge=challenge,
            expected_origin=parsed_url.replace(path='').to_url(),
            expected_rp_id=parsed_url.host,
            credential_public_key=base64url_to_bytes(auth_key.public_key),
            credential_current_sign_count=auth_key.sign_count,
        )
        auth_key.sign_count = auth_verification.new_sign_count
        return auth_key

    @api.model
    def _create_registration_options(self):
        return generate_registration_options(
            rp_id=url_parse(self.get_base_url()).host,
            rp_name='Odoo',
            user_id=str(self.env.user.id).encode(),
            user_name=self.env.user.login,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED
            )
        )

    @api.model
    def _verify_registration_options(self, registration, challenge):
        parsed_url = url_parse(self.get_base_url())
        return verify_registration_response(
            credential=registration,
            expected_challenge=challenge,
            expected_origin=parsed_url.replace(path='').to_url(),
            expected_rp_id=parsed_url.host,
        )

    @check_identity
    def action_delete_passkey(self):
        for key in self:
            if key.create_uid.id == self.env.user.id:
                key.sudo().unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Successfully deleted Passkey'),
                'type': 'success',
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                },
            }
        }

    def action_rename_passkey(self):
        return {
            'name': _('Rename Passkey'),
            'type': 'ir.actions.act_window',
            'res_model': 'auth.passkey.key',
            'view_id': self.env.ref('auth_passkey.auth_passkey_key_rename').id,
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
            'context': {
                'dialog_size': 'medium',
            }
        }


class PassKeyName(models.TransientModel):
    _name = 'auth.passkey.key.name'
    _description = 'Passkey Name'

    name = fields.Char('Name', required=True)

    @check_identity
    def make_key(self, credential_identifier=None, public_key=None):
        # We add in these fields with JS, if we didn't give them default values we would get a XML validation warning.
        if credential_identifier and public_key:
            self.ensure_one()
            self.env.cr.execute('''
            INSERT INTO {table} (name, credential_identifier, public_key, create_uid, write_date, create_date)
            VALUES (%s, %s, %s, %s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC')
            '''.format(table=self.env['auth.passkey.key']._table), [
                self.name,
                # Base64 can have different levels of padding depending on the platform / key.
                base64.urlsafe_b64decode(credential_identifier + '===').hex(),
                public_key,
                self.env.user.id,
            ])
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Successfully created Passkey'),
                    'type': 'success',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
