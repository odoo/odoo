import io
import xlsxwriter

from odoo import models, _, api
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import get_quarter_number, format_date
from collections import defaultdict

INCOME_FIELDS = (
    'year', 'period', 'activity_code', 'activity_type', 'activity_group', 'invoice_type', 'income_concept',
    'income_computable', 'date_expedition', 'date_transaction', 'invoice_series', 'invoice_number',
    'invoice_final_number', 'partner_nif_type', 'partner_nif_code', 'partner_nif_id',
    'partner_name', 'operation_code', 'operation_qualification', 'operation_exempt', 'total_amount',
    'base_amount', 'tax_rate', 'taxed_amount', 'surcharge_type', 'surcharge_fee', 'payment_date',
    'payment_amount', 'payment_medium', 'payment_medium_id', 'withholding_type', 'withholding_amount',
    'billing_agreement', 'property_situation', 'property_reference', 'external_reference'
)

EXPENSE_FIELDS = (
    'year', 'period', 'activity_code', 'activity_type', 'activity_group', 'invoice_type', 'expense_concept',
    'expense_deductible', 'date_expedition', 'date_transaction', 'expense_series_number', 'expense_final_number',
    'date_reception', 'reception_number', 'reception_number_final', 'partner_nif_type', 'partner_nif_code',
    'partner_nif_id', 'partner_name', 'operation_code', 'investment_good', 'isp_taxable', 'deductible_later',
    'deduction_year', 'deduction_period', 'total_amount', 'base_amount', 'tax_rate', 'taxed_amount', 'tax_deductible',
    'surcharge_type', 'surcharge_fee', 'payment_date', 'payment_amount', 'payment_medium', 'payment_medium_id',
    'withholding_type', 'withholding_amount', 'billing_agreement', 'property_situation', 'property_reference',
    'external_reference'
)

FORMAT_NEEDED_FIELDS = (
    'total_amount', 'base_amount', 'tax_rate', 'taxed_amount', 'surcharge_type', 'surcharge_fee',
    'income_computable', 'expense_deductible', 'tax_deductible', 'withholding_type', 'withholding_amount'
)

SURCHARGE_TAX_EQUIVALENT = {
    5.2: (21,),
    1.75: (21,),
    1.4: (10,),
    0.62: (5,),
    0.5: (5, 4),
    0: (0,),
    0.26: (2,),
    1: (7.5,),
}


