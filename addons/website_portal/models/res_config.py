from openerp import api, fields, models
from openerp.tools.safe_eval import safe_eval


class website_portal_config(models.TransientModel):
    _inherit = 'base.config.settings'

    address_validation = fields.Boolean('Verify addresses entered on the frontend using USPS (United States only)')
    mandatory_validation = fields.Boolean('Make validation mandatory when registering an address')
    usps_username = fields.Char('USPS API Username')
    usps_password = fields.Char('USPS API Password')

    @api.model
    def set_website_portal(self, ids):
        params = self.env['ir.config_parameter']
        myself = self.browse(ids[0])
        params.set_param('website_portal.address_validation', repr(myself.address_validation), groups=['base.group_system'])
        params.set_param('website_portal.mandatory_validation', repr(myself.mandatory_validation), groups=['base.group_system'])
        params.set_param('website_portal.usps_username', myself.usps_username or '', groups=['base.group_system'])
        params.set_param('website_portal.usps_password', myself.usps_password or '', groups=['base.group_system'])

    @api.model
    def get_default_all(self, ids):
        params = self.env['ir.config_parameter']
        usps_username = params.get_param('website_portal.usps_username', default='')
        usps_password = params.get_param('website_portal.usps_password', default='')
        address_validation = safe_eval(params.get_param('website_portal.address_validation', default="False"))
        mandatory_validation = safe_eval(params.get_param('website_portal.mandatory_validation', default="False"))
        return dict(usps_username=usps_username, usps_password=usps_password,
                    address_validation=address_validation, mandatory_validation=mandatory_validation)
