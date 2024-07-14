# coding: utf-8

from odoo import fields, models, api
from odoo.addons.l10n_mx_edi.models.l10n_mx_edi_document import USAGE_SELECTION


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    l10n_mx_edi_cfdi_to_public = fields.Boolean(
        string="CFDI to public",
        compute='_compute_l10n_mx_edi_cfdi_to_public',
        readonly=False,
        store=True,
        help="Send the CFDI with recipient 'publico en general'",
    )

    l10n_mx_edi_payment_method_id = fields.Many2one(
        comodel_name='l10n_mx_edi.payment.method',
        string="Payment Way",
        compute='_compute_l10n_mx_edi_payment_method_id',
        store=True,
        readonly=False,
        help="Indicates the way the invoice was/will be paid, where the options could be: "
             "Cash, Nominal Check, Credit Card, etc. Leave empty if unkown and the XML will show 'Unidentified'.",
    )

    l10n_mx_edi_usage = fields.Selection(
        selection=USAGE_SELECTION,
        string="Usage",
        compute="_compute_l10n_mx_edi_usage",
        store=True,
        readonly=False,
        tracking=True,
        help="The code that corresponds to the use that will be made of the receipt by the recipient.",
    )

    @api.depends('partner_id')
    def _compute_l10n_mx_edi_payment_method_id(self):
        default_payment_method_id = self.env.ref('l10n_mx_edi.payment_method_otros', raise_if_not_found=False)
        for order in self:
            if order.country_code == 'MX':
                order.l10n_mx_edi_payment_method_id = (
                    order.partner_id.l10n_mx_edi_payment_method_id or
                    order.l10n_mx_edi_payment_method_id or
                    default_payment_method_id
                )
            else:
                order.l10n_mx_edi_payment_method_id = False

    @api.depends('partner_id')
    def _compute_l10n_mx_edi_usage(self):
        for order in self:
            if order.country_code == 'MX':
                order.l10n_mx_edi_usage = (
                    order.partner_id.l10n_mx_edi_usage or
                    order.l10n_mx_edi_usage or
                    'G03'
                )
            else:
                order.l10n_mx_edi_usage = False

    @api.depends('company_id')
    def _compute_l10n_mx_edi_cfdi_to_public(self):
        for order in self:
            order.l10n_mx_edi_cfdi_to_public = False

    def _prepare_invoice(self):
        # OVERRIDE
        vals = super()._prepare_invoice()
        vals['l10n_mx_edi_cfdi_to_public'] = self.l10n_mx_edi_cfdi_to_public
        vals['l10n_mx_edi_usage'] = self.l10n_mx_edi_usage
        vals['l10n_mx_edi_payment_method_id'] = self.l10n_mx_edi_payment_method_id.id
        return vals
