from odoo import fields, models
from odoo.exceptions import UserError


class OauthResource(models.Model):
    _name = 'oauth.resource'
    _description = 'OAuth Protected Resource'

    name = fields.Char(required=True, readonly=True)
    label = fields.Char(required=True, help="Shown to the user on the consent screen.")
    access_token_scope = fields.Char(
        required=True,
        readonly=True,
        help="Value written to res.users.apikeys.scope for credentials generated under this resource.",
    )
    active = fields.Boolean(default=True)

    _name_unique = models.Constraint('unique(name)', "The resource name must be unique.")

    def write(self, vals):
        immutable_fields = ["name", "access_token_scope"]
        if any(field_name in vals for field_name in immutable_fields):
            raise UserError(self.env._("The %(field_names)s are can't be changed.", field_names=", ".join(immutable_fields)))
        res = super().write(vals)
        if 'active' in vals and not vals['active']:
            clients = self.env['oauth.client'].search([('resource_id', 'in', self.ids)])
            clients.write({'active': vals['active']})
        return res
