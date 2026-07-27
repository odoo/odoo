from odoo import fields, models
from odoo.exceptions import AccessDenied


class OauthResource(models.Model):
    _inherit = 'oauth.resource'

    allowed_group_ids = fields.Many2many(
        'res.groups',
        help="The user needs to be in at least one of these access groups to be able to use OAuth under this resource.",
        required=True,
    )

    def _check_user_access(self, user):
        self.ensure_one()
        if not (self.allowed_group_ids & user.all_group_ids):
            raise AccessDenied(self.env._(
                "You do not have the required access rights for the '%(resource_name)s' resource.",
                resource_name=self.name
            ))
