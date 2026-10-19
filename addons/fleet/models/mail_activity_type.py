from odoo import api, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    @api.model
    def _get_model_info_by_xmlid(self):
        info = super()._get_model_info_by_xmlid()
        # used notably to generate activities only one time using a cron
        info['fleet.mail_act_fleet_contract_to_renew'] = {
            'res_model': 'fleet.vehicle.log.contract',
            'unlink': False,
        }
        return info
