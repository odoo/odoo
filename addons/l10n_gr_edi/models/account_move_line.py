from odoo import api, fields, models

from odoo.addons.l10n_gr_edi.models.preferred_classification import (
    CLASSIFICATION_CATEGORY_SELECTION,
    CLASSIFICATION_MAP,
    CLASSIFICATION_TYPE_SELECTION,
    CLASSIFICATION_VAT_SELECTION,
    TAX_EXEMPTION_CATEGORY_SELECTION,
    TYPES_WITH_SEND_EXPENSE,
)
from odoo.tools.sql import column_exists, create_column


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_gr_edi_available_cls_category = fields.Char(compute='_compute_l10n_gr_edi_available_cls_category')
    l10n_gr_edi_available_cls_type = fields.Char(compute='_compute_l10n_gr_edi_available_cls_type')
    l10n_gr_edi_available_cls_vat = fields.Char(compute='_compute_l10n_gr_edi_available_cls_type')
    l10n_gr_edi_need_exemption_category = fields.Boolean(compute='_compute_l10n_gr_edi_need_exemption_category', default=False)

    l10n_gr_edi_detail_type = fields.Selection(
        selection=[('1', '1'), ('2', '2')],
        string='MyDATA Detail Type',
        compute='_compute_l10n_gr_edi_detail_type',
        store=True,
        readonly=False,
    )
    l10n_gr_edi_cls_category = fields.Selection(
        selection=CLASSIFICATION_CATEGORY_SELECTION,
        string='MyDATA Category',
        compute='_compute_l10n_gr_edi_cls_category',
        store=True,
        readonly=False,
    )
    l10n_gr_edi_cls_type = fields.Selection(
        selection=CLASSIFICATION_TYPE_SELECTION,
        string='MyDATA Type',
        compute='_compute_l10n_gr_edi_cls_type',
        store=True,
        readonly=False,
    )
    l10n_gr_edi_cls_vat = fields.Selection(
        selection=CLASSIFICATION_VAT_SELECTION,
        string='MyDATA VAT Classification',
        compute='_compute_l10n_gr_edi_cls_vat',
        store=True,
        readonly=False,
    )
    l10n_gr_edi_tax_exemption_category = fields.Selection(
        selection=TAX_EXEMPTION_CATEGORY_SELECTION,
        string='MyDATA Tax Exemption Category',
        compute='_compute_l10n_gr_edi_tax_exemption_category',
        store=True,
        readonly=False,
    )

    def _auto_init(self):
        """
        Create all compute-stored fields here to avoid MemoryError when initializing on large databases.
        """
        for column_name, column_type in (
            ('l10n_gr_edi_detail_type', 'varchar'),
            ('l10n_gr_edi_cls_category', 'varchar'),
            ('l10n_gr_edi_cls_type', 'varchar'),
            ('l10n_gr_edi_cls_vat', 'varchar'),
            ('l10n_gr_edi_tax_exemption_category', 'varchar'),
        ):
            if not column_exists(self.env.cr, 'account_move_line', column_name):
                create_column(self.env.cr, 'account_move_line', column_name, column_type)

        return super()._auto_init()

    @api.depends('move_id.l10n_gr_edi_inv_type')
    def _compute_l10n_gr_edi_detail_type(self):
        self.l10n_gr_edi_detail_type = False

    @api.depends(
        'move_id.l10n_gr_edi_inv_type',
        'move_id.l10n_gr_edi_correlation_id',
        'l10n_gr_edi_detail_type',
    )
    def _compute_l10n_gr_edi_available_cls_category(self):
        for line in self:
            inv_type = line.move_id.l10n_gr_edi_inv_type

            # we need inv_type to calculate available_cls_category
            if not inv_type or (
                    inv_type
                    and CLASSIFICATION_MAP[inv_type] == 'associate'
                    and not line.move_id.l10n_gr_edi_correlation_id
            ):  # associate inv_type must have a correlation_id, otherwise inv_type is considered empty
                line.l10n_gr_edi_available_cls_category = False
                continue

            if CLASSIFICATION_MAP[inv_type] == 'associate':
                inv_type = line.move_id.l10n_gr_edi_correlation_id.l10n_gr_edi_inv_type

            is_income = (
                line.move_type in ('out_invoice', 'out_refund')
                and inv_type not in TYPES_WITH_SEND_EXPENSE
                and (not line.l10n_gr_edi_detail_type or line.l10n_gr_edi_detail_type == '2')
            )

            line.l10n_gr_edi_available_cls_category = self.env['l10n_gr_edi.preferred_classification']._get_l10n_gr_edi_available_cls_category(
                inv_type=inv_type, category_type='1' if is_income else '2')

    @api.depends('l10n_gr_edi_cls_category', 'move_id.l10n_gr_edi_correlation_id')
    def _compute_l10n_gr_edi_available_cls_type(self):
        for line in self:
            inv_type = line.move_id.l10n_gr_edi_inv_type
            cls_category = line.l10n_gr_edi_cls_category

            if inv_type and CLASSIFICATION_MAP[inv_type] == 'associate' and line.move_id.l10n_gr_edi_correlation_id:
                inv_type = line.move_id.l10n_gr_edi_correlation_id.l10n_gr_edi_inv_type

            if cls_category:
                line.l10n_gr_edi_available_cls_type = self.env['l10n_gr_edi.preferred_classification']._get_l10n_gr_edi_available_cls_type(inv_type, cls_category)
                line.l10n_gr_edi_available_cls_vat = self.env['l10n_gr_edi.preferred_classification']._get_l10n_gr_edi_available_cls_vat(inv_type, cls_category)
            else:
                line.l10n_gr_edi_available_cls_type = False
                line.l10n_gr_edi_available_cls_vat = False

    def _l10n_gr_edi_get_preferred_classification_id(self, with_category=False):
        self.ensure_one()
        if with_category:  # for _compute_l10n_gr_edi_cls_type
            domain = [
                ('l10n_gr_edi_inv_type', '=', self.move_id.l10n_gr_edi_inv_type),
                ('l10n_gr_edi_cls_category', '=', self.l10n_gr_edi_cls_category),
                ('l10n_gr_edi_cls_type', 'in', self.l10n_gr_edi_available_cls_type.split(',')),
            ]
        else:  # for _compute_l10n_gr_edi_cls_category
            domain = [
                ('l10n_gr_edi_inv_type', '=', self.move_id.l10n_gr_edi_inv_type),
                ('l10n_gr_edi_cls_category', 'in', self.l10n_gr_edi_available_cls_category.split(',')),
            ]

        preferred_id = self.env['l10n_gr_edi.preferred_classification']
        # Try to get from the move's fiscal position first
        if self.move_id.fiscal_position_id:
            preferred_id = self.move_id.fiscal_position_id.l10n_gr_edi_preferred_classification_ids.filtered_domain(domain)[:1]
        # If nothing is found, try to get preferred classification from the line's product
        if not preferred_id and self.product_id:
            preferred_id = self.product_id.product_tmpl_id.l10n_gr_edi_preferred_classification_ids.filtered_domain(domain)[:1]

        return preferred_id

    @api.depends(
        'move_id.l10n_gr_edi_inv_type',
        'l10n_gr_edi_available_cls_category',
        'product_id',
    )
    def _compute_l10n_gr_edi_cls_category(self):
        for line in self:
            if not line.l10n_gr_edi_available_cls_category:
                line.l10n_gr_edi_cls_category = False
            elif preferred_id := line._l10n_gr_edi_get_preferred_classification_id():
                line.l10n_gr_edi_cls_category = preferred_id.l10n_gr_edi_cls_category
            elif line.l10n_gr_edi_cls_category and line.l10n_gr_edi_cls_category in line.l10n_gr_edi_available_cls_category:
                line.l10n_gr_edi_cls_category = line.l10n_gr_edi_cls_category
            else:
                line.l10n_gr_edi_cls_category = False

    @api.depends(
        'move_id.l10n_gr_edi_inv_type',
        'l10n_gr_edi_available_cls_type',
        'product_id',
    )
    def _compute_l10n_gr_edi_cls_type(self):
        for line in self:
            if not line.l10n_gr_edi_available_cls_type:
                line.l10n_gr_edi_cls_type = False
            elif preferred_id := line._l10n_gr_edi_get_preferred_classification_id(with_category=True):
                line.l10n_gr_edi_cls_type = preferred_id.l10n_gr_edi_cls_type
            elif line.l10n_gr_edi_cls_type and line.l10n_gr_edi_cls_type in line.l10n_gr_edi_available_cls_type:
                line.l10n_gr_edi_cls_type = line.l10n_gr_edi_cls_type
            else:
                line.l10n_gr_edi_cls_type = False

    @api.depends('l10n_gr_edi_available_cls_vat')
    def _compute_l10n_gr_edi_cls_vat(self):
        self.l10n_gr_edi_cls_vat = False

    @api.depends('tax_ids')
    def _compute_l10n_gr_edi_need_exemption_category(self):
        for line in self:
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            line.l10n_gr_edi_need_exemption_category = len(taxes) == 1 and taxes.amount == 0

    @api.depends('tax_ids')
    def _compute_l10n_gr_edi_tax_exemption_category(self):
        for line in self:
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            if line.move_id.country_code == 'GR' and len(taxes) == 1 and taxes.amount == 0:
                if line.l10n_gr_edi_tax_exemption_category:
                    line.l10n_gr_edi_tax_exemption_category = line.l10n_gr_edi_tax_exemption_category
                else:
                    line.l10n_gr_edi_tax_exemption_category = taxes.l10n_gr_edi_default_tax_exemption_category or '1'
            else:
                line.l10n_gr_edi_tax_exemption_category = False
