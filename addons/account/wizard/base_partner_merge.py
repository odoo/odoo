from odoo import models


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def _get_summable_fields(self):
        """Add to summable fields list, fields created in this module.
         - customer_rank and supplier_rank will have a better ranking for the merged partner
        """
        return super()._get_summable_fields() + ['customer_rank', 'supplier_rank']
