from odoo import models, fields, api
from odoo.addons.l10n_gr_edi.models.classification_data import (
    CLASSIFICATION_MAP, CLASSIFICATION_CATEGORY_SELECTION, CLASSIFICATION_TYPE_SELECTION, CLASSIFICATION_VAT_SELECTION,
    TAX_EXEMPTION_CATEGORY_SELECTION, TYPES_WITH_SEND_EXPENSE,
    _get_l10n_gr_edi_available_cls_type, _get_l10n_gr_edi_available_cls_vat, _get_l10n_gr_edi_available_cls_category,
)


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
    )

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

            is_income = (line.move_type in ('out_invoice', 'out_refund') and
                         inv_type not in TYPES_WITH_SEND_EXPENSE and
                         (not line.l10n_gr_edi_detail_type or line.l10n_gr_edi_detail_type == '2'))

            line.l10n_gr_edi_available_cls_category = _get_l10n_gr_edi_available_cls_category(
                inv_type=inv_type, category_type='1' if is_income else '2')

    @api.depends('l10n_gr_edi_cls_category')
    def _compute_l10n_gr_edi_available_cls_type(self):
        for line in self:
            inv_type = line.move_id.l10n_gr_edi_inv_type
            cls_category = line.l10n_gr_edi_cls_category

            if inv_type and CLASSIFICATION_MAP[inv_type] == 'associate' and line.move_id.l10n_gr_edi_correlation_id:
                inv_type = line.move_id.l10n_gr_edi_correlation_id.l10n_gr_edi_inv_type

            if cls_category:
                line.l10n_gr_edi_available_cls_type = _get_l10n_gr_edi_available_cls_type(inv_type, cls_category)
                line.l10n_gr_edi_available_cls_vat = _get_l10n_gr_edi_available_cls_vat(inv_type, cls_category)
            else:
                line.l10n_gr_edi_available_cls_type = False
                line.l10n_gr_edi_available_cls_vat = False

    def _l10n_gr_edi_get_preferred_classification_id(self, with_category=False):
        self.ensure_one()
        if with_category:  # for _compute_l10n_gr_edi_cls_type
            common_domain = [
                ('l10n_gr_edi_inv_type', '=', self.move_id.l10n_gr_edi_inv_type),
                ('l10n_gr_edi_cls_category', '=', self.l10n_gr_edi_cls_category),
                ('l10n_gr_edi_cls_type', 'in', self.l10n_gr_edi_available_cls_type.split(',')),
            ]
        else:  # for _compute_l10n_gr_edi_cls_category
            common_domain = [
                ('l10n_gr_edi_inv_type', '=', self.move_id.l10n_gr_edi_inv_type),
                ('l10n_gr_edi_cls_category', 'in', self.l10n_gr_edi_available_cls_category.split(',')),
            ]
        with_product_domain = common_domain + [('product_template_id', '=', self.product_id.product_tmpl_id.id)]
        with_fiscal_domain = common_domain + [('fiscal_position_id', '=', self.move_id.fiscal_position_id.id)]

        preferred_id = self.env['l10n_gr_edi.preferred_classification']
        # Try to get preferred classification from the line's product first
        if self.product_id:
            preferred_id = self.env['l10n_gr_edi.preferred_classification'].search(with_product_domain, limit=1)
        # If nothing is found, try to get from the move's fiscal position
        if not preferred_id and self.move_id.fiscal_position_id:
            preferred_id = self.env['l10n_gr_edi.preferred_classification'].search(with_fiscal_domain, limit=1)

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
            line.l10n_gr_edi_need_exemption_category = len(line.tax_ids) == 1 and line.tax_ids.amount == 0

    @api.depends('tax_ids')
    def _compute_l10n_gr_edi_tax_exemption_category(self):
        for line in self:
            if len(line.tax_ids) == 1 and line.tax_ids.amount == 0:
                if line._origin.l10n_gr_edi_tax_exemption_category:
                    line.l10n_gr_edi_tax_exemption_category = line.l10n_gr_edi_tax_exemption_category
                else:
                    line.l10n_gr_edi_tax_exemption_category = line.tax_ids.l10n_gr_edi_default_tax_exemption_category or '1'
            else:
                line.l10n_gr_edi_tax_exemption_category = False
