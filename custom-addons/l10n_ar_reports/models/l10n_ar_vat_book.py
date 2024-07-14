# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools.float_utils import float_split_str

from collections import OrderedDict
import re
import zipfile
import io


class ArgentinianReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ar.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Argentinian Report Custom Handler'

    def _get_custom_display_config(self):
        return {
            'templates': {
                'AccountReportFilters': 'l10n_ar_reports.L10nArReportsFiltersCustomizable',
            },
        }

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        # dict of the form {move_id: {column_group_key: {expression_label: value}}}
        move_info_dict = {}

        # dict of the form {column_group_key: total_value}
        total_values_dict = {}

        # Every key/expression_label that is a number (and should be rendered like one)
        number_keys = ['taxed', 'not_taxed', 'vat_25', 'vat_5', 'vat_10', 'vat_21', 'vat_27', 'vat_per', 'perc_iibb', 'perc_earnings', 'city_tax', 'other_taxes', 'total']

        # Build full query
        query_list = []
        full_query_params = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query, params = self._build_query(report, column_group_options, column_group_key)
            query_list.append(f"({query})")
            full_query_params += params

            # Set defaults here since the results of the query for this column_group_key might be empty
            total_values_dict.setdefault(column_group_key, dict.fromkeys(number_keys, 0.0))

        full_query = " UNION ALL ".join(query_list)
        self._cr.execute(full_query, full_query_params)
        results = self._cr.dictfetchall()
        for result in results:
            # Iterate over these results in order to fill the move_info_dict dictionary
            move_id = result['id']
            column_group_key = result['column_group_key']

            # Convert date to string to be displayed in the xlsx report
            result['date'] = result['date'].strftime("%Y-%m-%d")

            # For number rendering, take the opposite for sales taxes
            sign = -1.0 if result['tax_type'] == 'sale' else 1.0

            current_move_info = move_info_dict.setdefault(move_id, {})

            current_move_info['line_name'] = result['move_name']
            current_move_info[column_group_key] = result

            # Apply sign and add values to totals
            totals = total_values_dict[column_group_key]
            for key in number_keys:
                result[key] = sign * result[key]
                totals[key] += result[key]

        lines = []
        for move_id, move_info in move_info_dict.items():
            # 1 line for each move_id
            line = self._create_report_line(report, options, move_info, move_id, number_keys)
            lines.append((0, line))
        # Single total line if only one type of journal is selected
        selected_tax_types = self._vat_book_get_selected_tax_types(options)
        if len(selected_tax_types) < 2:
            total_line = self._create_report_total_line(report, options, total_values_dict)
            lines.append((0, total_line))

        return lines

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if previous_options is None:
            previous_options = {}

        # Add export button
        zip_export_button = {
            'name': _('VAT Book (ZIP)'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'vat_book_export_files_to_zip',
            'file_export_type': _('ZIP'),
        }

        options['buttons'].append(zip_export_button)
        options['ar_vat_book_tax_types_available'] = {
            'sale': _('Sales'),
            'purchase': _('Purchases'),
            'all': _('All'),
        }
        if options.get('_running_export_test'):
            # Exporting the file is not allowed for 'all'. When executing the export tests, we hence always select 'sales', to avoid raising.
            options['ar_vat_book_tax_type_selected'] = 'sale'
        else:
            options['ar_vat_book_tax_type_selected'] = previous_options.get('ar_vat_book_tax_type_selected', 'all')

        options['forced_domain'] = [
             *options.get('forced_domain', []),
             ('journal_id.l10n_latam_use_documents', '!=', False),
         ]

        tax_types = self._vat_book_get_selected_tax_types(options)

        # 2 columns are conditional, depending on some taxes being active or inactive
        columns_to_remove = []
        if not self.env['account.tax'].search([('type_tax_use', 'in', tax_types), ('tax_group_id.l10n_ar_vat_afip_code', '=', '9')]):
            columns_to_remove.append('vat_25')
        if not self.env['account.tax'].search([('type_tax_use', 'in', tax_types), ('tax_group_id.l10n_ar_vat_afip_code', '=', '8')]):
            columns_to_remove.append('vat_5')

        options['columns'] = [col for col in options['columns'] if col['expression_label'] not in columns_to_remove]

    ####################################################
    # REPORT LINES: CORE
    ####################################################

    def _build_query(self, report, options, column_group_key):
        #pylint: disable=sql-injection
        tables, where_clause, where_params = report._query_get(options, 'strict_range')

        where_clause = f"AND {where_clause}"
        tax_types = tuple(self._vat_book_get_selected_tax_types(options))

        return self.env['account.ar.vat.line']._ar_vat_line_build_query(tables, where_clause, where_params, column_group_key, tax_types)

    def _create_report_line(self, report, options, move_vals, move_id, number_values):
        """ Create a standard (non total) line for the report
        :param options: report options
        :param move_vals: values necessary for the line
        :param move_id: id of the account.move (or account.ar.vat.line)
        :param number_values: list of expression_label that require the 'number' class
        """
        columns = []
        for column in options['columns']:
            expression_label = column['expression_label']
            value = move_vals.get(column['column_group_key'], {}).get(expression_label)

            columns.append(report._build_column_dict(value, column, options=options))

        return {
            'id': report._get_generic_line_id('account.move', move_id),
            'caret_options': 'account.move',
            'name': move_vals['line_name'],
            'columns': columns,
            'level': 2,
        }

    def _create_report_total_line(self, report, options, total_vals):
        """ Create a total line for the report
        :param options: report options
        :param total_vals: values necessary for the line
        """
        columns = []
        for column in options['columns']:
            expression_label = column['expression_label']
            value = total_vals.get(column['column_group_key'], {}).get(expression_label)

            columns.append(report._build_column_dict(value, column, options=options))
        return {
            'id': report._get_generic_line_id(None, None, markup='total'),
            'name': _('Total'),
            'class': 'total',
            'level': 1,
            'columns': columns,
        }

    ####################################################
    # EXPORT/PRINT
    ####################################################

    def vat_book_export_files_to_zip(self, options):
        """ Export method that lets us export the VAT book to a zip archive.
        It contains the files that we upload to AFIP for Purchase VAT Book """
        tax_type = self._vat_book_get_selected_tax_types(options)
        if len(tax_type) > 1:
            raise UserError(_("Only one tax type should be selected."))
        tax_type = tax_type[0]

        # Build file name
        export_file_name = {'sale': 'Libro_IVA_Ventas', 'purchase': 'Libro_IVA_Compras'}.get(tax_type, 'Libro_IVA')
        export_file_name = f"{export_file_name}_{options['date']['date_to']}"

        # Build zip content
        txt_types = ['purchases', 'goods_import', 'used_goods'] if tax_type == 'purchase' else ['sale']
        filenames = {
            'purchases': 'Compras',
            'purchases_aliquots': 'IVA_Compras',
            'goods_import': 'Importaciones_de_Bienes',
            'goods_import_aliquots': 'IVA_Importaciones_de_Bienes',
            'used_goods': 'Compras_Bienes_Usados',
            'used_goods_aliquots': 'IVA_Compras_Bienes_Usados',
            'sale': 'Ventas',
            'sale_aliquots': 'IVA_Ventas'
        }
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for txt_type in txt_types:
                options.update({'txt_type': txt_type})
                vouchers_data, aliquots_data = self._vat_book_get_txt_files(options, tax_type)
                if vouchers_data:
                    zf.writestr(filenames.get(txt_type) + '.txt', vouchers_data)
                if aliquots_data:
                    zf.writestr(filenames.get(f'{txt_type}_aliquots') + '.txt', aliquots_data)
        file_content = stream.getvalue()
        return {
            'file_name': export_file_name,
            'file_content': file_content,
            'file_type': 'zip',
        }

    def _vat_book_get_txt_files(self, options, tax_type):
        """ Compute the date to be printed in the txt files"""
        lines = []
        invoices = self._vat_book_get_txt_invoices(options)
        aliquots = self._vat_book_get_REGINFO_CV_ALICUOTAS(options, tax_type, invoices)
        for v in aliquots.values():
            lines += v
        aliquots_data = '\r\n'.join(lines).encode('ISO-8859-1')
        vouchers_data = '\r\n'.join(self._vat_book_get_REGINFO_CV_CBTE(options, aliquots, tax_type, invoices)).encode('ISO-8859-1', 'ignore')
        return vouchers_data, aliquots_data

    ####################################################
    # HELPERS
    ####################################################

    def _vat_book_get_selected_tax_types(self, options):
        # If no particular one is selected, then select them all
        selected = options['ar_vat_book_tax_type_selected']
        return ['sale', 'purchase'] if selected == 'all' else [selected]

    @api.model
    def _vat_book_get_lines_domain(self, options):
        company_ids = self.env.company.ids
        selected_journal_types = self._vat_book_get_selected_tax_types(options)
        domain = [('journal_id.type', 'in', selected_journal_types),
                  ('journal_id.l10n_latam_use_documents', '=', True), ('company_id', 'in', company_ids)]
        state = options.get('all_entries') and 'all' or 'posted'
        if state and state.lower() != 'all':
            domain += [('state', '=', state)]
        if options.get('date').get('date_to'):
            domain += [('date', '<=', options['date']['date_to'])]
        if options.get('date').get('date_from'):
            domain += [('date', '>=', options['date']['date_from'])]
        return domain

    @api.model
    def _vat_book_format_amount(self, amount, padding=15, decimals=2):
        """ We need to represent float numbers as  integers, with a certain padding and taking into account certain
        decimals to take into account. For example:

            amount -2.1589 with default padding and decimales
            should return -00000000000215 which is:
               * a integer with padding 15 that includes the sign of the amount if negative
               * the integer part of the amount concatenate with 2 digits of the decimal part of the amount """
        template = "{:0" + str(padding) + "d}"
        (unitary_part, decimal_part) = float_split_str(amount, decimals)
        return template.format(int(unitary_part + decimal_part))

    @api.model
    def _vat_book_get_partner_document_code_and_number(self, partner):
        """ For a given partner turn the identification coda and identification number in the expected format for the
        txt files """
        # CUIT is mandatory for all except for final consummer
        if partner.l10n_ar_afip_responsibility_type_id.code == '5' or (
                partner.l10n_ar_afip_responsibility_type_id.code == '10' and not partner.commercial_partner_id.is_company):
            doc_code = f"{int(partner.l10n_latam_identification_type_id.l10n_ar_afip_code):0>2d}"
            doc_number = partner.vat or ''
            # we clean the letters that are not supported
            doc_number = re.sub("[^0-9]", "", doc_number)
        elif partner.l10n_ar_afip_responsibility_type_id.code == '9':
            commercial_partner = partner.commercial_partner_id
            doc_number = partner.l10n_ar_vat or (commercial_partner.country_id.l10n_ar_legal_entity_vat
                if commercial_partner.is_company else commercial_partner.country_id.l10n_ar_natural_vat)
            doc_code = '80'
            if not commercial_partner.country_id:
                raise RedirectWarning(
                    message=_("The partner '%s' does not have a country configured.", commercial_partner.name),
                    action={
                        'type': 'ir.actions.act_window',
                        'res_model': 'res.partner',
                        'views': [(False, 'form')],
                        'res_id': commercial_partner.id,
                        'name': _('Partner'),
                        'view_mode': 'form',
                    },
                    button_text=_('Edit Partner'),
                )
            if not doc_number:
                raise RedirectWarning(
                    message=_(
                        "The country '%s' does not have a '%s' configured.",
                        commercial_partner.country_id.name,
                        _('Legal Entity VAT') if commercial_partner.is_company else _('Natural Person VAT')
                    ),
                    action={
                        'type': 'ir.actions.act_window',
                        'res_model': 'res.country',
                        'views': [(False, 'form')],
                        'res_id': commercial_partner.country_id.id,
                        'name': _('Country'),
                        'view_mode': 'form',
                    },
                    button_text=_('Edit Country'),
                )
        else:
            doc_number = partner.ensure_vat()
            doc_code = '80'
        return doc_code, doc_number.rjust(20, '0')

    @api.model
    def _vat_book_get_pos_and_invoice_invoice_number(self, invoice):
        res = invoice._l10n_ar_get_document_number_parts(
            invoice.l10n_latam_document_number, invoice.l10n_latam_document_type_id.code)
        return f"{res['invoice_number']:0>20d}", f"{res['point_of_sale']:0>5d}"

    def _vat_book_get_txt_invoices(self, options):
        state = options.get('all_entries') and 'all' or 'posted'
        if state != 'posted':
            raise UserError(_('Can only generate TXT files using posted entries.'
                              ' Please remove Include unposted entries filter and try again'))

        domain = [('l10n_latam_document_type_id.code', '!=', False)] + self._vat_book_get_lines_domain(options)
        txt_type = options.get('txt_type')
        if txt_type == 'purchases':
            domain += [('l10n_latam_document_type_id.code', 'not in', ['66', '30', '32'])]
        elif txt_type == 'goods_import':
            domain += [('l10n_latam_document_type_id.code', '=', '66')]
        elif txt_type == 'used_goods':
            domain += [('l10n_latam_document_type_id.code', 'in', ['30', '32'])]
        return self.env['account.move'].search(domain, order='invoice_date asc, name asc, id asc')

    def _vat_book_get_tax_row(self, invoice, base, code, tax_amount, options, tax_type):
        inv = invoice
        impo = options.get('txt_type') == 'goods_import'

        invoice_number, pos_number = self._vat_book_get_pos_and_invoice_invoice_number(inv)
        doc_code, doc_number = self._vat_book_get_partner_document_code_and_number(inv.commercial_partner_id)
        if tax_type == 'sale':
            row = [
                f"{int(inv.l10n_latam_document_type_id.code):0>3d}",  # Field 1: Tipo de Comprobante
                pos_number,  # Field 2: Punto de Venta
                invoice_number,  # Field 3: Número de Comprobante
                self._vat_book_format_amount(base),  # Field 4: Importe Neto Gravado
                str(code).rjust(4, '0'),  # Field 5: Alícuota de IVA.
                self._vat_book_format_amount(tax_amount),  # Field 6: Impuesto Liquidado.
            ]
        elif impo:
            row = [
                (inv.l10n_latam_document_number or inv.name or '').rjust(16, '0'),  # Field 1: Despacho de importación.
                self._vat_book_format_amount(base),  # Field 2: Importe Neto Gravado
                str(code).rjust(4, '0'),  # Field 3: Alícuota de IVA
                self._vat_book_format_amount(tax_amount),  # Field 4: Impuesto Liquidado.
            ]
        else:
            row = [
                f"{int(inv.l10n_latam_document_type_id.code):0>3d}",  # Field 1: Tipo de Comprobante
                pos_number,  # Field 2: Punto de Venta
                invoice_number,  # Field 3: Número de Comprobante
                doc_code,  # Field 4: Código de documento del vendedor
                doc_number,  # Field 5: Número de identificación del vendedor
                self._vat_book_format_amount(base),  # Field 6: Importe Neto Gravado
                str(code).rjust(4, '0'),  # Field 7: Alícuota de IVA.
                self._vat_book_format_amount(tax_amount),  # Field 8: Impuesto Liquidado.
            ]
        return row

    def _vat_book_get_REGINFO_CV_CBTE(self, options, aliquots, tax_type, invoices):
        res = []

        for inv in invoices:
            aliquots_count = len(aliquots.get(inv))

            currency_rate = inv.l10n_ar_currency_rate
            currency_code = inv.currency_id.l10n_ar_afip_code

            invoice_number, pos_number = self._vat_book_get_pos_and_invoice_invoice_number(inv)
            doc_code, doc_number = self._vat_book_get_partner_document_code_and_number(inv.partner_id)

            amounts = inv._l10n_ar_get_amounts()
            vat_amount = amounts['vat_amount']
            vat_exempt_base_amount = amounts['vat_exempt_base_amount']
            vat_untaxed_base_amount = amounts['vat_untaxed_base_amount']
            other_taxes_amount = amounts['other_taxes_amount']
            vat_perc_amount = amounts['vat_perc_amount']
            iibb_perc_amount = amounts['iibb_perc_amount']
            mun_perc_amount = amounts['mun_perc_amount']
            intern_tax_amount = amounts['intern_tax_amount']
            perc_imp_nacionales_amount = amounts['profits_perc_amount'] + amounts['other_perc_amount']
            if inv.move_type in ('out_refund', 'in_refund') and \
                    inv.l10n_latam_document_type_id.code in inv._get_l10n_ar_codes_used_for_inv_and_ref():
                amount_total = -inv.amount_total
            else:
                amount_total = inv.amount_total

            if vat_exempt_base_amount:
                if inv.partner_id.l10n_ar_afip_responsibility_type_id.code == '10':  # free zone operation
                    operation_code = 'Z'
                elif inv.l10n_latam_document_type_id.l10n_ar_letter == 'E':          # exportation operation
                    operation_code = 'X'
                else:                                                                # exempt operation
                    operation_code = 'E'
            elif inv.l10n_latam_document_type_id.code == '66':                       # import clearance
                operation_code = 'E'
            elif vat_untaxed_base_amount:                                            # not taxed operation
                operation_code = 'N'
            else:
                operation_code = ' '
            row = [
                inv.invoice_date.strftime('%Y%m%d'),  # Field 1: Fecha de comprobante
                f"{int(inv.l10n_latam_document_type_id.code):0>3d}",  # Field 2: Tipo de Comprobante.
                pos_number,  # Field 3: Punto de Venta
                invoice_number,  # Field 4: Número de Comprobante
                # If it is a multiple-sheet receipt, the document number of the first sheet must be reported, taking into account the provisions of article 23, paragraph a), point 6. of General Resolution No. 1,415, the related resolutions that modify and complement this one.
                # In the case of registering grouped by daily totals, the first voucher number of the range to be considered must be entered.
            ]

            if tax_type == 'sale':
                # Field 5: Número de Comprobante Hasta: En el resto de los casos se consignará el dato registrado en el campo 4
                row.append(invoice_number)
            else:
                # Field 5: Despacho de importación
                if inv.l10n_latam_document_type_id.code == '66':
                    row.append((inv.l10n_latam_document_number).rjust(16, '0'))
                else:
                    row.append(''.rjust(16, ' '))
            row += [
                doc_code,  # Field 6: Código de documento del comprador.
                doc_number,  # Field 7: Número de Identificación del comprador
                inv.commercial_partner_id.name.ljust(30, ' ')[:30],  # Field 8: Apellido y Nombre del comprador.
                self._vat_book_format_amount(amount_total),  # Field 9: Importe Total de la Operación.
                self._vat_book_format_amount(vat_untaxed_base_amount),  # Field 10: Importe total de conceptos que no integran el precio neto gravado
            ]

            if tax_type == 'sale':
                row += [
                    self._vat_book_format_amount(0.0),  # Field 11: Percepción a no categorizados
                    # the "uncategorized / responsible not registered" figure is not used anymore
                    self._vat_book_format_amount(vat_exempt_base_amount),  # Field 12: Importe de operaciones exentas
                    self._vat_book_format_amount(perc_imp_nacionales_amount + vat_perc_amount),  # Field 13: Importe de percepciones o pagos a cuenta de impuestos Nacionales
                ]
            else:
                row += [
                    self._vat_book_format_amount(vat_exempt_base_amount),  # Field 11: Importe de operaciones exentas
                    self._vat_book_format_amount(vat_perc_amount),  # Field 12: Importe de percepciones o pagos a cuenta del Impuesto al Valor Agregado
                    self._vat_book_format_amount(perc_imp_nacionales_amount),  # Field 13: Importe de percepciones o pagos a cuenta otros impuestos nacionales
                ]

            row += [
                self._vat_book_format_amount(iibb_perc_amount),  # Field 14: Importe de percepciones de ingresos brutos
                self._vat_book_format_amount(mun_perc_amount),  # Field 15: Importe de percepciones de impuestos municipales
                self._vat_book_format_amount(intern_tax_amount),  # Field 16: Importe de impuestos internos
                str(currency_code),  # Field 17: Código de Moneda

                self._vat_book_format_amount(currency_rate, padding=10, decimals=6),  # Field 18: Tipo de Cambio
                # new modality of currency_rate

                str(aliquots_count),  # Field 19: Cantidad de alícuotas de IVA
                operation_code,  # Field 20: Código de operación.
            ]

            if tax_type == 'sale':
                document_codes = [
                    '16', '19', '20', '21', '22', '23', '24', '27', '28', '29', '33', '34', '35', '37', '38', '43', '44',
                    '45', '46', '47', '48', '49', '54', '55', '56', '57', '58', '59', '60', '61', '68', '81', '82', '83',
                    '110', '111', '112', '113', '114', '115', '116', '117', '118', '119', '120', '150', '151', '157',
                    '158', '159', '160', '161', '162', '163', '164', '165', '166', '167', '168', '169', '170', '171',
                    '172', '180', '182', '183', '185', '186', '188', '189', '190', '191',
                    '201', '202', '203', '206', '207', '208', '211', '212', '213', '331', '332']
                row += [
                    # Field 21: Otros Tributos
                    self._vat_book_format_amount(other_taxes_amount),

                    # Field 22: vencimiento comprobante
                    # NOTE: it does not appear in instructions but it does in application. for ticket and export invoice is not reported, also for some others but that we do not have implemented
                    inv.l10n_latam_document_type_id.code in document_codes and '00000000' or inv.invoice_date_due.strftime('%Y%m%d')
                ]
            else:
                row.append(self._vat_book_format_amount(0.0 if inv.company_id.l10n_ar_computable_tax_credit == 'global' else vat_amount))  # Field 21: Crédito Fiscal Computable

                liquido_type = inv.l10n_latam_document_type_id.code in ['33', '58', '59', '60', '63']
                row += [
                    self._vat_book_format_amount(other_taxes_amount),  # Field 22: Otros Tributos

                    # NOTE: still not implemented on this three fields for use case with third pary commisioner

                    # Field 23: CUIT Emisor / Corredor
                    # It will be reported only if the field 'Tipo de Comprobante' contains '33', '58', '59', '60' or '63'. if there is no intervention of third party in the operation then the informant VAT number will be reported. For the rest of the vouchers it will be completed with zeros
                    liquido_type and inv.company_id.partner_id.ensure_vat() or '0' * 11,

                    (liquido_type and inv.company_id.name or '').ljust(30, ' ')[:30],  # Field 24: Denominación Emisor / Corredor

                    # Field 25: IVA Comisión
                    # If field 23 is different from zero, then we will add the VAT tax base amount of thecommission
                    self._vat_book_format_amount(0),
                ]
            res.append(''.join(row))
        return res

    def _vat_book_get_REGINFO_CV_ALICUOTAS(self, options, tax_type, invoices):
        """ We return a dict to calculate the number of aliquots when we make the vouchers """
        res = OrderedDict()

        # only vat taxes with codes 3, 4, 5, 6, 8, 9. this follows what is mentioned in http://contadoresenred.com/regimen-de-informacion-de-compras-y-ventas-rg-3685-como-cargar-la-informacion/. We start counting codes 1 (not taxed) and 2 (exempt) if there are no aliquots, we add one of this with 0, 0, 0 in details. we also use mapped in case there are duplicate afip codes (eg manual and auto)
        for inv in invoices:
            lines = []
            vat_taxes = inv._get_vat()

            # typically this is for invoices with zero amount
            if not vat_taxes and any(t.tax_group_id.l10n_ar_vat_afip_code
                                     and t.tax_group_id.l10n_ar_vat_afip_code != '0'
                                     for t in inv.invoice_line_ids.mapped('tax_ids')):
                lines.append(''.join(self._vat_book_get_tax_row(inv, 0.0, 3, 0.0, options, tax_type)))

            # we group by afip_code
            for vat_tax in vat_taxes:
                lines.append(''.join(self._vat_book_get_tax_row(inv, vat_tax['BaseImp'], vat_tax['Id'], vat_tax['Importe'], options, tax_type)))

            res[inv] = lines

        return res
