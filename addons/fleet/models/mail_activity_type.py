from odoo import api, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    @api.model
    def _get_xmlid_model_link(self):
        link = super()._get_xmlid_model_link()
        link['fleet.mail_act_fleet_contract_to_renew'] = 'fleet.vehicle.log.contract'
        return link
