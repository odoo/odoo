# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models, api


class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"

    intrastat_transaction_id = fields.Many2one('l10n_be_intrastat.transaction', 'Intrastat Transaction Type',
                                               help="Intrastat nature of transaction")


class account_invoice(models.Model):
    _inherit = "account.invoice"

    incoterm_id = fields.Many2one('stock.incoterms', 'Incoterm',
        help="International Commercial Terms are a series of predefined commercial terms "
             "used in international transactions.")
    transport_mode_id = fields.Many2one('l10n_be_intrastat.transport_mode', 'Intrastat Transport Mode')
    intrastat_country_id = fields.Many2one('res.country', 'Intrastat Country',
        help='Intrastat country, delivery for sales, origin for purchases',
        domain=[('intrastat', '=', True)])


class intrastat_region(models.Model):
    _name = 'l10n_be_intrastat.region'

    code = fields.Char('Code', required=True)
    country_id = fields.Many2one('res.country', 'Country')
    name = fields.Char('Name', translate=True)
    description = fields.Char('Description')

    _sql_constraints = [
        ('l10n_be_intrastat_regioncodeunique', 'UNIQUE (code)', 'Code must be unique.'),
    ]


class intrastat_transaction(models.Model):
    _name = 'l10n_be_intrastat.transaction'
    _rec_name = 'code'

    code = fields.Char('Code', required=True, readonly=True)
    description = fields.Text('Description', readonly=True)

    _sql_constraints = [
        ('l10n_be_intrastat_trcodeunique', 'UNIQUE (code)', 'Code must be unique.'),
    ]


class intrastat_transport_mode(models.Model):
    _name = 'l10n_be_intrastat.transport_mode'

    code = fields.Char('Code', required=True, readonly=True)
    name = fields.Char('Description', readonly=True)

    _sql_constraints = [
        ('l10n_be_intrastat_trmodecodeunique', 'UNIQUE (code)', 'Code must be unique.'),
    ]


class product_category(models.Model):
    _name = "product.category"
    _inherit = "product.category"

    intrastat_id = fields.Many2one('report.intrastat.code', 'Intrastat Code')

    @api.multi
    def get_intrastat_recursively(self):
        """ Recursively search in categories to find an intrastat code id
        """
        if self.intrastat_id:
            res = self.intrastat_id.id
        elif self.parent_id:
            res = self.parent_id.get_intrastat_recursively()
        else:
            res = None
        return res


class product_product(models.Model):
    _name = "product.product"
    _inherit = "product.product"

    @api.multi
    def get_intrastat_recursively(self):
        """ Recursively search in categories to find an intrastat code id
        """
        if self.intrastat_id:
            res = self.intrastat_id.id
        elif self.categ_id:
            res = self.categ_id.get_intrastat_recursively()
        else:
            res = None
        return res


class purchase_order(models.Model):
    _inherit = "purchase.order"

    def _prepare_invoice(self):
        """
        copy incoterm from purchase order to invoice
        """
        invoice = super(purchase_order, self)._prepare_invoice()
        if self.incoterm_id:
            invoice['incoterm_id'] = self.incoterm_id.id
        #Try to determine products origin
        if self.partner_id.country_id:
            #It comes from vendor
            invoice['intrastat_country_id'] = self.partner_id.country_id.id

        return invoice


class report_intrastat_code(models.Model):
    _inherit = "report.intrastat.code"

    description = fields.Text('Description', translate=True)


class res_company(models.Model):
    _inherit = "res.company"

    region_id = fields.Many2one('l10n_be_intrastat.region', 'Intrastat region')
    transport_mode_id = fields.Many2one('l10n_be_intrastat.transport_mode',
                                             'Default transport mode')
    incoterm_id = fields.Many2one('stock.incoterms', 'Default incoterm for Intrastat',
                                       help="International Commercial Terms are a series of "
                                            "predefined commercial terms used in international "
                                            "transactions.")


class sale_order(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        """
        copy incoterm from sale order to invoice
        """
        invoice = super(sale_order, self)._prepare_invoice()
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


class stock_warehouse(models.Model):
    _inherit = "stock.warehouse"

    region_id = fields.Many2one('l10n_be_intrastat.region', 'Intrastat region')

    def get_regionid_from_locationid(self, location):
        location_ids = location.search([('parent_left', '<=', location.parent_left), ('parent_right', '>=', location.parent_right)])
        warehouses = self.search([('lot_stock_id', 'in', location_ids.ids), ('region_id', '!=', False)])
        if warehouses and warehouses[0]:
            return warehouses[0].region_id.id
        return None
