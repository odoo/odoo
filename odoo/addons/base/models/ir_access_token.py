# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.models import BaseModel
from odoo.tools.misc import consteq, hash_sign, verify_hash_signed


class IrAccessToken(models.Model):
    _name = 'ir.access.token'
    _description = 'Access Token'

    res_model = fields.Char('Resource Model', required=True)
    res_id = fields.Integer('Resource ID', required=True)
    scope = fields.Char('Scope', required=True)
    expiration = fields.Datetime('Expiration')
    owner_id = fields.Many2one('res.users')
    # Tokens are not stored.
    # However, it is necessary to maintain existing tokens as valid
    # and retain the ability to force the value of a token.
    manual_token = fields.Char('Manual Token', groups=fields.NO_ACCESS, index='btree_not_null')
    token = fields.Char('Token', compute='_compute_token', groups=fields.NO_ACCESS)

    _res_record_idx = models.Index('(res_model, res_id)')

    @api.autovacuum
    def _gc_access_token(self):
        self.search([('expiration', '<', fields.Datetime.now())]).unlink()

    @api.constrains('expiration')
    def _constraint_expiration(self):
        for access_token in self:
            if access_token.expiration and access_token.expiration < fields.Datetime.now():
                raise ValidationError(_('Expiration cannot be in the past'))

    @api.depends_context('uid')  # Invalidate the cache if the user changes
    @api.depends('manual_token')
    def _compute_token(self):
        # A ``MissingError`` will be raised if access token doesn't exist
        for access_token in self:
            if access_token.manual_token:
                access_token.token = access_token.manual_token
                continue
            # It is necessary to embedded the access token id in the payload.
            # Indeed, if there are two tokens that can grant access to the same
            # record, it must be possible to invalidate only one of the two.
            payload = (access_token.id, access_token.res_model, access_token.res_id, access_token.owner_id.id)
            access_token.token = hash_sign(
                self.env, access_token.scope, payload,
                expiration=access_token.expiration,
            )

    def write(self, vals):
        # To update an access token invalidate it
        raise UserError(_('Cannot update access tokens'))

    @api.model
    @api.private
    def use(self, token: str, scope: str) -> BaseModel:
        """ Use the token and get the referenced record (sudoed).

        :raises AccessError: If the token is invalid, expired, or does not match
                             the expected scope or payload.
                             If the owner of the token is not correct.
        """
        try:
            payload = verify_hash_signed(self.env, scope, token)  # Expiration is verified
        except ValueError:
            # The token is not in the correct format (maybe manually entered token)
            access_token = self.search_fetch([
                ('manual_token', '=', token),
                ('scope', '=', scope),
                ('owner_id', 'in', (False, self.env.uid)),
                '|',
                    ('expiration', '>=', fields.Datetime.now()),
                    ('expiration', '=', False),
            ], limit=1)
        else:
            if payload is None:  # Expired token
                raise AccessError(_('Invalid token'))
            access_token_id, *_rest, owner_id = payload
            access_token = self.browse(access_token_id)
            # Ensure correct owner
            if owner_id and owner_id != self.env.uid:
                raise AccessError(_('Invalid token'))
            # Ensure the access_token record exists (+ fetch)
            try:
                access_token.res_model
            except MissingError:
                raise AccessError(_('Invalid token'))

        # Recompute token and assert with the token used ensures the integrity
        # of values in the database. This ensures that if the data in the
        # database is altered, it does not change the intended behaviour of the
        # token.
        if not consteq(access_token.token or '', token):
            raise AccessError(_('Invalid token'))

        # Return the referenced record in sudo
        return self.env[access_token.res_model].browse(access_token.res_id).sudo()
