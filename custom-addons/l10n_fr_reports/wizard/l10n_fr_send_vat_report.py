# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.tools import cleanup_xml_node, float_repr
from odoo.exceptions import ValidationError
from odoo.addons.l10n_fr_reports.models.account_report_async_export import ENDPOINT

from lxml import etree
from stdnum.fr import siret

CODE_TO_EDI_ID = {
    'box_A1': 'CA',
    'box_A2': 'CB',
    'box_A3': 'KH',
    'box_A4': 'DK',
    'box_A5': 'KV',
    'box_B1': 'CH',
    'box_B2': 'CC',
    'box_B3': 'CF',
    'box_B4': 'CG',
    'box_B5': 'CE',
    'box_E1': 'DA',
    'box_E2': 'DB',
    'box_E3': 'DH',
    'box_E4': 'KW',
    'box_E5': 'KX',
    'box_E6': 'KY',
    'box_F1': 'KZ',
    'box_F2': 'DC',
    'box_F3': 'DF',
    'box_F4': 'DJ',
    'box_F5': 'LA',
    'box_F6': 'DD',
    'box_F7': 'DG',
    'box_F8': 'DE',
    'box_F9': 'LR',
    'box_08_base': 'FP',
    'box_08_taxe': 'GP',
    'box_09_base': 'FB',
    'box_09_taxe': 'GB',
    'box_9B_base': 'FR',
    'box_9B_taxe': 'GR',
    'box_10_base': 'FM',
    'box_10_taxe': 'GM',
    'box_11_base': 'FN',
    'box_11_taxe': 'GN',
    'box_T1_base': 'BQ',
    'box_T1_taxe': 'CQ',
    'box_T2_base': 'BP',
    'box_T2_taxe': 'CP',
    'box_T3_base': 'BS',
    'box_T3_taxe': 'CS',
    'box_T4_base': 'BF',
    'box_T4_taxe': 'MC',
    'box_T5_base': 'BE',
    'box_T5_taxe': 'MA',
    'box_T6_base': 'MF',
    'box_T6_taxe': 'ME',
    'box_T7_base': 'MG',
    'box_T7_taxe': 'MD',
    'box_13_base': 'FC',
    'box_13_taxe': 'GC',
    'box_P1_base': 'GS',
    'box_P1_taxe': 'GT',
    'box_P2_base': 'GU',
    'box_P2_taxe': 'GV',
    'box_I1_base': 'LB',
    'box_I1_taxe': 'LC',
    'box_I2_base': 'LD',
    'box_I2_taxe': 'LE',
    'box_I3_base': 'LF',
    'box_I3_taxe': 'LG',
    'box_I4_base': 'LH',
    'box_I4_taxe': 'LJ',
    'box_I5_base': 'LK',
    'box_I5_taxe': 'LL',
    'box_I6_base': 'LM',
    'box_I6_taxe': 'LN',
    'box_15': 'GG',
    'box_15_1': 'GA',
    'box_15_2': 'LQ',
    'box_5B': 'KS',
    'box_16': 'GH',
    'box_17': 'GJ',
    'box_18': 'GK',
    'box_19': 'HA',
    'box_20': 'HB',
    'box_21': 'HC',
    'box_22': 'HD',
    'box_2C': 'KU',
    'box_22A': 'HE',
    'box_23': 'HG',
    'box_24': 'HF',
    'box_2E': 'HL',
    'box_25': 'JA',
    'box_TD': 'KA',
    'box_26': 'JB',
    'box_AA': 'KJ',
    'box_27': 'JC',
    'box_Y5': 'MT',
    'box_Y6': 'MH',
    'box_X5': 'MN',
    'box_28': 'ND',
    'box_29': 'KB',
    'box_Z5': 'NC',
    'box_AB': 'KL',
    'box_32': 'KE',
}


