from odoo import api, models


class BenefitType(models.Model):
    _inherit = 'hr.benefit.type'

    @api.model
    def _load_from_xmlid(self, *xmlids):
        benefit_types = self.env['hr.benefit.type']
        for xmlid in xmlids:
            benefit_types |= self.env.ref(xmlid, raise_if_not_found=False)
        return benefit_types
