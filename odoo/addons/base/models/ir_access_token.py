# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime, timedelta
from typing import Literal, Self

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.models import BaseModel
from odoo.tools.misc import consteq, hash_sign, verify_hash_signed


_logger = logging.getLogger(__name__)


class IrAccessToken(models.Model):
    _name = 'ir.access.token'
    _description = 'Access Token'

    res_model = fields.Char('Resource Model', required=True)
    res_id = fields.Many2oneReference('Resource ID', model_field='res_model', required=True)
    scope = fields.Char('Scope', required=True)
    expiration = fields.Datetime('Expiration', index='btree')
    owner_id = fields.Many2one('res.users')
    # Tokens are not stored.
    # However, it is necessary to maintain existing tokens as valid
    # and retain the ability to force the value of a token.
    manual_token = fields.Char('Manual Token', groups=fields.NO_ACCESS)
    token = fields.Char('Token', compute='_compute_token', groups=fields.NO_ACCESS)

    _res_record_idx = models.Index('(res_model, res_id)')

    @api.autovacuum
    def _gc_access_token(self):
        self.search([('expiration', '<', self.env.cr.now())]).unlink()

    @api.constrains('expiration')
    def _constraint_expiration(self):
        for access_token in self:
            if access_token.expiration and access_token.expiration < self.env.cr.now():
                raise ValidationError(self.env._('Expiration cannot be in the past'))

    # No depends, we do not want recomputation if value change
    def _compute_token(self):
        for access_token in self:
            if access_token.manual_token:
                access_token.token = access_token.manual_token
                continue

            payload = (
                access_token.id,
                access_token.res_model,
                access_token.res_id,
                access_token.owner_id.id,
            )
            access_token.token = hash_sign(
                self.env, access_token.scope, payload,
                expiration=access_token.expiration,
            )

    def write(self, vals):
        raise UserError(self.env._('Cannot update access tokens'))

    def action_open_record(self):
        self.ensure_one()

        if not (self.res_model and self.res_id):
            return False

        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    @api.private
    def retrieve_from_token(self, scope: str, token: str, *,
        record_id: int | None = None) -> Self:
        """ Retrieve access token record from a token and scope. """
        try:
            payload = verify_hash_signed(self.env, scope, token)

        except ValueError:
            assert record_id, 'A record ID must be provided for the current token format.'
            domain = [
                ('res_id', '=', record_id),
                ('scope', '=', scope),
                ('owner_id', 'in', (False, self.env.uid)),
                '|', ('expiration', '>=', self.env.cr.now()), ('expiration', '=', False),
            ]

        else:
            if payload is None:
                return self.browse()

            access_token_id, *_, owner_id = payload

            if owner_id and owner_id != self.env.uid:
                return self.browse()

            domain = [('id', '=', access_token_id)]

        access_tokens = self.search_fetch(domain)

        return next((
            access_token for access_token in access_tokens
            if consteq(access_token.token, token)
        ), self.browse())


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.private
    def grant_access_token(self, scope: str, *,
        expiration: datetime | timedelta | None = None, owner: BaseModel | None = None,
        _manual_token: str | None = None) -> str:
        """ Generates a token to grant access to record for the given scope.

        :param scope: Access scope associated with the token.
        :param expiration: Optional expiration datetime for the token.
                           Optional duration timedelta for the token.
                           If False, the token does not expire.
        :param owner: Optional single record identifying the token owner.
        :param _manual_token: Optional token value which must be forced.
        :return: Signed access token string.
        """
        if not self.env.is_admin():
            raise AccessError(self.env._("Only administrators can grant access tokens."))

        if isinstance(expiration, timedelta):
            expiration = datetime.now() + expiration

        self.ensure_one()
        access_token = self.env['ir.access.token'].sudo().create({
            'res_model': self._name,
            'res_id': self.id,
            'scope': scope,
            'expiration': expiration,
            'owner_id': owner.id if owner else False,
            'manual_token': _manual_token,
        })

        return access_token.token

    @api.private
    def revoke_access_tokens(self, scope: str, *,
        owners: BaseModel | None = None) -> int:
        """ Ensures that tokens for the records and scope are invalidated. """
        if not self.env.is_admin():
            raise AccessError(self.env._("Only administrators can revoke access tokens."))

        access_tokens = self.env['ir.access.token'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self._ids),
            ('scope', '=', scope),
            ('owner_id', 'in', owners.ids if owners else [False]),
        ])
        if access_tokens:
            access_tokens.unlink()
            _logger.info('User %d revokes access tokens (%s)', self.env.uid, ', '.join(map(str, access_tokens._ids)))
        return len(access_tokens)

    @api.private
    def get_access_token(self, scope: str, *,
        owner: BaseModel | None = None) -> str | Literal[False]:
        """ Retrieve a token for the record and scope. """
        if not self.env.is_admin():
            raise AccessError(self.env._("Only administrators can retrieve access tokens."))

        self.ensure_one()

        access_token = self.env['ir.access.token'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('scope', '=', scope),
            ('owner_id', '=', owner.id if owner else False),
            '|',
                ('expiration', '>=', datetime.now()),
                ('expiration', '=', False),
        ], order='expiration desc nulls first', limit=1)

        return access_token.token  # ``False`` if record does not exist

    @api.model
    @api.private
    def get_record_from_access_token(self, scope: str, token: str, *,
        record_id: int | None = None) -> BaseModel:
        """ Use the token and get the referenced record (sudoed).

        :raises AccessError: If the token is invalid, expired, or does not match
                             the expected scope or payload.
                             If the owner of the token is not correct.
        """
        access_token = self.env['ir.access.token'].sudo().retrieve_from_token(scope, token, record_id=record_id)

        if access_token.res_model != self._name:
            raise AccessError(self.env._('Invalid token'))

        return self.browse(access_token.res_id).sudo()
