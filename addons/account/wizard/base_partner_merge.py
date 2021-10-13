from odoo import models


class MergePartnerAutomatic(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def _get_summable_fields(self):
        """ Add to summable fields list, fields created in this module.
        """
        res = super()._get_summable_fields()
        res += ['customer_rank', 'supplier_rank']
        return res
