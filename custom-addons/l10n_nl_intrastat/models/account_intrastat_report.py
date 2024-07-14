# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, release, _
from odoo.exceptions import ValidationError

from datetime import datetime, date
from math import copysign


class IntrastatReportCustomHandler(models.AbstractModel):
    _inherit = 'account.intrastat.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.partner_id.country_id.code != 'NL':
            return

        cbs_button = {
            'name': _('CBS'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'l10n_nl_export_to_csv',
            'file_export_type': _('CBS'),
        }
        options['buttons'].append(cbs_button)

    def _show_region_code(self):
        # The region code is irrelevant for the Netherlands and will always be an empty column, with
        # this function we can conditionally exclude it from the report.
        if self.env.company.account_fiscal_country_id.code == 'NL':
            return False
        return super()._show_region_code()

    @api.model
    def l10n_nl_export_to_csv(self, options):
        """ Export the Centraal Bureau voor de Statistiek (CBS) file.

        Documentation found in:
        https://www.cbs.nl/en-gb/participants-survey/overzicht/businesses/onderzoek/international-trade-in-goods/idep-code-lists

        :param options: The report options.
        :return:        Info dict needed by the export button with:
                        - file_name
                        - file_content
                        - file_type
        """
        #pylint: disable=sql-injection
        # Fetch data.
        self.env['account.move.line'].check_access_rights('read')

        company = self.env.company
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']

        query, params = self._prepare_query(options)

        self._cr.execute(query, params)
        query_res = self._cr.dictfetchall()
        query_res = self._fill_missing_values(query_res)
        line_map = dict((l.id, l) for l in self.env['account.move.line'].browse(res['id'] for res in query_res))

        # Create csv file content.
        vat = company.vat
        now = datetime.now()
        registration_number = company.l10n_nl_cbs_reg_number or ''
        software_version = release.version

        # The software_version looks like saas~11.1+e but we have maximum 5 characters allowed
        software_version = software_version.replace('saas~', '').replace('+e', '').replace('alpha', '')

        # Changes to the format of the transaction codes require different report structures
        # The old transaction codes are single-digit
        if fields.Date.to_date(date_to) < date(2022, 1, 1):
            if all(len(str(res['transaction_code'])) == 1 for res in query_res):
                new_codes = False
            elif all(len(str(res['transaction_code'])) == 2 for res in query_res) \
                 and fields.Date.to_date(date_from).year == 2021:
                new_codes = True
            else:
                raise ValidationError(_(
                    "The transaction codes that have been used are inconsistent with the time period. Before January 2021 "
                    "the transaction codes for a period should consist of single-digits only. Before January 2022 transactions codes should "
                    "consist of exclusively single-digits or double-digits. Please ensure all transactions in the "
                    "specified period utilise the correct transaction codes."
                ))
        else:
            if all(len(str(res['transaction_code'])) == 2 for res in query_res):
                new_codes = True
            else:
                raise ValidationError(_(
                    "The transaction codes that have been used are inconsistent with the time period. From the start of "
                    "January 2022 onwards the transaction codes should consist of two digits only (no single-digit codes). Please "
                    "ensure all transactions in the specified period utilise the correct transaction codes."
                ))

        # HEADER LINE
        file_content = ''.join([
            '9801',                                                             # Record type           length=4
            vat and vat[2:].replace(' ', '').ljust(12) or ''.ljust(12),         # VAT number            length=12
            date_from[:4] + date_from[5:7],                                     # Review period         length=6
            (company.name or '').ljust(40),                                     # Company name          length=40
            registration_number.ljust(6),                                       # Registration number   length=6
            software_version.ljust(5),                                          # Version number        length=5
            now.strftime('%Y%m%d'),                                             # Creation date         length=8
            now.strftime('%H%M%S'),                                             # Creation time         length=6
            company.phone and \
            company.phone.replace(' ', '')[:15].ljust(15) or ''.ljust(15),      # Telephone number      length=15
            ''.ljust(13),                                                       # Reserve               length=13
        ]) + '\n'

        # CONTENT LINES
        i = 1
        for res in query_res:
            line = line_map[res['id']]
            inv = line.move_id
            country_dest_code = inv.partner_shipping_id.country_id and inv.partner_shipping_id.country_id.code or ''
            country_origin_code = res['intrastat_product_origin_country_code'] if res['type'] == 'Dispatch' and fields.Date.to_date(date_to) > date(2022, 1, 1) else ''
            country = inv.intrastat_country_id.code and inv.intrastat_country_id.code or '' if res['type'] == 'Arrival' else country_dest_code

            # From the Manual for Statistical Declarations International Trade in Goods:
            #
            # For commodities where no supplementary unit is given, the weight has te be reported,
            # rounded off in kilograms.
            # [...]
            # Weights below 1 kilogram should be rounded off above.
            #
            # Therefore:
            #  5.2 => 5; -5.2 => -5; 0.2 => 1; -0.2 => -1
            # If the mass is zero, we leave it like this: it means the user forgot to set the weight
            # of the products, so it should be corrected.
            mass = line.product_id and line.quantity * (line.product_id.weight or line.product_id.product_tmpl_id.weight) or 0
            if mass:
                mass = copysign(round(mass) or 1.0, mass)
            supp_unit = str(round(res['supplementary_units'])).zfill(10) if res['supplementary_units'] else '0000000000'

            # In the case of the value:
            # If the invoice value does not reconcile with the actual value of the goods, deviating
            # provisions apply. This applies, for instance, in the event of free delivery...
            # [...]
            # The actual value of the goods must be given
            value = line.price_subtotal or line.product_id.lst_price
            transaction_period = str(inv.invoice_date.year) + str(inv.invoice_date.month).rjust(2, '0')
            file_content += ''.join([
                transaction_period,                                             # Transaction period    length=6
                '6' if res['type'] == 'Arrival' else '7',                       # Commodity flow        length=1
                vat and vat[2:].replace(' ', '').ljust(12) or ''.ljust(12),     # VAT number            length=12
                str(i).zfill(5),                                                # Line number           length=5
                country_origin_code.ljust(3),                                   # Country of origin     length=3
                country.ljust(3),                                               # Count. of cons./dest. length=3
                res['transport_code'] or '3',                                   # Mode of transport     length=1
                '0',                                                            # Container             length=1
                '00',                                                           # Traffic region/port   length=2
                '00',                                                           # Statistical procedure length=2
                ' ' if new_codes else str(res['transaction_code']) or '1',      # Transaction (old)     length=1
                (res['commodity_code'] or '')[:8].ljust(8),                     # Commodity code        length=8
                '00',                                                           # Taric                 length=2
                mass >= 0 and '+' or '-',                                       # Mass sign             length=1
                str(int(abs(mass))).zfill(10),                                  # Mass                  length=10
                '+',                                                            # Supplementary sign    length=1
                inv.move_type in ['in_invoice', 'out_invoice'] and '+' or '-',  # Invoice sign          length=1
                supp_unit,                                                      # Supplementary unit    length=10
                str(int(value)).zfill(10),                                      # Invoice value         length=10
                '+',                                                            # Statistical sign      length=1
                '0000000000',                                                   # Statistical value     length=10
                (inv.name or '')[-10:].ljust(10),                               # Administration number length=10
                ''.ljust(3),                                                    # Reserve               length=3
                ' ',                                                            # Correction items      length=1
                '000',                                                          # Preference            length=3
                ''.ljust(7),                                                    # Reserve               length=7
                str(res['transaction_code']) or '11' if new_codes else '',      # Transaction (new)     length=2
                (res.get('partner_vat') or 'QV999999999999').ljust(17) if \
                new_codes else '',                                              # PartnerID (VAT No.)   length=17
            ]) + '\n'
            i += 1

        # FOOTER LINE
        file_content += ''.join([
            '9899',                                                             # Record type           length=4
            ''.ljust(111)                                                       # Reserve               length=111
        ])
        return {
            'file_name': self.env['account.report'].browse(options['report_id']).get_default_report_filename(options, 'csv'),
            'file_content': file_content,
            'file_type': 'csv',
        }