class L10nFrSendVatReport(models.TransientModel):
    _name = "l10n_fr_reports.send.vat.report"
    _description = "Send VAT Report Wizard"

    recipient = fields.Selection([
        ("DGI_EDI_TVA", "DGFiP"),
        ("CEC_EDI_TVA", "Expert Accountant"),
        ("OGA_EDI_TVA", "OGA"),
    ], default="DGI_EDI_TVA", required=True)
    test_interchange = fields.Boolean("Test Interchange")

    def _get_address_dict(self, company):
        return {
            'street': company.street,
            'complement': company.street2,
            'postal_code': company.zip,
            'city': company.city,
            'country_code': company.country_id.code,
        }

    def _check_constraints(self, model, list_fields):
        error_list = []
        for field in list_fields:
            if not model[field]:
                error_list.append(_("%s is required on %s", model._fields[field].string, model.display_name))
        if error_list:
            raise ValidationError(", ".join(error_list))

    def _check_siret(self, company):
        if not siret.is_valid(company.siret):
            raise ValidationError(_("%s has an invalid siret: %s.", company.display_name, company.siret))

    def _prepare_edi_vals(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        dt_from = fields.Date.to_date(options['date']['date_from'])
        dt_from, dt_to = self.env.company._get_tax_closing_period_boundaries(dt_from)
        options = report.get_options(
            {'no_format': True, 'date': {'date_from': dt_from, 'date_to': dt_to}, 'filter_unfold_all': True})
        lines = report._get_lines(options)

        # Check constraints
        sender_company = report._get_sender_company_for_export(options)
        # Assume Emitor = Writer -> omit the emitor
        writer = sender_company.account_representative_id or sender_company
        self._check_constraints(writer, ['siret', 'street', 'zip', 'city', 'country_id'])
        self._check_siret(writer)
        # Debtor
        debtor = sender_company
        self._check_constraints(debtor, ['siret', 'street', 'zip', 'city', 'country_id'])
        self._check_siret(debtor)

        # Use mapping to populate the xml
        form_vals = []
        currency = self.env.company.currency_id
        # Specific Lines (not filled if 0):
        # * 22A: the tax coefficient and cannot be 0
        # * P1 and P2: petroleum lines and should be sent only for companies with specific tax regimes
        # * F9: should be in the xml only for vat units
        # * A4, I1, I2, I3, I4, I5: some companies do not have the option to declare VAT import
        specific_lines = [
            'box_A4', 'box_F9', 'box_I1_base', 'box_I2_base', 'box_I3_base', 'box_I4_base', 'box_I5_base',
            'box_I6_base', 'box_22A', 'box_P1_base', 'box_P1_taxe', 'box_P2_base', 'box_P2_taxe',
        ]
        for line in lines:
            model, res_id = report._get_model_info_from_id(line['id'])
            if model == 'account.report.line':
                report_line = self.env[model].browse(res_id)
                if CODE_TO_EDI_ID.get(report_line.code):
                    col = next(filter(lambda c: c['expression_label'] == 'balance', line['columns']))
                    val = col['no_format'] or 0
                    if report_line.code in specific_lines and currency.is_zero(val):
                        continue
                    form_vals.append({
                        'id': CODE_TO_EDI_ID[report_line.code],
                        'value': float_repr(currency.round(val), currency.decimal_places).replace('.', ','),
                    })
        if not form_vals:
            raise ValidationError(_("The tax report is empty."))

        writer_vals = {
            'siret': writer.siret,
            'designation': "CEC_EDI_TVA",
            'designation_cont_1': writer.name,  # "raison sociale"
            'address': self._get_address_dict(writer),
        }
        debtor_vals = {
            'identifier': debtor.siret and debtor.siret[:9],  # siren
            'designation': debtor.name,  # "raison sociale"
            'address': self._get_address_dict(debtor),
            'rof': "TVA1",  # "référence obligation fiscale"
        }
        # EDI partner
        aspone_vals = {
            'identifier': "9210007",
            'designation': "ASP-ONE.FR",
            'address': {'number': 56, 'street': "RUE DE BILLANCOURT", 'postal_code': 92100,
                        'city': "BOULOGNE-BILLANCOURT", 'country_code': "FR"},
            'reference': "DEC00001",
        }
        # T-IDENTIF
        identif_vals = [
            {
                'id': 'AA',
                'identifier': debtor.siret and debtor.siret[:9],
                'designation': debtor.display_name,
                'address': self._get_address_dict(debtor),
            },
            {'id': 'KD', 'value': 'TVA1'},  # ROF
            {'id': 'CA', 'value': dt_from.strftime("%Y%m%d")},  # declaration period: yyyymmdd
            {'id': 'CB', 'value': dt_to.strftime("%Y%m%d")},
            {'id': 'GA', 'iban': None, 'bic': None},  # payment info
            {'id': 'HA', 'value': None},  # amount of payment
            {'id': 'KA', 'value': None},  # payment reference
        ]

        return {
            'date_from': dt_from,
            'date_to': dt_to,
            'is_test': '1' if self.test_interchange else '0',
            'type': "INFENT",  # constant
            'declarations': [{
                'type': "IDT",  # depends on the procedure
                'reference': "INFENT000042",  # internal reference to the emitor
                'writer': writer_vals,
                'debtor': debtor_vals,
                'edi_partner': aspone_vals,
                'recipients': [{'designation': self.recipient}],
                # T-IDENTIF form
                'identif': {
                    'millesime': "23",
                    'zones': identif_vals,
                },
                # 3310CA3
                'form': {
                    'millesime': "23",
                    'name': "3310CA3",
                    'zones': form_vals,
                }
            }],
        }

    def send_vat_return(self):
        self.ensure_one()

        # Generate xml
        options = self.env.context.get('l10n_fr_generation_options')
        vals = self._prepare_edi_vals(options)
        xml_content = self.env['ir.qweb']._render('l10n_fr_reports.aspone_xml_edi', vals)
        try:
            xml_content.encode('ISO-8859-15')
        except UnicodeEncodeError as e:
            raise ValidationError(
                _("The xml file generated contains an invalid character: '%s'", xml_content[e.start:e.end]))

        xml_content = etree.tostring(cleanup_xml_node(xml_content), encoding='ISO-8859-15', standalone='yes')

        # Send xml to ASPOne
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        response = self.env['account.report.async.export']._get_fr_webservice_answer(
            url=ENDPOINT + "/api/l10n_fr_aspone/1/add_document",
            params={'db_uuid': db_uuid, 'xml_content': xml_content.decode('iso8859_15')},
        )

        deposit_uid = ''
        if response['responseType'] == 'SUCCESS':
            if not response['response']['errorResponse']:
                deposit_uid = response['response']['successfullResponse']['depositId']

        if not deposit_uid:
            raise ValidationError(_("Error occured while sending the report to the government : '%s'", str(response)))

        # Create the attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'vat_report.xml',
            'res_model': 'l10n_fr_reports.report',
            'type': 'binary',
            # IAP might force the "Test" flag to 1 if the config parameter 'l10n_fr_aspone_proxy.test_env' is True
            'raw': response['xml_content'].encode(),
            'mimetype': 'application/xml',
        })

        if vals['date_from'].month != vals['date_to'].month:
            name = f"Report_{vals['date_from'].month:02d}-{vals['date_to'].month:02d}/{vals['date_from'].year}"
        else:
            name = f"Report_{vals['date_from'].month:02d}/{vals['date_from'].year}"

        # Create the vat return
        self.env['account.report.async.export'].create({
            'name': name,
            'attachment_ids': attachment.ids,
            'deposit_uid': deposit_uid,
            'date_from': vals['date_from'],
            'date_to': vals['date_to'],
            'report_id': self.env.ref('l10n_fr.tax_report').id,
            'recipient': self.recipient,
            'state': 'sent',
        })
