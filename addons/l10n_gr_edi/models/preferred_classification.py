from odoo import fields, models, api
from odoo.addons.l10n_gr_edi.models.classification_data import INVOICE_TYPES_SELECTION, \
    CLASSIFICATION_CATEGORY_SELECTION, CLASSIFICATION_TYPE_SELECTION, CLASSIFICATION_MAP, \
    _get_l10n_gr_edi_available_cls_category, _get_l10n_gr_edi_available_cls_type


class PreferredClassification(models.Model):
    _name = 'l10n_gr_edi.preferred_classification'
    _description = 'Preferred myDATA classification combinations for a particular product'
    _order = 'priority DESC, id DESC'

    # Inverse fields
    product_template_id = fields.Many2one('product.template')
    fiscal_position_id = fields.Many2one('account.fiscal.position')

    priority = fields.Integer('Priority', default=1)
    l10n_gr_edi_inv_type = fields.Selection(
        selection=INVOICE_TYPES_SELECTION,
        string='MyDATA Invoice Type',
    )
    l10n_gr_edi_cls_category = fields.Selection(
        selection=CLASSIFICATION_CATEGORY_SELECTION,
        string='MyDATA Category',
    )
    l10n_gr_edi_cls_type = fields.Selection(
        selection=CLASSIFICATION_TYPE_SELECTION,
        string='MyDATA Type',
    )

    l10n_gr_edi_available_inv_type = fields.Char(default=','.join(CLASSIFICATION_MAP.keys()))
    l10n_gr_edi_available_cls_category = fields.Char(compute='_compute_l10n_gr_edi_available_cls_category')
    l10n_gr_edi_available_cls_type = fields.Char(compute='_compute_l10n_gr_edi_available_cls_type')

    @api.onchange('l10n_gr_edi_available_cls_category')
    def _onchange_reset_cls_category(self):
        for line in self:
            line.l10n_gr_edi_cls_category = False

    @api.onchange('l10n_gr_edi_available_cls_type')
    def _onchange_reset_cls_type(self):
        for line in self:
            line.l10n_gr_edi_cls_type = False

    @api.depends('l10n_gr_edi_inv_type')
    def _compute_l10n_gr_edi_available_cls_category(self):
        for record in self:
            record.l10n_gr_edi_available_cls_category = _get_l10n_gr_edi_available_cls_category(record.l10n_gr_edi_inv_type)

    @api.depends('l10n_gr_edi_inv_type', 'l10n_gr_edi_cls_category')
    def _compute_l10n_gr_edi_available_cls_type(self):
        for record in self:
            record.l10n_gr_edi_available_cls_type = _get_l10n_gr_edi_available_cls_type(
                inv_type=record.l10n_gr_edi_inv_type, cls_category=record.l10n_gr_edi_cls_category)
