# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
import openerp

# ----------------------------------------------------------
# Models
# ----------------------------------------------------------


class voip_configurator(models.Model):
    _name = 'voip.configurator'

    @api.model
    def get_pbx_config(self):
        return {'pbx_ip': self.env['ir.config_parameter'].get_param('crm.voip.pbx_ip'),
                'wsServer': self.env['ir.config_parameter'].get_param('crm.voip.wsServer'),
                'login': self.env.user[0].sip_login,
                'password': self.env.user[0].sip_password,
                'physical_phone': self.env.user[0].sip_physicalPhone,
                'always_transfert': self.env.user[0].sip_always_transfert,
                'ring_number': self.env.user[0].sip_ring_number}

    #not deleted yet waiting to be sure about the error management.
    # @api.model
    # def error_config(self):
    #     print(self.env.user[0].groups_id)
    #     action = self.env.ref('base.action_res_users_my')
    #     msg = "Wrong configuration for the call. Verify the user's configuration.\nIf you still have issues, please contact your administrator";
    #     raise openerp.exceptions.RedirectWarning(_(msg), action.id, _('Configure The User Now'))

class res_users(models.Model):
    _inherit = 'res.users'

    sip_login = fields.Char("SIP Login / Browser's Extension")
    sip_password = fields.Char('SIP Password')
    sip_physicalPhone = fields.Char("Physical Phone's Number")
    sip_always_transfert = fields.Boolean("Always redirect to physical phone", default=False)
    sip_ring_number = fields.Integer("Number of ringing", default=6, help="The number of ringing before cancelling the call")