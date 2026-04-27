from odoo import api, fields, models
from odoo.tools.sql import column_exists, create_column


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_co_dian_mandate_contract = fields.Boolean(
        string='Mandate Contract',
        compute='_compute_l10n_co_dian_mandate_contract',
        store=True,
        readonly=False
    )

    @api.depends('type')
    def _compute_l10n_co_dian_mandate_contract(self):
        for product in self:
            if product.type != 'service':
                product.l10n_co_dian_mandate_contract = False

    def _auto_init(self):
        """
        Create all compute-stored fields here to avoid MemoryError when initializing on large databases.
        """
        if not column_exists(self.env.cr, 'account_move', 'l10n_co_dian_mandate_contract'):
            create_column(self.env.cr, 'account_move', 'l10n_co_dian_mandate_contract', 'bool')

        return super()._auto_init()
