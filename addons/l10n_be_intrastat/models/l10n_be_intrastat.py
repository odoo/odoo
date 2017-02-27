# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    intrastat_transaction_id = fields.Many2one('l10n_be_intrastat.transaction', string='Intrastat Transaction Type',
                                               help="Intrastat nature of transaction")


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    incoterm_id = fields.Many2one('stock.incoterms', string='Incoterm',
        help="International Commercial Terms are a series of predefined commercial terms "
             "used in international transactions.")
    transport_mode_id = fields.Many2one('l10n_be_intrastat.transport_mode', string='Intrastat Transport Mode')
    intrastat_country_id = fields.Many2one('res.country', string='Intrastat Country',
        help='Intrastat country, delivery for sales, origin for purchases',
        domain=[('intrastat', '=', True)])


class IntrastatRegion(models.Model):
    _name = 'l10n_be_intrastat.region'

    code = fields.Char(required=True)
    country_id = fields.Many2one('res.country', string='Country')
    name = fields.Char(translate=True)
    description = fields.Char()

    _sql_constraints = [
        ('l10n_be_intrastat_regioncodeunique', 'UNIQUE (code)', 'Code must be unique.'),
    ]


class IntrastatTransaction(models.Model):
    _name = 'l10n_be_intrastat.transaction'
    _rec_name = 'code'

    code = fields.Char(required=True, readonly=True)
    description = fields.Text(readonly=True)

    _sql_constraints = [
        ('l10n_be_intrastat_trcodeunique', 'UNIQUE (code)', 'Code must be unique.'),
    ]


class IntrastatTransportMode(models.Model):
    _name = 'l10n_be_intrastat.transport_mode'

    code = fields.Char(required=True, readonly=True)
    name = fields.Char(string='Description', readonly=True)

    _sql_constraints = [
        ('l10n_be_intrastat_trmodecodeunique', 'UNIQUE (code)', 'Code must be unique.'),
    ]


class ProductCategory(models.Model):
    _inherit = "product.category"

    intrastat_id = fields.Many2one('report.intrastat.code', string='Intrastat Code')

    @api.multi
    def get_intrastat_recursively(self):
        """ Recursively search in categories to find an intrastat code id
        """
        res = None
        if self.intrastat_id:
            res = self.intrastat_id.id
        elif self.parent_id:
            res = self.parent_id.get_intrastat_recursively()
        return res


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    def get_intrastat_recursively(self):
        """ Recursively search in categories to find an intrastat code id
        """
        res = None
        if self.intrastat_id:
            res = self.intrastat_id.id
        elif self.categ_id:
            res = self.categ_id.get_intrastat_recursively()
        return res


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _prepare_invoice(self):
        """
        copy incoterm from purchase order to invoice
        """
        invoice = super(PurchaseOrder, self)._prepare_invoice()
        if self.incoterm_id:
            invoice['incoterm_id'] = self.incoterm_id.id
        #Try to determine products origin
        if self.partner_id.country_id:
            #It comes from vendor
            invoice['intrastat_country_id'] = self.partner_id.country_id.id
        return invoice


class ReportIntrastatCode(models.Model):
    _inherit = "report.intrastat.code"

    description = fields.Text(string='Description', translate=True)


class ResCompany(models.Model):
    _inherit = "res.company"

    region_id = fields.Many2one('l10n_be_intrastat.region', string='Intrastat region')
    transport_mode_id = fields.Many2one('l10n_be_intrastat.transport_mode',
                                             string='Default transport mode')
    incoterm_id = fields.Many2one('stock.incoterms', string='Default incoterm for Intrastat',
                                       help="International Commercial Terms are a series of "
                                            "predefined commercial terms used in international "
                                            "transactions.")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        """
        copy incoterm from sales order to invoice
        """
        invoice = super(SaleOrder, self)._prepare_invoice()
        if self.incoterm:
            invoice['incoterm_id'] = self.incoterm.id
        # Guess products destination
        if self.partner_shipping_id.country_id:
            invoice['intrastat_country_id'] = self.partner_shipping_id.country_id.id
        elif self.partner_id.country_id:
            invoice['intrastat_country_id'] = self.partner_id.country_id.id
        elif self.partner_invoice_id.country_id:
            invoice['intrastat_country_id'] = self.partner_invoice_id.country_id.id
        return invoice


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    region_id = fields.Many2one('l10n_be_intrastat.region', string='Intrastat region')

    def get_regionid_from_locationid(self, location):
        location_ids = location.search([('parent_left', '<=', location.parent_left), ('parent_right', '>=', location.parent_right)])
        warehouses = self.search([('lot_stock_id', 'in', location_ids.ids), ('region_id', '!=', False)], limit=1)
        if warehouses:
            return warehouses.region_id.id
        return None
