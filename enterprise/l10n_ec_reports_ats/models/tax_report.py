# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _, api
from odoo.tools import float_repr, float_round, groupby
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.addons.l10n_ec.models.res_partner import PartnerIdTypeEc
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_VAT_TAX_NOT_ZERO_GROUPS

import unicodedata
import re
from collections import defaultdict

SALE_DOCUMENT_CODES = ['01', '02', '03', '04', '05']
LOCAL_PURCHASE_DOCUMENT_CODES = ['01', '02', '03', '04', '05', '09', '11', '12', '19', '20', '21', '43', '45', '47', '48']
ATS_SALE_DOCUMENT_TYPE = {
    '01': '18',
    '02': '18',
}


class L10nECTaxReportATSCustomHandler(models.AbstractModel):
    _inherit = 'account.tax.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if self.env.company.account_fiscal_country_id.code == 'EC':
            options['buttons'].append({
                'name': _('ATS'),
                'sequence': 60,
                'action': 'export_file',
                'action_param': 'l10n_ec_export_ats',
                'file_export_type': _('XML'),
            })

    def l10n_ec_export_ats(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        xml_str, errors = self._generate_ats(options)
        if errors and not options.get('l10n_ec_ats_ignore_errors'):
            error_msg = _('While preparing the data for the ATS export, we noticed the following missing or incorrect data.') + '\n\n'
            error_msg += '\n'.join(errors)
            action_vals = report.export_file({**options, 'l10n_ec_ats_ignore_errors': True}, 'l10n_ec_export_ats')
            raise RedirectWarning(error_msg, action_vals, _('Generate ATS'))

        report_name = 'ATS - ' + options['date']['string'] + ' - ' + report.get_default_report_filename(options, 'xml')
        return {
            'file_name': report_name,
            'file_content': xml_str,
            'file_type': 'xml',
        }

    def _generate_ats(self, options):
        # Generate ATS report
        # 2.1 Company information
        company = self.env.company
        if not company.account_fiscal_country_id.code == 'EC':
            raise ValidationError(_('This report is only available for Ecuadorian companies.'))
        date_start = fields.Date.to_date(options['date']['date_from'])
        date_finish = fields.Date.to_date(options['date']['date_to'])

        sale_journals = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', company.id),
            ('l10n_ec_entity', '!=', False),
        ])
        num_estab_ruc = len(set(sale_journals.mapped('l10n_ec_entity')))

        values = {
            'company': self.env.company,
            'latam_identification_type': self._l10n_ec_get_ats_identification_type_code(company.partner_id.l10n_latam_identification_type_id),
            'anio': date_finish.year,
            'mes': f'{date_finish.month:02}',
            'num_estab_ruc': f'{num_estab_ruc:03}',
            'format_float': lambda x: float_repr(float_round(x, 2), 2),
        }

        # Purchase documents
        purchase_vals, purchase_errors = self._get_purchase_values(date_start, date_finish)
        sale_vals, sale_errors = self._get_sale_values(date_start, date_finish)
        withhold_journals = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', company.id),
            ('l10n_ec_withhold_type', '=', 'in_withhold'),
        ]) # In withhold Journals
        journals = sale_journals + withhold_journals
        void_moves = self._get_void_moves(date_start, date_finish, journals)
        values.update({
            'purchase_vals': purchase_vals,
            'void_moves': void_moves,
            **sale_vals,
        })

        errors = purchase_errors + sale_errors

        return self.env['ir.qweb']._render('l10n_ec_reports_ats.ats_report_template', values), errors

    @api.model
    def _get_purchase_values(self, date_start, date_finish):
        """ Provide the values for the purchase section.
        For this section, invoice lines are grouped by invoice and by tax support. """

        def get_authorization_number(move):
            if move.l10n_ec_authorization_number:
                return move.l10n_ec_authorization_number.strip()
            # The government software does not allow to report documents without authorization number. If is not setted, send 9999999999.
            else:
                return '9999999999'

        def get_ec_type(taxes):
            return (taxes & ec_vat_taxes).tax_group_id.l10n_ec_type or 'zero_vat'

        def get_taxsupport(taxes):
            return (taxes & ec_vat_taxes).l10n_ec_code_taxsupport or '02'

        # Get all VAT taxes, including the ones that are archived like 12% since 29/02/2024
        ec_vat_taxes = self.env['account.tax'].with_context(active_test=False).search([
            ('tax_group_id.l10n_ec_type', 'not in', (False, 'ice', 'irbpnr', 'other')),
            ('company_id', '=', self.env.company.id),
        ])

        errors = []
        withhold_taxes_without_ats_code = self.env['account.tax']

        purchase_invoices = self.env['account.move'].search(
            [
                ('move_type', 'in', ('in_invoice', 'in_refund')),
                ('state', '=', 'posted'),
                ('l10n_latam_document_type_id.code', 'in', LOCAL_PURCHASE_DOCUMENT_CODES),
                ('date', '>=', date_start),
                ('date', '<=', date_finish),
                ('company_id', '=', self.env.company.id)
            ],
            order='invoice_date, move_type, l10n_latam_document_type_id, create_date',
        )

        purchase_vals = []
        for in_inv in purchase_invoices:
            is_from_ecuador = in_inv.commercial_partner_id.country_id == self.env.ref('base.ec')
            invoice_lines = in_inv.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note'))
            if is_from_ecuador and any(len(l.tax_ids & ec_vat_taxes) != 1 for l in invoice_lines):
                errors.append(_("%(invoice)s: Invoice lines should have exactly one VAT tax.", invoice=in_inv.name))
            if not is_from_ecuador and any(len(l.tax_ids & ec_vat_taxes) > 1 for l in invoice_lines):
                errors.append(
                    _("%(invoice)s: Import invoice lines should have at most one VAT tax.", invoice=in_inv.name)
                )

            # This will create base_amounts and tax_amounts dicts with this structure:
            # {
            #     'taxsupport': {
            #         'ec_tax_type': total of base lines / tax lines
            #     }
            # }
            # If an invoice line has no EC VAT tax on it, it will be reported with taxsupport '02' and tax type 'zero_vat'.
            # This could happen in the case of import invoices that are created without taxes.
            # In general, this ensures that all base lines are reported even if they are missing a tax.

            sign = 1 if in_inv.move_type == 'in_invoice' else -1
            base_amounts = defaultdict(lambda: defaultdict(int), {
                taxsupport: defaultdict(int, {
                                ec_type: sign * sum(base_line.balance for base_line in base_lines_per_ec_type)
                                for ec_type, base_lines_per_ec_type in groupby(base_lines_per_taxsupport, lambda l: get_ec_type(l.tax_ids))
                            })
                for taxsupport, base_lines_per_taxsupport in groupby(invoice_lines, lambda l: get_taxsupport(l.tax_ids))
            })

            tax_lines = in_inv.line_ids.filtered(lambda l: l.tax_line_id & ec_vat_taxes)
            tax_amounts = defaultdict(lambda: defaultdict(int), {
                taxsupport: defaultdict(int, {
                                ec_type: sign * sum(tax_line.balance for tax_line in tax_lines_per_ec_type)
                                for ec_type, tax_lines_per_ec_type in groupby(tax_lines_per_taxsupport, lambda l: get_ec_type(l.tax_line_id))
                            })
                for taxsupport, tax_lines_per_taxsupport in groupby(tax_lines, lambda l: get_taxsupport(l.tax_line_id))
            })

            # 1. INVOICE-RELATED FIELDS
            # 1.1. General fields
            transaction_type = PartnerIdTypeEc.get_ats_code_for_partner(in_inv.partner_id, in_inv.move_type).value
            id_prov, validation_errors = self._l10n_ec_get_validated_partner_vat(in_inv.partner_id)
            errors += validation_errors
            parte_rel = 'SI' if in_inv.commercial_partner_id.l10n_ec_related_party else 'NO'
            estab_inv, emision_inv, secuencial_inv = self._l10n_ec_get_document_number_vals(in_inv)

            inv_values = {
                'tpIdProv': transaction_type,
                'idProv': id_prov,
                'tipoComprobante': self._get_l10n_latam_ats_document_code(in_inv),
                'parteRel': parte_rel,
                'fechaRegistro': in_inv.date.strftime('%d/%m/%Y'),
                'establecimiento': estab_inv,
                'puntoEmision': emision_inv,
                'secuencial': secuencial_inv,
                'fechaEmision': in_inv.invoice_date.strftime('%d/%m/%Y'),
                'autorizacion': get_authorization_number(in_inv),
            }
            if in_inv.l10n_ec_sri_payment_id.code:
                inv_values.update({
                    'formasDePago': in_inv._l10n_ec_get_formas_de_pago(),
                })

            # 1.2. Provide the partner name if ID is passport/foreign
            if transaction_type == '03':
                natural_society = in_inv.commercial_partner_id._get_l10n_ec_edi_supplier_identification_type_code()
                natural_society_name = self._l10n_ec_get_normalized_name(in_inv.partner_id.commercial_company_name or in_inv.partner_id.name)
                inv_values.update({
                    'tipoProv': natural_society,
                    'denoProv': natural_society_name,
                })

            # 1.3. Local / foreign data
            foreign_data = in_inv._l10n_ec_wth_get_foreign_data()
            pago_local_extranjero = foreign_data['identification']
            paying_country = in_inv.commercial_partner_id.country_id.l10n_ec_code_ats or 'NA'

            if pago_local_extranjero == '01':  # In Ecuador
                inv_values.update({
                    'pagoLocExt': pago_local_extranjero,
                    'paisEfecPago': 'NA',
                    'aplicConvDobTrib': 'NA',
                    'pagExtSujRetNorLeg': 'NA',
                })
            else:
                # General regime (01) is assumed
                inv_values.update({
                    'tipoRegi': '01',
                    'paisEfecPagoGen': paying_country,
                    'pagoLocExt': pago_local_extranjero,
                    'paisEfecPago': paying_country,
                    'aplicConvDobTrib': foreign_data['double_taxation'],
                    'pagExtSujRetNorLeg': foreign_data['subject_withhold'],
                })

            # 1.4. Credit note / debit note data
            if in_inv.l10n_latam_document_type_id.code in ('04', '05'):
                modified_move = in_inv.reversed_entry_id or in_inv.debit_origin_id
                if not modified_move:
                    errors.append(
                        _(
                            "%(invoice)s: The credit (NCs) or debit (NDs) note doesn't have the invoice that modifies it. It must be created from the original invoice",
                            invoice=in_inv.name,
                        ),
                    )
                else:
                    estab_mod, emision_mod, secuencial_mod = self._l10n_ec_get_document_number_vals(modified_move)
                    inv_values.update({
                        'docModificado': modified_move.l10n_latam_document_type_id.code or '',
                        'estabModificado': estab_mod,
                        'ptoEmiModificado': emision_mod,
                        'secModificado': secuencial_mod,
                        'autModificado': get_authorization_number(modified_move),
                    })

            inv_values.update({
                'totbasesImpReemb': sum(reimbursement._get_tax_amounts_converted(reimbursement.tax_base)
                                        for reimbursement in in_inv.l10n_ec_reimbursement_ids)
            })
            # 2. INVOICE LINE VALUES BY TAX SUPPORT
            for taxsupport in base_amounts:
                values = inv_values.copy()

                # 2.1. VAT base / tax data
                values.update({
                    'codSustento': taxsupport,
                    'baseNoGraIva': base_amounts[taxsupport]['not_charged_vat'],
                    'baseImponible': base_amounts[taxsupport]['zero_vat'],
                    'baseImpGrav': sum(base_amounts[taxsupport].get(ec_type, 0.0) for ec_type in L10N_EC_VAT_TAX_NOT_ZERO_GROUPS),
                    'baseImpExe': base_amounts[taxsupport]['exempt_vat'],
                    'montoIva': sum(tax_amounts[taxsupport].get(ec_type, 0.0) for ec_type in L10N_EC_VAT_TAX_NOT_ZERO_GROUPS),
                })

                # 2.2. VAT withholdings
                withhold_lines = in_inv.l10n_ec_related_withhold_line_ids.filtered(
                    lambda l: l.parent_state == 'posted' and l.l10n_ec_code_taxsupport == taxsupport
                )
                withhold_tax_lines = withhold_lines.filtered(lambda l: l.tax_line_id)
                withhold_amounts = {
                    code: abs(sum(tax_line.balance for tax_line in tax_lines))
                    for code, tax_lines in groupby(withhold_tax_lines, lambda l: l.tax_line_id.l10n_ec_code_applied)
                }
                # For credit notes, report the reversed amount of VAT.
                is_credit_note = in_inv.l10n_latam_document_type_id.internal_type == 'credit_note'
                values.update({
                    'valRetBien10': withhold_amounts.get('721', 0.0),
                    'valRetServ20': withhold_amounts.get('723', 0.0),
                    'valorRetBienes': withhold_amounts.get('725', 0.0),
                    'valRetServ50': withhold_amounts.get('727', 0.0),
                    'valorRetServicios': withhold_amounts.get('729', 0.0),
                    'valRetServ100': withhold_amounts.get('731', 0.0),
                    'valorRetencionNc': sum(withhold_tax_lines.mapped('balance')) if is_credit_note else 0.0,
                })

                # 2.3 Income tax withholdings
                income_withhold_base_lines = withhold_lines.filtered(lambda l: l.tax_ids.tax_group_id.l10n_ec_type in ['withhold_income_purchase'])
                if income_withhold_base_lines:
                    withhold_taxes_without_ats_code |= income_withhold_base_lines.tax_ids.filtered(
                        lambda t: not t.l10n_ec_code_ats or len(t.l10n_ec_code_ats) < 3
                    )

                    air_vals = [
                        {
                            'codRetAir': tax.l10n_ec_code_ats or 'NA',
                            'porcentajeAir': abs(tax.amount),
                            'baseImpAir': abs(sum(base_line.balance for base_line in base_lines)),
                            'valRetAir': abs(withhold_lines.filtered(lambda l: l.tax_line_id == tax).balance or 0.0)
                        }
                        for tax, base_lines in groupby(income_withhold_base_lines, lambda l: l.tax_ids)
                    ]
                    withhold = income_withhold_base_lines.move_id
                    estab_ret, emision_ret, secuencial_ret = self._l10n_ec_get_document_number_vals(withhold)

                    values.update({
                        'air_vals': air_vals,
                        'estabRetencion1': estab_ret,
                        'ptoEmiRetencion1': emision_ret,
                        'secRetencion1': secuencial_ret,
                        'autRetencion1': get_authorization_number(withhold),
                        'fechaEmiRet1': withhold.l10n_ec_withhold_date.strftime('%d/%m/%Y'),
                    })

                # 2.4. DIVIDEND WITHHOLDINGS ARE NOT SUPPORTED
                #   - Dividend Payment Date
                #   - Income tax paid by the company corresponding to the dividend
                #   - Year in which the profits attributable to the dividend were generated

                # 2.5. WITHHOLDS FOR BANANA IMPORTS ARE NOT SUPPORTED
                #   - Quantity of standard banana boxes
                #   - Price of standard banana boxes
                #   - Banana box price
                self._get_reimbursements_values(in_inv, values, errors)

                purchase_vals.append(values)
        error_template = _("%s: IR tax without 3 digit ats code")
        for tax in withhold_taxes_without_ats_code:
            errors.append(error_template % tax.name)

        return purchase_vals, errors

    def _get_reimbursements_values(self, in_inv, values, errors):
        def _append_error_messages_seq(reimbursement):
            sequential_inv = self.with_context(from_reimbursement=True)._l10n_ec_get_number_vals(reimbursement.document_number)[2]  # sequential
            if not sequential_inv:
                errors.append('In reimbursement %s the invoice %s does not have sequential.' %
                              (reimbursement.move_id.l10n_latam_document_number, reimbursement.document_number))
            if reimbursement.authorization_number and len(reimbursement.authorization_number) not in [10, 37, 49]:
                errors.append('In reimbursement %s the invoice %s has an incomplete authorization.' %
                              (reimbursement.move_id.l10n_latam_document_number, reimbursement.document_number))

        def _append_error_messages_partner_vat(reimbursements):
            no_vat_reimbursements = reimbursements.filtered(lambda r: not r.partner_id.vat)
            if no_vat_reimbursements:
                mess_error = ', '.join('%s' % name for name in no_vat_reimbursements.partner_id.mapped('name'))
                errors.append('In reimbursement %s  exists a partner without VAT number setted (%s).' % (no_vat_reimbursements.move_id.name, mess_error))

        if not in_inv._l10n_ec_is_purchase_reimbursement():
            return False

        _append_error_messages_partner_vat(in_inv.l10n_ec_reimbursement_ids)

        def _get_ats_code_prov_reimbursement(reimbursement):
            partner_type_id = reimbursement._get_identification_type()
            if partner_type_id == 'ruc':
                return PartnerIdTypeEc.IN_RUC.value
            return PartnerIdTypeEc.IN_PASSPORT.value

        reimbursements_vals = []
        # Whether there are more than one reimbursement with the same document_number, it's because this invoice has multiple vat tax
        # In the ATS we must group by document number and accumulate the tax bases
        for number_and_partner, reimburs_move in groupby(in_inv.l10n_ec_reimbursement_ids.sorted(lambda l: l.document_number), lambda i: (i.document_number, i.partner_id.commercial_partner_id)):
            amounts_vals = defaultdict(float)
            reimburs_list = list(reimburs_move)
            reimbursement_val = {}
            for reimbursement in reimburs_list:
                _append_error_messages_seq(reimbursement)
                amounts_by_tax_type = self._get_reimbursements_amounts(reimburs=reimbursement)
                amounts_vals['base_vat_0'] += amounts_by_tax_type['base_vat_0']
                amounts_vals['base_vat_no0'] += amounts_by_tax_type['base_vat_no0']
                amounts_vals['no_vat_amount'] += amounts_by_tax_type['no_vat_amount']
                amounts_vals['base_tax_free'] += amounts_by_tax_type['base_tax_free']
                amounts_vals['ice_amount'] += amounts_by_tax_type['ice_amount']
                amounts_vals['vat_amount_no0'] += amounts_by_tax_type['vat_amount_no0']

            reimburs = reimburs_list[0]
            estab_inv, emision_inv, secuencial_inv = self.with_context(from_reimbursement=True)._l10n_ec_get_number_vals(reimburs.document_number)
            reimbursement_val.update({
                'tipoComprobanteReemb': reimburs.l10n_latam_document_type_id.code or '',
                'tpIdProvReemb': _get_ats_code_prov_reimbursement(reimburs),
                'idProvReemb': reimburs.partner_vat_number,
                'establecimientoReemb': estab_inv,
                'puntoEmisionReemb': emision_inv,
                'secuencialReemb': secuencial_inv,
                'fechaEmisionReemb': reimburs.date.strftime('%d/%m/%Y'),
                'autorizacionReemb': reimburs.authorization_number or '9999999999',
                'baseImponibleReemb': reimburs._get_tax_amounts_converted(amounts_vals['base_vat_0']),
                'baseImpGravReemb': reimburs._get_tax_amounts_converted(amounts_vals['base_vat_no0']),
                'baseNoGraIvaReemb': reimburs._get_tax_amounts_converted(amounts_vals['no_vat_amount']),
                'baseImpExeReemb': reimburs._get_tax_amounts_converted(amounts_vals['base_tax_free']),
                'montoIceRemb': reimburs._get_tax_amounts_converted(amounts_vals['ice_amount']),
                'montoIvaRemb': reimburs._get_tax_amounts_converted(amounts_vals['vat_amount_no0']),

            })
            reimbursements_vals.append(reimbursement_val)
        values.update({
            'reimbursement_vals': reimbursements_vals
        })

    def _get_reimbursements_amounts(self, reimburs):
        # We need separate the amounts by tax_group type because of the tags in ATS
        ec_type = reimburs.tax_id.tax_group_id.l10n_ec_type
        return {
            'base_vat_no0': ec_type in L10N_EC_VAT_TAX_NOT_ZERO_GROUPS and reimburs.tax_base or 0.0,
            'vat_amount_no0': ec_type in L10N_EC_VAT_TAX_NOT_ZERO_GROUPS and reimburs.tax_amount or 0.0,
            'base_vat_0': ec_type == 'zero_vat' and reimburs.tax_base or 0.0,
            'no_vat_amount': ec_type == 'not_charged_vat' and reimburs.tax_base or 0.0,
            'base_tax_free':  ec_type == 'exempt_vat' and reimburs.tax_base or 0.0,
            'ice_amount': 0.0,  # ICE is not supported yet
        }

    def _get_void_moves(self, date_start, date_finish, journals):
        # Creates the cancelled document section
        void_invoices = self.env['account.move'].search(
            [
                ('move_type', 'in', self.env['account.move'].get_invoice_types()),
                ('state', '=', 'cancel'),
                ('name', 'not in', ('/', False)),    # filter out cancelled draft account moves
                ('l10n_latam_document_type_id.code', 'in', SALE_DOCUMENT_CODES + LOCAL_PURCHASE_DOCUMENT_CODES),
                ('date', '>=', date_start),
                ('date', '<=', date_finish),
                ('company_id', '=', self.env.company.id)
            ],
            order='invoice_date, move_type, l10n_latam_document_type_id, create_date',
        )
        void_invoices = void_invoices.filtered(lambda move: move.journal_id.l10n_ec_require_emission) # Filter only invoces emitted by the company
        withhold_journals = journals.filtered(lambda journal: journal.l10n_ec_withhold_type == 'in_withhold')
        # If the withholding does not have an authorization number, it is not reported. The authorization number indicates that it is an electronic or pre-printed withhold.
        void_withholds = self.env['account.move'].search(
            [
                ('move_type', 'in', ['entry']),
                ('state', '=', 'cancel'),
                ('name', 'not in', ('/', False)),    # filter out cancelled draft account moves
                ('journal_id', 'in', withhold_journals._ids),
                ('date', '>=', date_start),
                ('date', '<=', date_finish),
                ('l10n_ec_authorization_number', '!=', False),
                ('company_id', '=', self.env.company.id)
            ],
            order='invoice_date, move_type, l10n_latam_document_type_id, create_date',
        )
        void_moves = void_invoices + void_withholds
        return void_moves

    @api.model
    def _get_sale_values(self, date_start, date_finish):
        total_sales = 0.0

        invoices_values, errors = self._get_invoices_values(date_start, date_finish)
        # Order sale invoice by partner RUC. _get_sales_info_by_partner groups invoices by partner vat.
        sale_vals, sales_info_errors = self._get_sales_info_by_partner(invoices_values)
        errors += sales_info_errors

        values = {}
        if sale_vals:
            for id_partner in sale_vals:
                # Electronic invoices should not be added up in total sales, only old preprinted invoices
                if sale_vals[id_partner]['tipoEmision'] == 'F':
                    total_sales += sale_vals[id_partner]['amount_untaxed_signed']
            # Get all the establishments registered at the SRI
            sale_journals = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', self.env.company.id),
                ('l10n_ec_entity', '!=', False),
            ])
            entities = list(set(sale_journals.mapped('l10n_ec_entity')))
            entities.sort()

            values.update({
                'sale_vals': sale_vals,
                'entities': entities,
                'total_entity_vals': self._l10n_ec_get_total_by_entity(invoices_values),
            })

        values.update({
            'total_sales': '{0:.2f}'.format(total_sales)
        })

        return values, errors

    @api.model
    def _get_invoices_values(self, date_start, date_finish):

        def get_ec_type(taxes):
            return (taxes & ec_vat_taxes).tax_group_id.l10n_ec_type or 'zero_vat'

        # Get all VAT taxes, including the ones that are archived like 12% since 29/02/2024
        ec_vat_taxes = self.env['account.tax'].with_context(active_test=False).search([
            ('tax_group_id.l10n_ec_type', 'not in', (False, 'ice', 'irbpnr', 'other')),
            ('company_id', '=', self.env.company.id),
        ])

        errors = []
        invoices = self.env['account.move'].search(
            [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('l10n_latam_document_type_id.code', 'in', SALE_DOCUMENT_CODES),
                ('date', '>=', date_start),
                ('date', '<=', date_finish),
                ('company_id', '=', self.env.company.id),
            ],
            order='partner_id, l10n_latam_document_type_id, invoice_date, l10n_ec_authorization_number, create_date',
        )

        invoices_values = []
        error_template = _("%s: Invoice lines should have exactly one VAT tax.")
        for invoice in invoices:
            invoice_lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note'))
            if any(len(l.tax_ids & ec_vat_taxes) != 1 for l in invoice_lines):
                errors.append(error_template % invoice.name)

            # This will create base_amounts and tax_amounts dicts with this structure:
            # {
            #     'ec_tax_type': total of base lines / tax lines
            # }
            # If an invoice line has no EC VAT tax on it, it will be reported with tax type 'zero_vat'.
            # This ensures that all base lines are reported even if they are missing a tax.

            sign = -1 if invoice.move_type == 'out_invoice' else 1
            base_amounts = defaultdict(int, {
                ec_type: sign * sum(base_line.balance for base_line in base_lines)
                for ec_type, base_lines in groupby(invoice_lines, lambda l: get_ec_type(l.tax_ids))
            })
            tax_lines = invoice.line_ids.filtered(lambda l: l.tax_line_id & ec_vat_taxes)
            tax_amounts = defaultdict(int, {
                ec_type: sign * sum(tax_line.balance for tax_line in tax_lines)
                for ec_type, tax_lines in groupby(tax_lines, lambda l: get_ec_type(l.tax_line_id))
            })

            # tipoEmision: F = Física, E = Electrónica
            is_manual = (
                invoice.l10n_ec_authorization_number and len(invoice.l10n_ec_authorization_number) == 10
                or not any(edi_doc for edi_doc in invoice.edi_document_ids if edi_doc.edi_format_id == self.env.ref('l10n_ec_edi.ecuadorian_edi_format'))
            )
            emission_type = 'F' if is_manual else 'E'

            invoice_vals = {
                'move': invoice,
                'move_type': invoice.move_type,
                'partner': invoice.partner_id,
                'latam_document_type_code': invoice.l10n_latam_document_type_id.code,
                'entity_point': invoice.journal_id.l10n_ec_entity,
                'l10n_latam_document_number': invoice.l10n_latam_document_number,
                'journal_entity': invoice.journal_id.l10n_latam_use_documents and invoice.journal_id.active,
                'tipoComprobante': self._get_l10n_latam_ats_document_code(invoice),
                'tipoEmision': emission_type,
                'baseNoGraIva': base_amounts['exempt_vat'] + base_amounts['not_charged_vat'],
                'baseImponible': base_amounts['zero_vat'],
                'baseImpGrav': sum(base_amounts.get(ec_type, 0.0) for ec_type in L10N_EC_VAT_TAX_NOT_ZERO_GROUPS),
                'montoIva': sum(tax_amounts.get(ec_type, 0.0) for ec_type in L10N_EC_VAT_TAX_NOT_ZERO_GROUPS),
                'amount_untaxed_signed': invoice.amount_untaxed_signed,
            }
            if invoice.l10n_ec_sri_payment_id.code:
                invoice_vals.update({
                    'formasDePago': invoice._l10n_ec_get_formas_de_pago(),
                })
            invoices_values.append(invoice_vals)
        return invoices_values, errors

    @api.model
    def _get_sales_info_by_partner(self, invoices_values):
        group_sales = {}
        errors = []

        # The ATS validates by partner identification number. We must get the commercial partner instead of the partner
        for id_partner, partner_invoices_values in groupby(invoices_values, key=lambda m: (m['partner'].commercial_partner_id, m['latam_document_type_code'], m['tipoEmision'])):
            partner = partner_invoices_values[0]['partner']
            identification_type_code = PartnerIdTypeEc.get_ats_code_for_partner(partner, 'out_').value
            id_cliente, validation_errors = self._l10n_ec_get_validated_partner_vat(partner)
            errors += validation_errors

            values = {
                'numeroComprobantes': len(partner_invoices_values),
                'tipoComprobante': partner_invoices_values[0]['tipoComprobante'],
                'tipoEmision': partner_invoices_values[0]['tipoEmision'],
                'compensaciones': {'tipoCompe': '0', 'monto': 0}, # Compensations apply only to utility companies. Out of scope.
                'tpIdCliente': identification_type_code or '',
                'idCliente': id_cliente or '',
                'valorRetIva': 0.0,
                'valorRetRenta': 0.0,
                'baseNoGraIva': sum(invoices_values['baseNoGraIva'] for invoices_values in partner_invoices_values),
                'baseImponible': sum(invoices_values['baseImponible'] for invoices_values in partner_invoices_values),
                'baseImpGrav': sum(invoices_values['baseImpGrav'] for invoices_values in partner_invoices_values),
                'montoIva': sum(invoices_values['montoIva'] for invoices_values in partner_invoices_values),
                'amount_untaxed_signed': sum(invoices_values['amount_untaxed_signed'] for invoices_values in partner_invoices_values),
            }
            if partner_invoices_values[0].get('formasDePago', False):
                values.update({
                    'formasDePago': partner_invoices_values[0]['formasDePago'],
                })

            # Conditional field only when the supplier code type is equal to
            #   - 04: RUC
            #   - 05: CEDULA
            #   - 06: PASSPORT
            # Also is conditional with the document type code
            #   - 18: is the ATS document code for  '01' and '02' sales types
            #   - 04: Credit Notes
            #   - 05: Debit Notes
            #   - 44: Contributions and Contribution Voucher
            if (identification_type_code in ['04', '05', '06'] and
                    any(invoice_values['tipoComprobante'] in ['18', '04', '05', '44'] for invoice_values in partner_invoices_values)):
                values.update({
                    'parteRelVtas': 'SI' if partner.l10n_ec_related_party else 'NO'
                })

            if identification_type_code == '06':
                values.update({
                    'tipoCliente': '02' if partner.is_company else '01',
                    'denoCli': partner.commercial_partner_id.commercial_company_name or partner.commercial_partner_id.name
                })
            group_sales[id_partner] = values
        return group_sales, errors

    # =====  HELPERS  =====
    @api.model
    def _l10n_ec_get_ats_identification_type_code(self, identificaction_type):
        id_types_by_xmlid = {
            'l10n_ec.ec_dni': 'C',  # DNI
            'l10n_ec.ec_ruc': 'R',  # RUC
            'l10n_ec.ec_passport': 'P',  # EC passport
            'l10n_latam_base.it_pass': 'P',  # Passport
            'l10n_latam_base.it_fid': 'P',  # Foreign ID
            'l10n_latam_base.it_vat': 'P', # Foreign Vat
        }
        ats_id_type_code = '' # If there is no identification type, returns an empty string
        xmlid_by_res_id = {
            self.env['ir.model.data']._xmlid_to_res_model_res_id(xmlid, raise_if_not_found=True)[1]: xmlid
            for xmlid in id_types_by_xmlid
        }
        id_type_xmlid = xmlid_by_res_id.get(identificaction_type.id)
        if id_type_xmlid in id_types_by_xmlid:
            ats_id_type_code = id_types_by_xmlid[id_type_xmlid]
        if identificaction_type.country_id.code != 'EC':
            ats_id_type_code = 'P'
        return ats_id_type_code

    @api.model
    def _l10n_ec_get_total_by_entity(self, invoices_values):
        entity_totals = defaultdict(lambda: {
            'total': 0.0,
            'ivaComp': 0.0 # Compensations apply only to utility companies. Out of scope.
        })
        for invoice_values in invoices_values:
            # ATS electronic documents are excluded
            if invoice_values['tipoEmision'] == 'F':
                entity_point = invoice_values['entity_point']
                invoice_subtotal = invoice_values['baseImponible'] + invoice_values['baseImpGrav']
                invoice_subtotal = invoice_subtotal * (1 if invoice_values['move_type'] == 'out_invoice' else -1)
                entity_totals[entity_point]['total'] += invoice_subtotal
        return entity_totals

    @api.model
    def _l10n_ec_get_validated_partner_vat(self, partner):
        """ Return the validated and truncated (if necessary) partner ID:

        - All ID types must have at least 3 characters.
        - Foreign, passport and ec_passport types are truncated to 13 characters.
        - Other ID types are not allowed.
        """
        errors = []
        partner_vat = partner.commercial_partner_id.vat
        ec_id_type = partner._l10n_ec_get_identification_type()
        if (partner_vat and len(partner_vat) < 3) or not partner_vat:
            errors.append(_("The identification number of contact %s must have at least 3 characters.", partner.name))
        elif ec_id_type in ['passport', 'ec_passport', 'foreign']:
            # The regulations indicate that the first 13 digits be chosen.
            partner_vat = (partner_vat and partner_vat[:13]) or ''
        elif not ec_id_type:
            errors.append(
                _(
                    'Valid types of identification for the ATS report are: Cédula, Ruc, Passport, Foreign ID. Contact %(partner)s has type "%(type)s".',
                    partner=partner.name,
                    type=partner.l10n_latam_identification_type_id.name,
                )
            )
        return partner_vat, errors

    def _l10n_ec_get_document_number_vals(self, move):
        # Get the values ​​of the authorization number, establishment, emission point and sequential
        # of the document to be reported in the ATS
        move.ensure_one()
        estab, emision, sequential = self._l10n_ec_get_number_vals(move.l10n_latam_document_number)
        if (
                estab + emision + sequential == '0' * 15 and
                move.country_code == 'EC' and  # Is an Ecuadorian document
                move.l10n_latam_document_number and  # Has a document number
                not move.l10n_latam_document_type_id.l10n_ec_check_format  # Document type format not checked
        ):
            estab, emision, sequential = '999', '999', move.l10n_latam_document_number[-8:]

        return estab.zfill(3), emision.zfill(3), sequential.zfill(9)

    def _l10n_ec_get_number_vals(self, number):
        estab, emision, sequential = '', '', ''
        num_match = re.match(r'(?:Ret )?(\d{1,3})-(\d{1,3})-(\d{1,9})', number.strip())
        if num_match:
            estab, emision, sequential = num_match.groups()
        return estab.zfill(3), emision.zfill(3), sequential.zfill(9)

    @api.model
    def _l10n_ec_get_normalized_name(self, name):

        def get_printable_ASCII_text(text):
            mapping = {
                'ñ': 'n',
                'Ñ': 'N',
                '&': 'Y',
                '_': ' '
                }
            ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore')
            pattern = re.compile("|".join('(%s)' % re.escape(x) for x in mapping))
            ascii_replaced = pattern.sub(lambda m: mapping[m.group(0)], ascii_text.decode('utf-8'))
            return ascii_replaced.strip()

        text = name
        if text:
            text = text.replace('.', '')
            text = text.replace(',', '')
            text = text.replace('-', ' ')
            text = text.replace('/', ' ')
            text = text.replace('(', '')
            text = text.replace(')', '')
            text = text.replace(u'´', ' ')
            text = get_printable_ASCII_text(text)
        return text

    @api.model
    def _get_l10n_latam_ats_document_code(self, move):
        # Code mapping in special cases.
        move.ensure_one()
        document_code = move.l10n_latam_document_type_id.code
        if move.is_sale_document() and ATS_SALE_DOCUMENT_TYPE.get(document_code, False):
            return ATS_SALE_DOCUMENT_TYPE[document_code]
        elif move._l10n_ec_is_purchase_reimbursement():  # if the move is a reimbursement, the code is 41
            return '41'
        return document_code