class GenericTaxReportCustomHandler(models.AbstractModel):
    _inherit = 'account.generic.tax.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if self.env.company.account_fiscal_country_id.code == 'ES':
            options['buttons'].append({
                'name': _('VAT Record Books (XLSX)'),
                'sequence': 0,
                'action': 'export_file',
                'action_param': 'export_libros_de_iva',
                'file_export_type': _('XLSX'),
            })

    def _l10n_es_libros_fill_header(self, sheet_income, sheet_expense):
        def fill_header(sheet_val, header_title, subheaders=None):
            if not subheaders:
                sheet_val['sheet'].merge_range(0, sheet_val['index'], 1, sheet_val['index'], header_title)
                sheet_val['index'] += 1
            else:
                sheet_val['sheet'].merge_range(0, sheet_val['index'], 0, sheet_val['index'] + len(subheaders) - 1, header_title)
                for sub_idx, subheader in enumerate(subheaders):
                    sheet_val['sheet'].write(1, sheet_val['index'] + sub_idx, subheader)
                sheet_val['index'] += len(subheaders)

        sheet_inc_val = {'sheet': sheet_income, 'index': 0}
        sheet_exp_val = {'sheet': sheet_expense, 'index': 0}

        for sheet_val in (sheet_inc_val, sheet_exp_val):
            fill_header(sheet_val, 'Autoliquidación', ('Ejercicio', 'Periodo'))
            fill_header(sheet_val, 'Actividad', ('Código', 'Tipo', 'Grupo o Epígrafe del IAE'))
            fill_header(sheet_val, 'Tipo de Factura')
            fill_header(sheet_val, 'Concepto de Ingreso' if sheet_val == sheet_inc_val else 'Concepto de Gasto')
            fill_header(sheet_val, 'Ingreso Computable' if sheet_val == sheet_inc_val else 'Gasto Deducible')
            fill_header(sheet_val, 'Fecha Expedición')
            fill_header(sheet_val, 'Fecha Operación')

            if sheet_val == sheet_inc_val:
                fill_header(sheet_val, 'Identificación de la Factura', ('Serie', 'Número', 'Número-Final'))
                fill_header(sheet_val, 'NIF Destinario', ('Tipo', 'Código País', 'Identificación'))
                fill_header(sheet_val, 'Nombre Destinario')
            else:
                fill_header(sheet_val, 'Identificación Factura del Expedidor', ('(Serie-Número)', 'Número-Final'))
                fill_header(sheet_val, 'Fecha Recepción')
                fill_header(sheet_val, 'Número Recepción')
                fill_header(sheet_val, 'Número Recepción Final')
                fill_header(sheet_val, 'NIF Expedidor', ('Tipo', 'Código País', 'Identificación'))
                fill_header(sheet_val, 'Nombre Expedidor')

            fill_header(sheet_val, 'Clave de Operación')
            if sheet_val == sheet_inc_val:
                fill_header(sheet_val, 'Calificación de la Operación')
                fill_header(sheet_val, 'Operación Exenta')
            else:
                fill_header(sheet_val, 'Bien de Inversión')
                fill_header(sheet_val, 'Inversión del Sujeto Pasivo')
                fill_header(sheet_val, 'Deducible en Periodo Posterior')
                fill_header(sheet_val, 'Periodo Deducción', ('Ejercicio', 'Periodo'))
            fill_header(sheet_val, 'Total Factura')
            fill_header(sheet_val, 'Base Imponible')
            fill_header(sheet_val, 'Tipo de IVA')
            if sheet_val == sheet_inc_val:
                fill_header(sheet_val, 'Cuota IVA Repercutida')
            else:
                fill_header(sheet_val, 'Cuota IVA Soportado')
                fill_header(sheet_val, 'Cuota Deducible')
            fill_header(sheet_val, 'Tipo de Recargo eq.')
            fill_header(sheet_val, 'Cuota Recargo eq.')

            if sheet_val == sheet_inc_val:
                head = 'Cobro (Operación Criterio de Caja de IVA y/o artículo 7.2.1º de Reglamento del IRPF)'
            else:
                head = 'Pago (Operación Criterio de Caja de IVA y/o artículo 7.2.1º de Reglamento del IRPF)'
            fill_header(sheet_val, head, ('Fecha', 'Importe', 'Medio Utilizado', 'Identificación Medio Utilizado'))
            fill_header(sheet_val, 'Tipo Retención del IRPF')
            fill_header(sheet_val, 'Importe Retenido del IRPF')
            fill_header(sheet_val, 'Registro Acuerdo Facturación')
            fill_header(sheet_val, 'Inmueble', ('Situación', 'Referencia Catastral'))
            fill_header(sheet_val, 'Referencia Externa')

    def _l10n_es_libros_get_common_line_vals(self, line, tax):
        iae_group = self.env.company.l10n_es_reports_iae_group
        partner = line.partner_id
        exempt_reason = line.move_id.invoice_line_ids.tax_ids.filtered(lambda t: t.l10n_es_exempt_reason == 'E2')
        sign = -1 if line.move_id.is_sale_document(include_receipts=True) else 1

        delivery_date = line.move_id.delivery_date

        common_line_vals = {
            'year': line.date.year,
            'period': str(get_quarter_number(line.date)) + 'T',
            'activity_code': iae_group[0],
            'activity_type': iae_group[1:3],
            'activity_group': iae_group[3:],
            'invoice_type': {
                'out_invoice': 'F2' if line.move_id.l10n_es_is_simplified else 'F1',
                'out_receipt': 'F2' if line.move_id.l10n_es_is_simplified else 'F1',
                'out_refund': 'R5' if line.move_id.l10n_es_is_simplified else 'R1',
                'in_invoice': 'F5' if tax.l10n_es_type == 'dua' else 'F1',
                'in_receipt': 'F5' if tax.l10n_es_type == 'dua' else 'F1',
                'in_refund': 'R4',
            }[line.move_type],
            'date_expedition': format_date(self.env, line.invoice_date, date_format='dd/MM/yyyy'),
            'date_transaction': format_date(self.env, delivery_date,
                                            date_format='dd/MM/yyyy') if delivery_date and delivery_date != line.invoice_date else '',
            'partner_name': partner.name,
            'operation_code': '02' if exempt_reason else '01',
            'total_amount': line.balance * sign,
            'base_amount': line.balance * sign,
            'tax_rate': 0,
            'taxed_amount': 0,
            'surcharge_type': 0,
            'surcharge_fee': 0,
            'withholding_type': 0,
            'withholding_amount': 0,
        }
        if (not partner.country_id or partner.country_id.code == 'ES') and partner.vat:
            common_line_vals['partner_nif_id'] = partner.vat[2:] if partner.vat.startswith('ES') else partner.vat
        elif partner.vat and partner.country_id in self.env.ref('base.europe').country_ids:
            common_line_vals['partner_nif_id'] = partner.vat
            common_line_vals['partner_nif_type'] = "02"
        elif partner.vat:
            common_line_vals['partner_nif_id'] = partner.vat
            common_line_vals['partner_nif_type'] = "06"
            common_line_vals['partner_nif_code'] = partner.country_id.code

        return common_line_vals

    def _l10n_es_libros_create_income_line_vals(self, line, tax):
        line_vals = {field: '' for field in INCOME_FIELDS}
        line_vals.update(self._l10n_es_libros_get_common_line_vals(line, tax))
        line_vals.update({
            'income_concept': 'I01',
            'income_computable': -line.balance,
            'invoice_number': line.move_id.name,
            'operation_qualification': {
                'sujeto': 'S1',
                'sujeto_isp': 'S2',
                'no_sujeto': 'N1',
                'no_sujeto_loc': 'N2',
            }.get(tax.l10n_es_type, ''),
            'operation_exempt': tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else '',
        })
        if line_vals['operation_qualification'] == 'S2':
            line_vals['tax_rate'] = 0

        return line_vals

    def _l10n_es_libros_create_expense_line_vals(self, line, tax):
        expense_concept = 'G01'
        line_vals = {field: '' for field in EXPENSE_FIELDS}
        line_vals.update(self._l10n_es_libros_get_common_line_vals(line, tax))
        line_vals.update({
            'expense_concept': expense_concept,
            'expense_deductible': line.balance,
            'expense_series_number': line.move_id.ref or '',
            'reception_number': line.move_id.name,
            'date_reception': format_date(self.env, line.date.isoformat(), date_format='dd/MM/yyyy'),
            'investment_good': 'S' if (tax.l10n_es_bien_inversion and
                                       line_vals['operation_code'] != '02') else 'N',
            'isp_taxable': 'S' if tax.l10n_es_type == 'sujeto_isp' else 'N',
            'tax_deductible': 0,
        })
        return line_vals

    @api.model
    def _l10n_es_libros_merge_base_line(self, line_vals, base_line):
        is_income = base_line.move_id.is_sale_document(include_receipts=True)
        sign = -1 if is_income else 1
        new_balance = line_vals['base_amount'] + base_line.balance * sign
        line_vals.update({
            'total_amount': new_balance,
            'base_amount': new_balance,
        })
        if is_income:
            line_vals['income_computable'] = new_balance
        else:
            line_vals['expense_deductible'] = new_balance

    @api.model
    def _l10n_es_libros_merge_line_tax(self, line_vals, line, tax, tax_amount):
        if tax.l10n_es_type == 'recargo':
            line_vals.update({
                'total_amount': line_vals['total_amount'] + tax_amount,
                'surcharge_type': abs(tax.amount),
                'surcharge_fee': line_vals['surcharge_fee'] + tax_amount,
            })
        elif tax.l10n_es_type == 'retencion':
            line_vals.update({
                'total_amount': line_vals['total_amount'] + tax_amount,
                'withholding_type': abs(tax.amount),
                'withholding_amount': line_vals['withholding_amount'] - tax_amount,
            })
        elif tax.l10n_es_type == 'ignore':
            return
        else:
            if line_vals.get('operation_qualification') == 'S2':
                return
            line_vals.update({
                'total_amount': line_vals['total_amount'] + tax_amount,
                'tax_rate': tax.amount,
                'taxed_amount': line_vals['taxed_amount'] + tax_amount,
            })
            # add amount to tax_deductible only if the line have mod303 in the tax grid (supports pro rata tax type)
            if not line.move_id.is_sale_document(include_receipts=True) and any('mod303' in tag for tag in line.tax_tag_ids.mapped('name')):
                line_vals['tax_deductible'] += tax_amount

    def _l10n_es_libros_format_sheet_line_vals(self, sheet_line_vals):
        for move_idx in sheet_line_vals:
            for line_vals in sheet_line_vals[move_idx].values():
                for field, value in line_vals.items():
                    if field in FORMAT_NEEDED_FIELDS and value != '':
                        line_vals[field] = round(value, 2)

    def _l10n_es_libros_get_sheet_line_vals(self, lines):
        """ Parse the invoice lines to generate each report lines based on the combination
        of taxes used on each line.
        Then parse the tax lines to populate the fields related to tax amounts of the report lines.
        """
        inc_line_vals, exp_line_vals = {}, {}
        # The keys of the first dict are account moves (account.move record).
        # The keys of the second dict are a tuple of the taxes used on each invoice line: (tax_a, tax_b).
        # The keys of the third dict are taxes (account.tax record).
        # One entry of the third dict is an accumulated amount of base amounts for a tax, which is used
        # to compute the ratio with the base amount of a tax line.
        base_amount_by_tax = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        # generate the report lines from the invoice lines
        for line in lines.filtered(lambda l: l.tax_ids):
            is_income = line.move_id.is_sale_document(include_receipts=True)
            sheet_line_vals = inc_line_vals if is_income else exp_line_vals
            create_line_vals = self._l10n_es_libros_create_income_line_vals if is_income else self._l10n_es_libros_create_expense_line_vals
            move = line.move_id
            sheet_line_vals.setdefault(move.id, {})
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            tax_key = tuple(taxes)
            ignore_line = True
            regular_tax = False
            for tax in taxes:
                # a tax of type "recargo" should be associated to a tax having a specific amount
                if tax.l10n_es_type == 'recargo':
                    linked_tax = taxes.filtered(
                        lambda t: t.l10n_es_type not in ('recargo', 'retencion', 'ignore')
                            and t.amount in SURCHARGE_TAX_EQUIVALENT[tax.amount]
                    )
                    if not linked_tax:
                        raise UserError(_('Unable to find matching surcharge tax in %s', move.name))
                # invoice lines with only taxes of type "ignore" and/or "retencion" should be ignored
                elif tax.l10n_es_type not in ('ignore', 'retencion'):
                    ignore_line = False
                    if not regular_tax:
                        regular_tax = tax
                # compute the new accumulated base amount for this tax
                base_amount_by_tax[move][tax_key][tax] += abs(line.balance)
            # if ignore_line is True, then all the taxes are "ignore" and/or "retencion" ones
            if ignore_line:
                del base_amount_by_tax[move][tax_key]
                continue    # no report line should be created for such line
            # initialize [inc/exp]_line_vals with base balance and first regular tax of invoice lines
            if tax_key in sheet_line_vals[move.id]:
                self._l10n_es_libros_merge_base_line(sheet_line_vals[move.id][tax_key], line)
            else:
                sheet_line_vals[move.id][tax_key] = create_line_vals(line, regular_tax)

        # loop on each tax line and compute the tax amount for each line based on the ratio
        # of the base amount
        tax_lines = (line for line in lines if line.tax_line_id)
        for line in tax_lines:
            is_income = line.move_id.is_sale_document(include_receipts=True)
            sheet_line_vals = inc_line_vals if is_income else exp_line_vals
            move, tax = line.move_id, line.tax_line_id
            sign = -1 if is_income else 1
            remaining_tax_base_amount = line.tax_base_amount
            remaining_tax_balance = line.balance
            for tax_key, data in base_amount_by_tax[move].items():
                if tax not in tax_key:
                    continue
                remaining_tax_base_amount -= data[tax]
                if remaining_tax_base_amount <= 0:
                    tax_amount = remaining_tax_balance
                    remaining_tax_balance = 0
                else:
                    ratio = data[tax] / line.tax_base_amount if line.tax_base_amount else 0
                    tax_amount = move.company_id.currency_id.round(line.balance * ratio)
                    remaining_tax_balance -= tax_amount
                # update the report line with the tax amount
                self._l10n_es_libros_merge_line_tax(sheet_line_vals[move.id][tax_key], line, tax, tax_amount * sign)

        self._l10n_es_libros_format_sheet_line_vals(inc_line_vals)
        self._l10n_es_libros_format_sheet_line_vals(exp_line_vals)
        return inc_line_vals, exp_line_vals

    def _l10n_es_libros_fill_content(self, sheet_income, sheet_expense, report, options):
        domain = report._get_options_domain(options, 'strict_range') + [('move_type', '!=', 'entry')]
        lines = self.env['account.move.line'].search(domain)

        inc_line_vals, exp_line_vals = self._l10n_es_libros_get_sheet_line_vals(lines)
        sheet_inc_vals = {'sheet': sheet_income, 'line_vals': inc_line_vals, 'row_idx': 2, 'fields': INCOME_FIELDS}
        sheet_exp_vals = {'sheet': sheet_expense, 'line_vals': exp_line_vals, 'row_idx': 2, 'fields': EXPENSE_FIELDS}

        for sheet_vals in (sheet_inc_vals, sheet_exp_vals):
            for move_idx in sheet_vals['line_vals']:
                for line_vals in sheet_vals['line_vals'][move_idx].values():
                    for col_idx, field in enumerate(sheet_vals['fields']):
                        if field in FORMAT_NEEDED_FIELDS and line_vals[field] and options.get('number_format'):
                            sheet_vals['sheet'].write(sheet_vals['row_idx'], col_idx, line_vals[field], options.get('number_format'))
                        else:
                            sheet_vals['sheet'].write(sheet_vals['row_idx'], col_idx, line_vals[field])
                    sheet_vals['row_idx'] += 1

    def export_libros_de_iva(self, options):
        if not self.env.company.l10n_es_reports_iae_group:
            raise RedirectWarning(
                _("Please configure the \"IAE Group or Heading\" of your company."),
                self.env.ref('base.action_res_company_form').id,
                _("Go to Company"),
            )
        report = self.env['account.report'].browse(options['report_id'])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_formulas': False})

        number_format = workbook.add_format({'num_format': '0.00'})
        sheet_income = workbook.add_worksheet('EXPEDIDAS_INGRESOS')
        sheet_expense = workbook.add_worksheet('RECIBIDAS_GASTOS')

        options['number_format'] = number_format
        self._l10n_es_libros_fill_header(sheet_income, sheet_expense)
        self._l10n_es_libros_fill_content(sheet_income, sheet_expense, report, options)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': 'libros_registro_de_iva.xlsx',
            'file_content': generated_file,
            'file_type': 'xlsx',
        }


class SpanishLibrosRegistroExportHandler(models.AbstractModel):  # TODO: Remove in master
    _name = 'l10n_es.libros.registro.export.handler'
    _inherit = 'account.generic.tax.report.handler'
    _description = 'Spanish Libros Registro de IVA'
