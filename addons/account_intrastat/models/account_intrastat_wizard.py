# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

import calendar
import base64
from datetime import datetime


class IntrastatReportWizard(models.TransientModel):
    _name = 'account.intrastat.wizard'
    _description = 'Intrastat Report Wizard'

    def _default_date_from(self):
        return datetime.today().date().replace(day=1).strftime(DEFAULT_SERVER_DATE_FORMAT)

    def _default_date_to(self):
        today = datetime.today().date()
        last_day = calendar.monthrange(today.year, today.month)[1]
        return today.replace(day=last_day).strftime(DEFAULT_SERVER_DATE_FORMAT)

    date_from = fields.Date(required=True, string='Date From', default=_default_date_from)
    date_to = fields.Date(required=True, string='Date To', default=_default_date_to)
    extended = fields.Boolean(string='Extended', default=True)
    include_arrivals = fields.Boolean(string='Arrivals', default=True)
    include_dispatches = fields.Boolean(string='Dispatches', default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    filename = fields.Char(string='Filename', size=256, readonly=True)
    file_save = fields.Binary(string='Intrastat Report File', readonly=True)

    @api.model
    def _prepare_query(self, date_from, date_to, company_ids=None, invoice_types=None):
        query = '''
            SELECT
                row_number() over () AS sequence,
                CASE WHEN inv.type IN ('in_invoice', 'out_refund') THEN 19 ELSE 29 END AS system,
                country.code AS country_code,
                company_country.code AS comp_country_code,
                CASE WHEN inv_line.intrastat_transaction_id IS NULL THEN '1' ELSE transaction.code END AS transaction_code,
                company_region.code AS region_code,
                code.name AS commodity_code,
                inv_line.id AS id,
                prodt.id AS template_id,
                inv.id AS invoice_id,
                inv.number AS invoice_number,
                inv.date_invoice AS invoice_date,
                inv.type AS invoice_type,
                inv_incoterm.code AS invoice_incoterm,
                comp_incoterm.code AS company_incoterm,
                inv_transport.code AS invoice_transport,
                comp_transport.code AS company_transport,
                CASE WHEN inv_line.intrastat_transaction_id IS NULL THEN '1' ELSE transaction.code END AS trans_code,
                CASE WHEN inv.type IN ('in_invoice', 'out_refund') THEN 'Arrival' ELSE 'Dispatch' END AS type,
                prodt.weight * inv_line.quantity * (
                    CASE WHEN inv_line_uom.category_id IS NULL OR inv_line_uom.category_id = prod_uom.category_id
                    THEN 1 ELSE inv_line_uom.factor END
                ) AS weight,
                inv_line.quantity * (
                    CASE WHEN inv_line_uom.category_id IS NULL OR inv_line_uom.category_id = prod_uom.category_id
                    THEN 1 ELSE inv_line_uom.factor END
                ) AS quantity,
                inv_line.price_subtotal AS value
            FROM account_invoice_line inv_line
                LEFT JOIN account_invoice inv ON inv_line.invoice_id = inv.id
                LEFT JOIN account_intrastat_transaction transaction ON inv_line.intrastat_transaction_id = transaction.id
                LEFT JOIN res_company company ON inv.company_id = company.id
                LEFT JOIN account_intrastat_region company_region ON company.region_id = company_region.id
                LEFT JOIN res_partner partner ON inv_line.partner_id = partner.id
                LEFT JOIN res_partner comp_partner ON company.partner_id = comp_partner.id
                LEFT JOIN res_country country ON partner.country_id = country.id
                LEFT JOIN res_country company_country ON comp_partner.country_id = company_country.id
                INNER JOIN product_product prod ON inv_line.product_id = prod.id
                LEFT JOIN product_template prodt ON prod.product_tmpl_id = prodt.id
                LEFT JOIN account_intrastat_code code ON prodt.intrastat_id = code.id
                LEFT JOIN uom_uom inv_line_uom ON inv_line.uom_id = inv_line_uom.id
                LEFT JOIN uom_uom prod_uom ON prodt.uom_id = prod_uom.id
                LEFT JOIN account_incoterms inv_incoterm ON inv.incoterm_id = inv_incoterm.id
                LEFT JOIN account_incoterms comp_incoterm ON company.incoterm_id = comp_incoterm.id
                LEFT JOIN account_intrastat_transport inv_transport ON inv.transport_mode_id = inv_transport.id
                LEFT JOIN account_intrastat_transport comp_transport ON company.transport_mode_id = comp_transport.id
            WHERE inv.state in ('open', 'paid')
                AND country.intrastat = TRUE
                AND inv.date_invoice >= %s
                AND inv.date_invoice <= %s
            ORDER BY inv.date_invoice DESC
        '''
        params = [date_from, date_to]

        if company_ids:
            query = query.replace('WHERE', 'WHERE inv.company_id IN %s AND')
            params = [tuple(company_ids)] + params

        if invoice_types:
            query = query.replace('WHERE', 'WHERE inv.type IN %s AND')
            params = [tuple(invoice_types)] + params

        return query, params

    @api.model
    def _check_missing_values(self, vals, cache):
        ''' Some values are to complex to be retrieved in the SQL query.
        Then, this method is used to compute the missing values fetched from the database.

        :param vals:    A dictionary created by the dictfetchall method.
        :param cache:   A cache dictionary used to avoid performance loss.
        '''
        # Check account.intrastat.code
        # If missing, retrieve the commodity code by looking in the product category recursively.
        if not vals['commodity_code']:
            cache_key = 'commodity_code_%s' % str(vals['template_id'])
            vals['commodity_code'] = cache.get(cache_key)
            if not vals['commodity_code']:
                product = self.env['product.template'].browse(vals['template_id'])
                intrastat_code = product.search_intrastat_code()
                cache[cache_key] = vals['commodity_code'] = intrastat_code.name

    @api.model
    def _create_xml(self, date_from, date_to, company, incl_arrivals=True, incl_dispatches=True, extended=True):
        ''' Create the xml export.

        :param date_from:       Starting date.
        :param date_to:         End date.
        :param company:         The company.
        :param incl_arrivals:   Include arrivals.
        :param incl_dispatches: Include dispatches.
        :param extended:        Flag to include or not the 'EXTPC' and 'EXDELTRM' sections (legal requirement in Belgium).
        :return:                The xml export file content.
        '''
        cache = {}

        # create in_vals corresponding to invoices with cash-in
        in_vals = []
        if incl_arrivals:
            query, params = self._prepare_query(date_from, date_to,
                                                company_ids=[company.id], invoice_types=('in_invoice', 'out_refund'))
            self._cr.execute(query, params)
            in_vals = self._cr.dictfetchall()
            [self._check_missing_values(v, cache) for v in in_vals]

        # create out_vals corresponding to invoices with cash-out
        out_vals = []
        if incl_dispatches:
            query, params = self._prepare_query(date_from, date_to,
                                                company_ids=[company.id], invoice_types=('out_invoice', 'in_refund'))
            self._cr.execute(query, params)
            out_vals = self._cr.dictfetchall()
            [self._check_missing_values(v, cache) for v in out_vals]

        return self.env.ref('account_intrastat.intrastat_report_export_xml').render({
            'company': company,
            'in_vals': in_vals,
            'out_vals': out_vals,
            'extended': extended,
        })

    @api.multi
    def get_xml(self):
        self.ensure_one()

        if not self.company_id.country_id:
            raise ValidationError(_('The country of your company is not set, please make sure to configure it first.'))
        if not self.company_id.company_registry:
            raise ValidationError(_('The registry number of your company is not set, please make sure to configure it first.'))

        content = self._create_xml(
            self.date_from, self.date_to, self.company_id, self.include_arrivals, self.include_dispatches, self.extended
        )

        self.write({
            'filename': 'intrastat.xml',
            'file_save': base64.encodestring(content),
        })

        url = 'web/content/?model=account.intrastat.wizard&id=%s&filename_field=filename&field=file_save&download=true&filename=%s'
        return {
            'name': 'XML Declaration',
            'type': 'ir.actions.act_url',
            'url': url % (str(self.id), self.filename),
            'target': 'self',
        }
