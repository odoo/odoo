# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class RecruitmentPlatform(models.Model):
    _name = 'hr.recruitment.platform'
    _description = 'Recruitment Platform'
    _inherit = ['avatar.mixin']

    name = fields.Char(string="Name", required=True)
    website = fields.Char(string="Website")

    # crud pricing
    price_to_publish = fields.Float(string="Price to Publish")
    price_to_get = fields.Float(string="Price to Get")
    price_to_update = fields.Float(string="Price to Update")
    price_to_delete = fields.Float(string="Price to Delete")

    def _post_api_call(self, data):
        # To be overridden by the specific platform
        return {
            'data': {},
            'status': _('failure'),
            'message': _(
                'No API call defined for this platform '
                'please contact the administrator'
            )
        }
