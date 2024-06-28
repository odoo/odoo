from odoo import models, fields, api
from odoo.addons.l10n_gr_edi.models.classification_data import (
    CLASSIFICATION_MAP, CLASSIFICATION_CATEGORY_SELECTION, CLASSIFICATION_TYPE_SELECTION, CLASSIFICATION_VAT_SELECTION,
    TAX_EXEMPTION_CATEGORY_SELECTION, TYPES_WITH_SEND_EXPENSE,
    _get_l10n_gr_edi_available_cls_type, _get_l10n_gr_edi_available_cls_vat, _get_l10n_gr_edi_available_cls_category,
)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_gr_edi_cls_category = fields.Selection(
        selection=CLASSIFICATION_CATEGORY_SELECTION,
        string='MyDATA Category',
    )
    l10n_gr_edi_cls_type = fields.Selection(
        selection=CLASSIFICATION_TYPE_SELECTION,
        string='MyDATA Type',
    )
    l10n_gr_edi_cls_vat = fields.Selection(
        selection=CLASSIFICATION_VAT_SELECTION,
        string='MyDATA VAT Classification',
    )
    l10n_gr_edi_available_cls_category = fields.Char(compute='_compute_l10n_gr_edi_available_cls_category')
    l10n_gr_edi_available_cls_type = fields.Char(compute='_compute_l10n_gr_edi_available_cls_type')
    l10n_gr_edi_available_cls_vat = fields.Char(compute='_compute_l10n_gr_edi_available_cls_type')
    l10n_gr_edi_tax_exemption_category = fields.Selection(
        selection=TAX_EXEMPTION_CATEGORY_SELECTION,
        string='MyDATA Tax Exemption Category',
        compute='_compute_l10n_gr_edi_tax_exemption_category',
        store=True,
    )
    l10n_gr_edi_need_exemption_category = fields.Boolean(
        compute='_compute_l10n_gr_edi_need_exemption_category',
        default=False,
    )
    l10n_gr_edi_detail_type = fields.Selection(
        selection=[('1', '1'), ('2', '2')],
        string='MyDATA Detail Type',
    )

    def _l10n_gr_edi_get_preferred_classification(self, with_cls_category=False):
        self.ensure_one()
        if with_cls_category:
            category_domain = ('l10n_gr_edi_cls_category', '=', self.l10n_gr_edi_cls_category)
        else:
            category_domain = ('l10n_gr_edi_cls_category', 'in', self.l10n_gr_edi_available_cls_category and
                               self.l10n_gr_edi_available_cls_category.split(',') or ())

        # Try to get preferred classification from move's fiscal position first
        preferred_classification = self.env['l10n_gr_edi.preferred_classification'].search([
            ('fiscal_position_id', '=', self.move_id.fiscal_position_id.id),
            ('fiscal_position_id', '!=', False),
            ('l10n_gr_edi_inv_type', '=', self.move_id.l10n_gr_edi_inv_type),
            category_domain,
        ], limit=1)

        if not preferred_classification:
            # If nothing is found, get preferred classification from line's product template
            preferred_classification = self.env['l10n_gr_edi.preferred_classification'].search([
                ('product_template_id', '=', self.product_id.product_tmpl_id.id),
                ('product_template_id', '!=', False),
                ('l10n_gr_edi_inv_type', '=', self.move_id.l10n_gr_edi_inv_type),
                category_domain,
            ], limit=1)

        return preferred_classification

    @api.onchange('product_id', 'l10n_gr_edi_available_cls_category')
    def _onchange_update_classification(self):
        for line in self:
            preferred_classification = line._l10n_gr_edi_get_preferred_classification()
            line.l10n_gr_edi_cls_category = preferred_classification.l10n_gr_edi_cls_category
            line.l10n_gr_edi_cls_type = preferred_classification.l10n_gr_edi_cls_type

    @api.onchange('l10n_gr_edi_available_cls_type')
    def _onchange_get_preferred_product_cls_type(self):
        for line in self:
            preferred_classification = line._l10n_gr_edi_get_preferred_classification(with_cls_category=True)
            line.l10n_gr_edi_cls_type = preferred_classification.l10n_gr_edi_cls_type

    @api.onchange('l10n_gr_edi_available_cls_vat')
    def _onchange_reset_cls_vat(self):
        for line in self:
            line.l10n_gr_edi_cls_vat = False

    @api.depends(
        'move_id.l10n_gr_edi_inv_type',
        'move_id.l10n_gr_edi_correlation_id',
        'l10n_gr_edi_detail_type',
    )
    def _compute_l10n_gr_edi_available_cls_category(self):
        for line in self:
            inv_type = line.move_id.l10n_gr_edi_inv_type

            if not inv_type or (
                    inv_type
                    and CLASSIFICATION_MAP[inv_type] == 'associate'
                    and not line.move_id.l10n_gr_edi_correlation_id
            ):
                line.l10n_gr_edi_available_cls_category = False
                continue

            if CLASSIFICATION_MAP[inv_type] == 'associate':
                inv_type = line.move_id.l10n_gr_edi_correlation_id.l10n_gr_edi_inv_type

            is_income = (line.move_type in ('out_invoice', 'out_refund') and
                         inv_type not in TYPES_WITH_SEND_EXPENSE and
                         (not line.l10n_gr_edi_detail_type or line.l10n_gr_edi_detail_type == '2'))

            line.l10n_gr_edi_available_cls_category = _get_l10n_gr_edi_available_cls_category(
                inv_type=inv_type, category_type='1' if is_income else '2')

    @api.depends('l10n_gr_edi_available_cls_category', 'l10n_gr_edi_cls_category')
    def _compute_l10n_gr_edi_available_cls_type(self):
        for line in self:
            inv_type = line.move_id.l10n_gr_edi_inv_type
            cls_category = line.l10n_gr_edi_cls_category

            if inv_type and CLASSIFICATION_MAP[inv_type] == 'associate' and line.move_id.l10n_gr_edi_correlation_id:
                inv_type = line.move_id.l10n_gr_edi_correlation_id.l10n_gr_edi_inv_type

            line.l10n_gr_edi_available_cls_type = _get_l10n_gr_edi_available_cls_type(inv_type, cls_category)
            line.l10n_gr_edi_available_cls_vat = _get_l10n_gr_edi_available_cls_vat(inv_type, cls_category)

    @api.depends('tax_ids')
    def _compute_l10n_gr_edi_need_exemption_category(self):
        for line in self:
            line.l10n_gr_edi_need_exemption_category = len(line.tax_ids) == 1 and line.tax_ids.amount == 0

    @api.depends('tax_ids')
    def _compute_l10n_gr_edi_tax_exemption_category(self):
        for line in self:
            if len(line.tax_ids) == 1 and line.tax_ids.amount == 0:
                line.l10n_gr_edi_tax_exemption_category = line.tax_ids.l10n_gr_edi_default_tax_exemption_category or '1'
            else:
                line.l10n_gr_edi_tax_exemption_category = False
