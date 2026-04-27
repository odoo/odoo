import base64
import csv
import pytz
import re

from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from io import StringIO
from werkzeug.urls import url_encode

from odoo import api, fields, models
from odoo.tools import groupby, SQL
from odoo.exceptions import UserError
from odoo.tools import float_repr


class StockMovePleReport(models.TransientModel):
    _name = 'l10n_pe.stock.ple.wizard'
    _description = 'Wizard to generate Stock Move PLE reports for PE'

    @api.model
    def default_get(self, fields_list):
        results = super().default_get(fields_list)
        if self.env.company.country_code != 'PE':
            raise UserError('This option is only available for Peruvian companies.')
        date_from = fields.Date.today().replace(day=1)
        results['date_from'] = date_from
        results['date_to'] = date_from + relativedelta(months=1, days=-1)
        return results

    date_from = fields.Date(
        required=True,
        help="Choose a date from to get the PLE reports at that date",
    )
    date_to = fields.Date(
        required=True,
        help="Choose a date to get the PLE reports at that date",
    )
    report_data = fields.Binary('Report file', readonly=True, attachment=False)
    report_filename = fields.Char(string='Filename', readonly=True)
    mimetype = fields.Char(string='Mimetype', readonly=True)

    def get_ple_report_12_1(self):
        return self.get_ple_report('1201')

    def get_ple_report_13_1(self):
        return self.get_ple_report('1301')

    def get_ple_report(self, report_number):
        data = self._get_ple_report_content(report_number)
        has_data = "1" if data else "0"
        filename = "LE%s%s%02d00%s00001%s11.txt" % (
            self.env.company.vat, self.date_from.year, self.date_from.month, report_number, has_data)
        self.write({
            'report_data': base64.b64encode(data.encode()),
            'report_filename': filename,
            'mimetype': 'application/txt',
        })
        return {
            'type': 'ir.actions.act_url',
            'url':  '/web/content/?' + url_encode({
                'model': self._name,
                'id': self.id,
                'filename_field': 'report_filename',
                'field': 'report_data',
                'download': 'true'
            }),
            'target': 'new'
        }

    @api.model
    def _get_serie_folio(self, number):
        values = {"serie": "", "folio": ""}
        number_matchs = list(re.finditer("\\d+", number or ""))
        if number_matchs:
            last_number_match = number_matchs[-1]
            values["serie"] = number[: last_number_match.start()].replace("-", "") or ""
            values["folio"] = last_number_match.group() or ""
        return values

    def _get_ple_report_content(self, report):
        def _get_stock_valuation(category):
            cost_method = self.env['product.category'].browse(category).property_cost_method
            return {'average': '1', 'fifo': '2', 'standard': '3'}.get(cost_method, '')

        data = []
        period = '%s%s00' % (self.date_from.year, str(self.date_from.month).zfill(2))
        count = 0
        data_per_products = {}
        for line in self._get_ple_reports_data():
            serie_folio = self._get_serie_folio(line['delivery_number'] or line['move_name'] or line['move_name_p'] or line['picking_name'] or '')
            if date_str := line['invoice_date'] or line['invoice_date_p'] or line['date'] or line['svl_date']:
                date = date_str.strftime('%d/%m/%Y')
            else:
                date = ''
            if line['product_id'] not in data_per_products:
                valuation_data = self._append_valuation_line(line, period, False, report)
                data_per_products[line['product_id']] = [valuation_data.get("qty_in", 0), valuation_data.get("value_in", 0)]
                if valuation_data:
                    data.append(valuation_data)
                    count += 1
            operation_type = (line['l10n_pe_operation_type'] or '99').zfill(2)
            if not operation_type and line['operation_type'] == 'mrp_operation':
                operation_type = '19' if line['quantity'] > 0 else '27'
            document_type = line['document_type'] or line['document_type_p'] or '00'
            if line['delivery_number'] or (operation_type in ['01', '02', '03', '04', '05', '06'] and document_type == '00'):
                document_type = '09'
            quantity = line['quantity']
            if report == '1201' and not quantity:
                continue
            if not quantity:
                operation_type = '99'
            values = {
                'period': period,
                'cuo': str(line['svl_id'] or count).replace('/', '').zfill(6),
                'number': 'M1',  # The first digit should be 'M' to denote entries for movements or adjustments within the month. Therefore, 'M1' indicates this is the first such entry.
                'establishment': line['l10n_pe_anexo_establishment_code'] or '0000',
                'catalogue': '1',  # Only supported 1 because We use Unspsc
                'type_of_existence': (line['l10n_pe_type_of_existence'] or '99').zfill(2),
                'default_code': re.sub(r"[_\-/'']", '', line.get('default_code', '') or '')[:24],
                'catalogue_used': '1',  # Only supported 1 because We use Unspsc
                'unspsc': line['unspsc_code'],
                'date': date,
                'document_type': document_type,
                'serie': serie_folio['serie'].replace(' ', '').replace('/', '') or '0',
                'folio': serie_folio['folio'].replace(' ', '') or '0',
                'operation_type': operation_type,
                'product': (line['product_name']['en_US'] or '').replace('"', "'")[:80],
                'uom': line['l10n_pe_edi_measure_unit_code'],
            }
            count += 1
            if report == '1201':
                values.update({
                    'qty_in': quantity if quantity > 0 else 0,
                    'qty_out': quantity if quantity <= 0 else 0,
                    'state': '1',
                })
                data.append(values)
                continue
            unit_cost = line['unit_cost'] or 0
            total_cost = line['value']
            data_per_products[line['product_id']][0] += quantity
            data_per_products[line['product_id']][1] += total_cost
            values.update({
                'valuation': _get_stock_valuation(line['category']),
                'qty_in': quantity if quantity > 0 else 0,
                'cost_in': round(unit_cost, 2) if quantity > 0 else 0,
                'value_in': round(total_cost, 2) if total_cost > 0 else 0,
                'qty_out': quantity if quantity <= 0 else 0,
                'cost_out': (round(unit_cost, 2)) if quantity <= 0 else 0,
                'value_out': round(total_cost, 2) if total_cost <= 0 else 0,
                'remaining': data_per_products[line['product_id']][0] or 0,
                'unit_cost_final': abs(round((data_per_products[line['product_id']][1] or 0) / (data_per_products[line['product_id']][0] or 1), 2)) or 0,
                'value': round(data_per_products[line['product_id']][1], 2) or 0,
                'state': '1',
            })
            data.append(values)
        data.extend(self._append_historic_valuation_lines(list(data_per_products), period, count, report))
        if not data:
            return ''
        float_fields = (
            "qty_in", "cost_in", "value_in",
            "qty_out", "cost_out", "value_out",
            "remaining", "unit_cost_final", "value",
        )

        for element in data:
            for field in float_fields:
                if field in element:
                    element[field] = float_repr(round(float(element[field] or 0.0), 2), precision_digits=2)
        output = StringIO()
        writer = csv.DictWriter(output, delimiter="|", skipinitialspace=True, lineterminator='\n', fieldnames=[*data[0], object()])
        writer.writerows(data)
        txt_result = output.getvalue()
        return txt_result

    def _append_valuation_line(self, line, period, count, report):
        def _get_stock_valuation(category):
            cost_method = self.env['product.category'].browse(category).property_cost_method
            return {'average': '1', 'fifo': '2', 'standard': '3'}.get(cost_method, '')
        date_from = datetime.combine(self.date_from, time.min)
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        date_from = tz.localize(date_from).astimezone(pytz.UTC)
        domain = [
            ('company_id', '=', self.env.company.id),
            ('product_id', '=', line['product_id']),
            ('create_date', '<', date_from),
        ]
        where_query = self.env['stock.valuation.layer']._where_calc(domain)
        self._cr.execute(SQL(
            """
                SELECT SUM(quantity) AS quantity, SUM(value) AS value
                FROM %(from_clause)s
                WHERE %(where_clause)s
            """,
            from_clause=where_query.from_clause,
            where_clause=where_query.where_clause,
        ))

        valuation_data = self._cr.dictfetchall()
        quantity = valuation_data[0]['quantity']
        if not quantity:
            return {}
        values = {
            'period': period,
            'cuo': f'{line["svl_id"]}A1'.zfill(6),
            'number': 'A1',
            'establishment': line['l10n_pe_anexo_establishment_code'] or '0000',
            'catalogue': '1',  # Only supported 1 because We use Unspsc
            'type_of_existence': '99',
            'default_code': (line['default_code'] or '').replace('_', '').replace('-', '').replace('/', '').replace("'", '')[:24],
            'catalogue_used': '1',  # Only supported 1 because We use Unspsc
            'unspsc': line['unspsc_code'],
            'date': self.date_from.strftime('%d/%m/%Y'),
            'document_type': '00',
            'serie': '0',
            'folio': '0',
            'operation_type': '16',
            'product': (line['product_name']['en_US'] or '').replace('"', "'")[:80],
            'uom': line['l10n_pe_edi_measure_unit_code'],
        }
        if report == '1201':
            values.update({
                'qty_in': quantity if quantity > 0 else 0,
                'qty_out': 0,
                'state': '1',
            })
            return values
        value = valuation_data[0]['value']
        values.update({
            'valuation': _get_stock_valuation(line['category']),
            'qty_in': quantity if quantity > 0 else 0,
            'cost_in': round(value / quantity, 2),
            'value_in': round(value, 2),
            'qty_out': 0,
            'cost_out': 0,
            'value_out': 0,
            'remaining': quantity if quantity > 0 else 0,
            'unit_cost_final': round(value / quantity, 2),
            'value': round(value, 2),
            'state': '1',
        })
        return values

    def _append_historic_valuation_lines(self, products, period, count, report):
        def _get_stock_valuation(category_id):
            cost_method = self.env['product.category'].browse(category_id).property_cost_method
            return {'average': '1', 'fifo': '2', 'standard': '3'}.get(cost_method, '')

        tz = pytz.timezone(self.env.user.tz or 'UTC')
        date_from = datetime.combine(self.date_from, time.min)
        date_from = tz.localize(date_from).astimezone(pytz.UTC)
        self.env.cr.execute(SQL(
            """
                SELECT
                    svl.product_id,
                    SUM(svl.quantity) AS quantity,
                    SUM(svl.value) AS value,
                    SUM(svl.value) / NULLIF(SUM(svl.quantity), 0) AS unit_cost,
                    product_unspsc_code.code AS unspsc_code,
                    product_product.default_code,
                    product_template.name AS product_name,
                    product_template.l10n_pe_type_of_existence,
                    product_template.categ_id AS category,
                    uom_uom.l10n_pe_edi_measure_unit_code
                FROM stock_valuation_layer svl
                JOIN product_product ON product_product.id = svl.product_id
                JOIN product_template ON product_template.id = product_product.product_tmpl_id
                LEFT JOIN product_unspsc_code ON product_unspsc_code.id = product_template.unspsc_code_id
                LEFT JOIN uom_uom ON uom_uom.id = product_template.uom_id
                WHERE svl.company_id = %(company_id)s
                AND svl.create_date < %(date_from)s
                AND svl.product_id NOT IN %(excluded_products)s
                AND product_template.type = 'product'
                GROUP BY
                    svl.product_id,
                    product_unspsc_code.code,
                    product_product.default_code,
                    product_template.name,
                    product_template.l10n_pe_type_of_existence,
                    product_template.categ_id,
                    uom_uom.l10n_pe_edi_measure_unit_code
                HAVING SUM(svl.quantity) != 0
            """,
            company_id=self.env.company.id,
            date_from=date_from,
            excluded_products=tuple(products or [0]),
        ))

        data = []
        for line in self._cr.dictfetchall():
            quantity = line['quantity']
            unit_cost = round(line['unit_cost'], 2) if line['unit_cost'] else 0.0
            value = round(line['value'], 2)

            values = {
                'period': period,
                'cuo': str(count).zfill(6),
                'number': 'A1',
                'establishment': '0000',
                'catalogue': '1',
                'type_of_existence': '99',
                'default_code': (line['default_code'] or '').replace('_', '').replace('-', '').replace('/', '').replace("'", '')[:24],
                'catalogue_used': '1',
                'unspsc': line['unspsc_code'],
                'date': self.date_from.strftime('%d/%m/%Y'),
                'document_type': '00',
                'serie': '0',
                'folio': '0',
                'operation_type': '16',
                'product': (line['product_name']['en_US'] or '').replace('"', "'")[:80],
                'uom': line['l10n_pe_edi_measure_unit_code'],
            }
            count += 1

            if report == '1201':
                values.update({
                    'qty_in': quantity,
                    'qty_out': 0,
                    'state': '1',
                })
                data.append(values)
                continue

            values.update({
                'valuation': _get_stock_valuation(line['category']),
                'qty_in': quantity,
                'cost_in': unit_cost,
                'value_in': value,
                'qty_out': 0,
                'cost_out': 0,
                'value_out': 0,
                'remaining': quantity,
                'unit_cost_final': unit_cost,
                'value': value,
                'state': '1',
            })
            data.append(values)
        return data

    def _get_ple_reports_data(self):
        # Convert dates to UTC using the user's timezone to match Odoo's layer
        # date handling. This avoids discrepancies between report results and
        # the layer view caused by timezone offsets.
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        date_from = datetime.combine(self.date_from, time.min)
        date_to = datetime.combine(self.date_to, time.max)
        date_from = tz.localize(date_from).astimezone(pytz.UTC)
        date_to = tz.localize(date_to).astimezone(pytz.UTC)
        domain = [
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to),
            ('company_id', '=', self.env.company.id),
        ]
        is_latam_doc_number_module_installed = 'l10n_latam_document_number' in self.env['stock.picking']._fields

        query = self.env['stock.valuation.layer']._where_calc(domain)
        query.left_join('stock_valuation_layer', 'stock_move_id', 'stock_move', 'id', 'move')
        query.left_join('stock_valuation_layer', 'product_id', 'product_product', 'id', 'product')
        query.left_join('stock_valuation_layer__product', 'product_tmpl_id', 'product_template', 'id', 'template')
        query.left_join('stock_valuation_layer__product__template', 'categ_id', 'product_category', 'id', 'category')
        query.left_join('stock_valuation_layer__product__template', 'unspsc_code_id', 'product_unspsc_code', 'id', 'unspsc')
        query.left_join('stock_valuation_layer__product__template', 'uom_id', 'uom_uom', 'id', 'uom')
        query.left_join('stock_valuation_layer__move', 'picking_id', 'stock_picking', 'id', 'picking')
        query.left_join('stock_valuation_layer__move', 'location_id', 'stock_location', 'id', 'location')
        query.left_join('stock_valuation_layer__move__location', 'warehouse_id', 'stock_warehouse', 'id', 'warehouse')
        query.left_join('stock_valuation_layer__move', 'picking_type_id', 'stock_picking_type', 'id', 'picking_type')
        query.left_join('stock_valuation_layer', 'account_move_id', 'account_move', 'id', 'account_move')

        # # Section to get the invoice related for SO
        query.left_join('stock_valuation_layer__move', 'sale_line_id', 'sale_order_line', 'id', 'sol')
        query.left_join('stock_valuation_layer__move__sol', 'id', 'sale_order_line_invoice_rel', 'order_line_id', 'solr')
        query.left_join('stock_valuation_layer__move__sol__solr', 'invoice_line_id', 'account_move_line', 'id', 'aml')
        query.left_join('stock_valuation_layer__move__sol__solr__aml', 'move_id', 'account_move', 'id', 'am')

        # # Section to get the invoice related for PO
        query.left_join('stock_valuation_layer__move', 'purchase_line_id', 'purchase_order_line', 'id', 'pol')
        query.left_join('stock_valuation_layer__move__pol', 'id', 'account_move_line', 'purchase_line_id', 'aml_p')
        query.left_join('stock_valuation_layer__move__pol__aml_p', 'move_id', 'account_move', 'id', 'am_p')

        query.left_join('stock_valuation_layer__move__sol__solr__aml__am', 'l10n_latam_document_type_id', 'l10n_latam_document_type', 'id', 'doctype')
        query.left_join('stock_valuation_layer__move__pol__aml_p__am_p', 'l10n_latam_document_type_id', 'l10n_latam_document_type', 'id', 'doctype_p')

        query.order = (
            "stock_valuation_layer.id,"
            "stock_valuation_layer.product_id,"
            "stock_valuation_layer.create_date,"
            "stock_valuation_layer__move__pol__aml_p__am_p.id NULLS LAST,"
            "stock_valuation_layer__move__sol__solr__aml__am.id NULLS LAST"
        )

        qu = query.select(
            'DISTINCT ON (stock_valuation_layer.id) stock_valuation_layer.id AS svl_id',
            'stock_valuation_layer.create_date AS svl_date',
            'stock_valuation_layer.quantity',
            'stock_valuation_layer.unit_cost',
            'stock_valuation_layer.value',
            'stock_valuation_layer.remaining_qty',
            'stock_valuation_layer.remaining_value',
            'stock_valuation_layer__move.id AS move_id',
            'stock_valuation_layer__account_move.name AS svl_name',
            'stock_valuation_layer__product.default_code',
            'stock_valuation_layer__product.id AS product_id',
            'stock_valuation_layer__product__template.name AS product_name',
            'stock_valuation_layer__product__template.l10n_pe_type_of_existence',
            'stock_valuation_layer__product__template__category.id AS category',
            'stock_valuation_layer__product__template__unspsc.code AS unspsc_code',
            'stock_valuation_layer__product__template__uom.l10n_pe_edi_measure_unit_code',
            'stock_valuation_layer__move.date',
            'stock_valuation_layer__move__location__warehouse.l10n_pe_anexo_establishment_code',
            'stock_valuation_layer__move__picking_type.code AS operation_type',
            'stock_valuation_layer__move__picking.l10n_pe_operation_type',
            'stock_valuation_layer__move__picking.l10n_latam_document_number AS delivery_number' if is_latam_doc_number_module_installed else 'NULL AS delivery_number',
            'stock_valuation_layer__move__picking.name AS picking_name',
            'stock_valuation_layer__move__sol__solr__aml__am.invoice_date',
            'stock_valuation_layer__move__sol__solr__aml__am__doctype.code AS document_type',
            'stock_valuation_layer__move__sol__solr__aml__am.name AS move_name',
            'stock_valuation_layer__move__pol__aml_p__am_p.invoice_date AS invoice_date_p',
            'stock_valuation_layer__move__pol__aml_p__am_p__doctype_p.code AS document_type_p',
            'stock_valuation_layer__move__pol__aml_p__am_p.name AS move_name_p'
        )

        inner_sql = qu.code.strip().rstrip(";")
        params = qu.params

        outer_sql = f"""
            SELECT *
            FROM (
                {inner_sql}
            ) svl_subquery
            ORDER BY
                svl_subquery.product_id,
                svl_subquery.svl_date NULLS FIRST,
                svl_subquery.svl_id
        """

        self.env.cr.execute(outer_sql, params)
        return self.env.cr.dictfetchall()
