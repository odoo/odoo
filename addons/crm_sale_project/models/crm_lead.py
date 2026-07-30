from odoo import models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def _get_project_create_from_lead_context(self):
        return {
            **super()._get_project_create_from_lead_context(),
            'default_allow_billable': True,
            'default_reinvoiced_sale_order_id': (
                self.order_ids[0].id if self.order_ids else False
            ),
        }

    def _prepare_opportunity_quotation_context(self):
        context = super()._prepare_opportunity_quotation_context()
        context.update({
            'is_sale_order': True,
            'default_project_id': self.sudo().project_ids[-1:].id,
        })
        return context
