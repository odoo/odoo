import json
from base64 import b64decode, b64encode
from datetime import datetime
from urllib.parse import urljoin

import requests
from lxml import etree
from markupsafe import Markup
from requests.exceptions import HTTPError, RequestException

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import file_open

ZATCA_API_URLS = {
    "sandbox": "https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/",
    "preprod": "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/",
    "prod": "https://gw-fatoora.zatca.gov.sa/e-invoicing/core/",
    "apis": {
        "ccsid": "compliance",
        "pcsid": "production/csids",
        "compliance": "compliance/invoices",
        "reporting": "invoices/reporting/single",
        "clearance": "invoices/clearance/single",
    }
}

# This SANDBOX_AUTH is only used for testing purposes, and is shared to all users of the sandbox environment
SANDBOX_AUTH = {
    'binarySecurityToken': "TUlJRDFEQ0NBM21nQXdJQkFnSVRid0FBZTNVQVlWVTM0SS8rNVFBQkFBQjdkVEFLQmdncWhrak9QUVFEQWpCak1SVXdFd1lLQ1pJbWlaUHlMR1FCR1JZRmJHOWpZV3d4RXpBUkJnb0praWFKay9Jc1pBRVpGZ05uYjNZeEZ6QVZCZ29Ka2lhSmsvSXNaQUVaRmdkbGVIUm5ZWHAwTVJ3d0dnWURWUVFERXhOVVUxcEZTVTVXVDBsRFJTMVRkV0pEUVMweE1CNFhEVEl5TURZeE1qRTNOREExTWxvWERUSTBNRFl4TVRFM05EQTFNbG93U1RFTE1Ba0dBMVVFQmhNQ1UwRXhEakFNQmdOVkJBb1RCV0ZuYVd4bE1SWXdGQVlEVlFRTEV3MW9ZWGxoSUhsaFoyaHRiM1Z5TVJJd0VBWURWUVFERXdreE1qY3VNQzR3TGpFd1ZqQVFCZ2NxaGtqT1BRSUJCZ1VyZ1FRQUNnTkNBQVRUQUs5bHJUVmtvOXJrcTZaWWNjOUhEUlpQNGI5UzR6QTRLbTdZWEorc25UVmhMa3pVMEhzbVNYOVVuOGpEaFJUT0hES2FmdDhDL3V1VVk5MzR2dU1ObzRJQ0p6Q0NBaU13Z1lnR0ExVWRFUVNCZ0RCK3BId3dlakViTUJrR0ExVUVCQXdTTVMxb1lYbGhmREl0TWpNMGZETXRNVEV5TVI4d0hRWUtDWkltaVpQeUxHUUJBUXdQTXpBd01EYzFOVGc0TnpBd01EQXpNUTB3Q3dZRFZRUU1EQVF4TVRBd01SRXdEd1lEVlFRYURBaGFZWFJqWVNBeE1qRVlNQllHQTFVRUR3d1BSbTl2WkNCQ2RYTnphVzVsYzNNek1CMEdBMVVkRGdRV0JCU2dtSVdENmJQZmJiS2ttVHdPSlJYdkliSDlIakFmQmdOVkhTTUVHREFXZ0JSMllJejdCcUNzWjFjMW5jK2FyS2NybVRXMUx6Qk9CZ05WSFI4RVJ6QkZNRU9nUWFBL2hqMW9kSFJ3T2k4dmRITjBZM0pzTG5waGRHTmhMbWR2ZGk1ellTOURaWEowUlc1eWIyeHNMMVJUV2tWSlRsWlBTVU5GTFZOMVlrTkJMVEV1WTNKc01JR3RCZ2dyQmdFRkJRY0JBUVNCb0RDQm5UQnVCZ2dyQmdFRkJRY3dBWVppYUhSMGNEb3ZMM1J6ZEdOeWJDNTZZWFJqWVM1bmIzWXVjMkV2UTJWeWRFVnVjbTlzYkM5VVUxcEZhVzUyYjJsalpWTkRRVEV1WlhoMFoyRjZkQzVuYjNZdWJHOWpZV3hmVkZOYVJVbE9WazlKUTBVdFUzVmlRMEV0TVNneEtTNWpjblF3S3dZSUt3WUJCUVVITUFHR0gyaDBkSEE2THk5MGMzUmpjbXd1ZW1GMFkyRXVaMjkyTG5OaEwyOWpjM0F3RGdZRFZSMFBBUUgvQkFRREFnZUFNQjBHQTFVZEpRUVdNQlFHQ0NzR0FRVUZCd01DQmdnckJnRUZCUWNEQXpBbkJna3JCZ0VFQVlJM0ZRb0VHakFZTUFvR0NDc0dBUVVGQndNQ01Bb0dDQ3NHQVFVRkJ3TURNQW9HQ0NxR1NNNDlCQU1DQTBrQU1FWUNJUUNWd0RNY3E2UE8rTWNtc0JYVXovdjFHZGhHcDdycVNhMkF4VEtTdjgzOElBSWhBT0JOREJ0OSszRFNsaWpvVmZ4enJkRGg1MjhXQzM3c21FZG9HV1ZyU3BHMQ==",
    'secret': "Xlj15LyMCgSC66ObnEO/qVPfhSbs3kDTjWnGheYhfSs="
}


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    """
        In order to clear/report an invoice through the ZATCA API, we need to onboard each journal by following
        three steps:

            STEP 1:
                Make a call to the Compliance CSID API '/compliance'.
                This will return three things:
                    -   X509 Compliance Cryptographic Stamp Identifier (CCSID/Certificate)
                    -   Password (Secret)
                    -   Compliance Request ID
            STEP 2:
                Make a call to the Compliance Checks API '/compliance/invoices', by passing the hashed xml content
                of the files available in the tests/compliance folder. This will check if the provided
                Standard/Simplified Invoices comply with UBL 2.1 standards in line with ZATCA specifications
            STEP 3:
                Make a call to the Production CSID API '/production/csids' including the Compliance Certificate,
                Password and Request ID from STEP 1.
                This will return three things:
                    -   X509 Production Certificate
                    -   Password (Secret)
                    -   Production Request ID
    """

    l10n_sa_csr = fields.Binary(attachment=True, copy=False, groups="base.group_system",
                                help="The Certificate Signing Request that is submitted to the Compliance API")
    l10n_sa_csr_errors = fields.Html("Onboarding Errors", copy=False)

    l10n_sa_compliance_csid_json = fields.Char("CCSID JSON", copy=False, groups="base.group_system",
                                               help="Compliance CSID data received from the Compliance CSID API "
                                                    "in dumped json format")
    l10n_sa_production_csid_certificate_id = fields.Many2one(string="PCSID Certificate", comodel_name="certificate.certificate",
                                                          domain=[('is_valid', '=', True)])
    l10n_sa_production_csid_json = fields.Char("PCSID JSON", copy=False, groups="base.group_system",
                                               help="Production CSID data received from the Production CSID API "
                                                    "in dumped json format")
    l10n_sa_production_csid_validity = fields.Datetime(related="l10n_sa_production_csid_certificate_id.date_end")
    l10n_sa_compliance_csid_certificate_id = fields.Many2one(string="CCSID certificate", comodel_name="certificate.certificate",
                                                          domain=[('is_valid', '=', True)])
    l10n_sa_compliance_checks_passed = fields.Boolean("Compliance Checks Done", default=False, copy=False,
                                                      help="Specifies if the Compliance Checks have been completed successfully")

    l10n_sa_chain_sequence_id = fields.Many2one('ir.sequence', string='ZATCA account.move chain sequence',
                                                readonly=True, copy=False)

    l10n_sa_serial_number = fields.Char("Serial Number", copy=False,
                                        help="The serial number of the Taxpayer solution unit. Provided by ZATCA")

    l10n_sa_latest_submission_hash = fields.Char("Latest Submission Hash", copy=False,
                                                 help="Hash of the latest submitted invoice to be used as the Previous Invoice Hash (KSA-13)")

    # ====== Utility Functions =======

    def _l10n_sa_ready_to_submit_einvoices(self):
        """
            Helper function to know if the required CSIDs have been obtained, and the compliance checks have been
            completed
        """
        self.ensure_one()
        return self.sudo().l10n_sa_production_csid_json

    def _l10n_sa_api_onboard_sanity_checks(self):
        """
            Perform a sanity check to validate that the journal is ready to be onboarded
        """

        # If the invoice wasn't sent to ZATCA because of a timeout, it will retain its existing chain index
        # Make sure there are no opened invoices with the journal's existing sequence
        move_ids = self.env['account.move'].search(
            [
                ('journal_id', '=', self.id),
                ('l10n_sa_chain_index', '!=', 0)
            ]
        )
        stuck_moves = [move for move in move_ids if not move._l10n_sa_is_in_chain()]
        if stuck_moves:
            raise UserError(_("Oops! The journal is stuck. Please submit the pending invoices to ZATCA and try again."))
    # ====== CSR Generation =======

    def _l10n_sa_csr_required_fields(self):
        """ Return the list of fields required to generate a valid CSR as per ZATCA requirements """
        return ['l10n_sa_private_key_id', 'vat', 'name', 'city', 'country_id', 'state_id']

    def _l10n_sa_generate_csr(self):
        """
            Generate a CSR for the Journal to be used for the Onboarding process and Invoice submissions
        """
        self.ensure_one()
        if any(not self.company_id[f] for f in self._l10n_sa_csr_required_fields()):
            raise UserError(
                _(
                    "Please, make sure all the following fields have been correctly set on the Company:%(fields)s",
                    fields="".join(
                        "\n - %s" % self.company_id._fields[f].string
                        for f in self._l10n_sa_csr_required_fields()
                        if not self.company_id[f]
                    ),
                ),
            )
        self._l10n_sa_reset_certificates()
        self.l10n_sa_csr = self.env['certificate.certificate'].sudo()._l10n_sa_get_csr_str(self)

    # ====== Certificate Methods =======

    def _l10n_sa_reset_certificates(self):
        """
            Reset all certificate values, including CSR and compliance checks
        """
        for journal in self.sudo():
            journal.l10n_sa_csr = False
            journal.l10n_sa_production_csid_json = False
            journal.l10n_sa_compliance_csid_json = False
            journal.l10n_sa_compliance_checks_passed = False

    def _l10n_sa_api_onboard_journal(self, otp):
        """
            Perform the onboarding for the journal. The onboarding consists of three steps:
                1.  Get the Compliance CSID
                2.  Perform the Compliance Checks
                3.  Get the Production CSID
        """
        self.ensure_one()
        # we want to perform sanity checks to ensure that the journal is ready to be onboarded
        # If the check fails, we do not want to revoke the existing PCSID because the user might still need it to post hanging invoices
        self._l10n_sa_api_onboard_sanity_checks()

        try:
            # If the company does not have a private key, we generate it.
            # The private key is used to generate the CSR but also to sign the invoices
            ec_private_key_sudo = self.company_id.sudo().l10n_sa_private_key_id
            if not ec_private_key_sudo:
                ec_private_key_sudo = self.env['certificate.key'].sudo()._generate_ec_private_key(self.company_id, name='CCSID private key')
                self.company_id.l10n_sa_private_key_id = ec_private_key_sudo
            self._l10n_sa_generate_csr()
            # STEP 1: The first step of the process is to get the CCSID
            self._l10n_sa_get_compliance_CSID(otp)
            # STEP 2: Once we have the CCSID, we preform the compliance checks
            self._l10n_sa_run_compliance_checks()
            # STEP 3: Once the compliance checks are completed, we request the PCSID
            self._l10n_sa_get_production_CSID()
            # Once all three steps are completed, we set the errors field to False
            self.l10n_sa_csr_errors = False
            # Regenerate a new chain sequence
            self._l10n_sa_edi_icv_onboarding()
        except (RequestException, HTTPError, UserError) as e:
            # In case of an exception returned from ZATCA (not timeout), we will need to regenerate the CSR
            # As the same CSR cannot be used twice for the same CCSID request
            self._l10n_sa_reset_certificates()
            self.l10n_sa_csr_errors = e.args[0] or _("Journal could not be onboarded")

    def _l10n_sa_get_compliance_CSID(self, otp):
        """
            Request a Compliance Cryptographic Stamp Identifier (CCSID) from ZATCA
        """
        CCSID_data = self._l10n_sa_api_get_compliance_CSID(otp)
        if CCSID_data.get('errors') or CCSID_data.get('error'):
            raise UserError(_("Could not obtain Compliance CSID: %s",
                              CCSID_data['errors'][0]['message'] if CCSID_data.get('errors') else CCSID_data['error']))
        cert_id = self.env['certificate.certificate'].sudo().create({
            'name': 'CCSID Certificate',
            'content': b64decode(CCSID_data['binarySecurityToken']),
            'private_key_id': self.company_id.sudo().l10n_sa_private_key_id.id,
        }).id
        self.sudo().write({
            'l10n_sa_compliance_csid_json': json.dumps(CCSID_data),
            'l10n_sa_compliance_csid_certificate_id': cert_id,
            'l10n_sa_production_csid_json': False,
            'l10n_sa_compliance_checks_passed': False,
        })

    def _l10n_sa_get_production_CSID(self, OTP=None):
        """
            Request a Production Cryptographic Stamp Identifier (PCSID) from ZATCA
        """

        self_sudo = self.sudo()

        if not self_sudo.l10n_sa_compliance_csid_json or not self_sudo.l10n_sa_compliance_csid_certificate_id:
            raise UserError(_("Cannot request a Production CSID before requesting a CCSID first"))
        elif not self_sudo.l10n_sa_compliance_checks_passed:
            raise UserError(_("Cannot request a Production CSID before completing the Compliance Checks"))

        renew = False
        zatca_format = self.env.ref('l10n_sa_edi.edi_sa_zatca')

        if self_sudo.l10n_sa_production_csid_json:
            time_now = zatca_format._l10n_sa_get_zatca_datetime(datetime.now())
            if zatca_format._l10n_sa_get_zatca_datetime(self_sudo.l10n_sa_production_csid_validity) < time_now:
                renew = True
            else:
                raise UserError(_("The Production CSID is still valid. You can only renew it once it has expired."))

        CCSID_data = json.loads(self_sudo.l10n_sa_compliance_csid_json)
        PCSID_data = self_sudo._l10n_sa_request_production_csid(CCSID_data, renew, OTP)
        if PCSID_data.get('error'):
            raise UserError(_("Could not obtain Production CSID: %s", PCSID_data['error']))
        self_sudo.l10n_sa_production_csid_json = json.dumps(PCSID_data)
        pcsid_certificate = self_sudo.env['certificate.certificate'].create({
            'name': 'PCSID Certificate',
            'content': b64decode(PCSID_data['binarySecurityToken']),
        })
        self.l10n_sa_production_csid_certificate_id = pcsid_certificate

    # ====== Compliance Checks =======

    def _l10n_sa_get_compliance_files(self):
        """
            Return the list of files to be used for the compliance checks.
        """
        file_names, compliance_files = [
            'standard/invoice.xml', 'standard/credit.xml', 'standard/debit.xml',
            'simplified/invoice.xml', 'simplified/credit.xml', 'simplified/debit.xml',
        ], {}
        for file in file_names:
            fpath = f'l10n_sa_edi/tests/compliance/{file}'
            with file_open(fpath, 'rb', filter_ext=('.xml',)) as ip:
                compliance_files[file] = ip.read().decode()
        return compliance_files

    def _l10n_sa_run_compliance_checks(self):
        """
            Run Compliance Checks once the CCSID has been obtained.

            The goal of the Compliance Checks is to make sure our system is able to produce, sign and send Invoices
            correctly. For this we use dummy invoice UBL files available under the tests/compliance folder:

            Standard Invoice, Standard Credit Note, Standard Debit Note, Simplified Invoice, Simplified Credit Note,
            Simplified Debit Note.

            We read each one of these files separately, sign them, then process them through the Compliance Checks API.
        """

        self.ensure_one()
        self_sudo = self.sudo()
        if self.country_code != 'SA':
            raise UserError(_("Compliance checks can only be run for companies operating from KSA"))
        if not self_sudo.l10n_sa_compliance_csid_json or not self_sudo.l10n_sa_compliance_csid_certificate_id:
            raise UserError(_("You need to request the CCSID first before you can proceed"))
        CCSID_data = json.loads(self_sudo.l10n_sa_compliance_csid_json)
        compliance_files = self._l10n_sa_get_compliance_files()
        for fname, fval in compliance_files.items():
            invoice_hash_hex = self.env['account.edi.xml.ubl_21.zatca']._l10n_sa_generate_invoice_xml_hash(
                fval).decode()
            digital_signature = self.env.ref('l10n_sa_edi.edi_sa_zatca')._l10n_sa_get_digital_signature(self.company_id, invoice_hash_hex).decode()
            prepared_xml = self._l10n_sa_prepare_compliance_xml(fname, fval, self_sudo.l10n_sa_compliance_csid_certificate_id, digital_signature)
            result = self._l10n_sa_api_compliance_checks(prepared_xml.decode(), CCSID_data)
            if result.get('error'):
                raise UserError(Markup("<p class='mb-0'>%s <b>%s</b></p>") % (_("Could not complete Compliance Checks for the following file:"), fname))
            if result['validationResults']['status'] == 'WARNING':
                warnings = Markup().join(Markup("<li><b>%(code)s</b>: %(message)s </li>") % e for e in result['validationResults']['warningMessages'])
                self.l10n_sa_csr_errors = Markup("<br/><br/><ul class='pl-3'><b>%s</b>%s</ul>") % (_("Warnings:"), warnings)
            elif result['validationResults']['status'] != 'PASS':
                errors = Markup().join(Markup("<li><b>%(code)s</b>: %(message)s </li>") % e for e in result['validationResults']['errorMessages'])
                raise UserError(Markup("<p class='mb-0'>%s <b>%s</b> %s</p>")
                                % (_("Could not complete Compliance Checks for the following file:"), fname, Markup("<br/><br/><ul class='pl-3'><b>%s</b>%s</ul>") % (_("Errors:"), errors)))
        self.l10n_sa_compliance_checks_passed = True

    def _l10n_sa_prepare_compliance_xml(self, xml_name, xml_raw, certificate, signature):
        """
            Prepare XML content to be used for Compliance checks
        """
        xml_content = self._l10n_sa_prepare_invoice_xml(xml_raw)
        signed_xml = self.env.ref('l10n_sa_edi.edi_sa_zatca')._l10n_sa_sign_xml(xml_content, certificate, signature)
        if xml_name.startswith('simplified'):
            qr_code_str = self.env['account.move']._l10n_sa_get_qr_code(self, signed_xml, certificate, signature, True)
            root = etree.fromstring(signed_xml)
            qr_node = root.xpath('//*[local-name()="ID"][text()="QR"]/following-sibling::*/*')[0]
            qr_node.text = b64encode(qr_code_str).decode()
            return etree.tostring(root, with_tail=False)
        return signed_xml

    def _l10n_sa_prepare_invoice_xml(self, xml_content):
        """
            Prepare the XML content of the test invoices before running the compliance checks
        """
        ubl_extensions = etree.fromstring(self.env['ir.qweb']._render('l10n_sa_edi.export_sa_zatca_ubl_extensions'))
        root = etree.fromstring(xml_content.encode())
        root.insert(0, ubl_extensions)
        ns_map = self.env['account.edi.xml.ubl_21.zatca']._l10n_sa_get_namespaces()

        def _get_node(xpath_str):
            return root.xpath(xpath_str, namespaces=ns_map)[0]

        # Update the Company VAT number in the test invoice
        vat_el = _get_node('//cbc:CompanyID')
        vat_el.text = self.company_id.vat

        # Update the Company Name in the test invoice
        name_nodes = ['cac:PartyName/cbc:Name', 'cac:PartyLegalEntity/cbc:RegistrationName', 'cac:Contact/cbc:Name']
        for node in name_nodes:
            comp_name_el = _get_node('//cac:AccountingSupplierParty/cac:Party/' + node)
            comp_name_el.text = self.company_id.display_name

        return etree.tostring(root)

    # ====== Index Chain & Previous Invoice Calculation =======
    def _l10n_sa_edi_icv_onboarding(self):
        """
            Onboarding method to create or reset ICV sequence for the journal
        """
        self.ensure_one()
        if self.l10n_sa_chain_sequence_id:
            self.l10n_sa_chain_sequence_id.number_next = 1
            message = _("Journal re-onboarded with ZATCA successfully")
        else:
            self.l10n_sa_chain_sequence_id = self._l10n_sa_edi_create_new_chain()
            message = _("Journal onboarded with ZATCA successfully")
        self.message_post(body=message)

    def _l10n_sa_edi_create_new_chain(self):
        self.ensure_one()
        return self.env['ir.sequence'].create({
            'name': f'ZATCA account move sequence for Journal {self.name} (id: {self.id})',
            'code': f'l10n_sa_edi.account.move.{self.id}',
            'implementation': 'no_gap',
            'company_id': self.company_id.id,
        })

    def _l10n_sa_edi_get_next_chain_index(self):
        self.ensure_one()
        if not self.l10n_sa_chain_sequence_id:
            self.l10n_sa_chain_sequence_id = self._l10n_sa_edi_create_new_chain()
        return self.l10n_sa_chain_sequence_id.next_by_id()

    def _l10n_sa_get_last_posted_invoice(self):
        """
        Returns the last invoice posted to this journal's chain.
        That invoice may have been received by the govt or not (eg. in case of a timeout).
        Only upon confirmed reception/refusal of that invoice can another one be posted.
        """
        self.ensure_one()
        return self.env['account.move'].search(
            [
                ('journal_id', '=', self.id),
                ('l10n_sa_chain_index', '!=', 0)
            ],
            limit=1, order='l10n_sa_chain_index desc'
        )

    # ====== API Calls to ZATCA =======

    def _l10n_sa_api_get_compliance_CSID(self, otp):
        """
            API call to the Compliance CSID API to generate a CCSID certificate, password and compliance request_id
            Requires a CSR token and a One Time Password (OTP)
        """
        self.ensure_one()
        if not otp:
            raise UserError(_("Please, set a valid OTP to be used for Onboarding"))
        if not self.l10n_sa_csr:
            raise UserError(_("Please, generate a CSR before requesting a CCSID"))
        request_data = {
            'body': json.dumps({'csr': self.l10n_sa_csr.decode()}),
            'header': {'OTP': otp}
        }
        return self._l10n_sa_call_api(request_data, ZATCA_API_URLS['apis']['ccsid'], 'POST')

    def _l10n_sa_api_get_production_CSID(self, CCSID_data):
        """
            API call to the Production CSID API to generate a PCSID certificate, password and production request_id
            Requires a requestID from the Compliance CSID API
        """
        request_data = {
            'body': json.dumps({'compliance_request_id': str(CCSID_data['requestID'])}),
            'header': {'Authorization': self._l10n_sa_authorization_header(CCSID_data)}
        }
        return self._l10n_sa_call_api(request_data, ZATCA_API_URLS['apis']['pcsid'], 'POST')

    def _l10n_sa_api_renew_production_CSID(self, PCSID_data, OTP):
        """
            API call to the Production CSID API to renew a PCSID certificate, password and production request_id
            Requires an expired Production CSIDPCSID_data
        """
        self.ensure_one()
        auth_data = PCSID_data
        # For renewal, the sandbox API expects a specific Username/Password, which are set in the SANDBOX_AUTH dict
        if self.company_id.l10n_sa_api_mode == 'sandbox':
            auth_data = SANDBOX_AUTH
        request_data = {
            'body': json.dumps({'csr': self.l10n_sa_csr.decode()}),
            'header': {
                'OTP': OTP,
                'Authorization': self._l10n_sa_authorization_header(auth_data)
            }
        }
        return self._l10n_sa_call_api(request_data, ZATCA_API_URLS['apis']['pcsid'], 'PATCH')

    def _l10n_sa_api_compliance_checks(self, xml_content, CCSID_data):
        """
            API call to the COMPLIANCE endpoint to generate a security token used for subsequent API calls
            Requires a CSR token and a One Time Password (OTP)
        """
        invoice_tree = etree.fromstring(xml_content)

        # Get the Invoice Hash from the XML document
        invoice_hash_node = invoice_tree.xpath('//*[@Id="invoiceSignedData"]/*[local-name()="DigestValue"]')[0]
        invoice_hash = invoice_hash_node.text

        # Get the Invoice UUID from the XML document
        invoice_uuid_node = invoice_tree.xpath('//*[local-name()="UUID"]')[0]
        invoice_uuid = invoice_uuid_node.text

        request_data = {
            'body': json.dumps({
                "invoiceHash": invoice_hash,
                "uuid": invoice_uuid,
                "invoice": b64encode(xml_content.encode()).decode()
            }),
            'header': {
                'Authorization': self._l10n_sa_authorization_header(CCSID_data),
                'Clearance-Status': '1'
            }
        }
        return self._l10n_sa_call_api(request_data, ZATCA_API_URLS['apis']['compliance'], 'POST')

    def _l10n_sa_get_api_clearance_url(self, invoice):
        """
            Return the API to be used for clearance. To be overridden to account for other cases, such as reporting.
        """
        return ZATCA_API_URLS['apis']['reporting' if invoice._l10n_sa_is_simplified() else 'clearance']

    def _l10n_sa_api_clearance(self, invoice, xml_content, PCSID_data):
        """
            API call to the CLEARANCE/REPORTING endpoint to sign an invoice
                - If SIMPLIFIED invoice: Reporting
                - If STANDARD invoice: Clearance
        """
        invoice_tree = etree.fromstring(xml_content)
        invoice_hash_node = invoice_tree.xpath('//*[@Id="invoiceSignedData"]/*[local-name()="DigestValue"]')[0]
        invoice_hash = invoice_hash_node.text
        request_data = {
            'body': json.dumps({
                "invoiceHash": invoice_hash,
                "uuid": invoice.l10n_sa_uuid,
                "invoice": b64encode(xml_content.encode()).decode()
            }),
            'header': {
                'Authorization': self._l10n_sa_authorization_header(PCSID_data),
                'Clearance-Status': '1'
            }
        }
        url_string = self._l10n_sa_get_api_clearance_url(invoice)
        return self._l10n_sa_call_api(request_data, url_string, 'POST')

    # ====== Certificate Methods =======

    def _l10n_sa_request_production_csid(self, csid_data, renew=False, otp=None):
        """
            Generate company Production CSID data
        """
        self.ensure_one()
        return (
            self._l10n_sa_api_renew_production_CSID(csid_data, otp)
            if renew
            else self._l10n_sa_api_get_production_CSID(csid_data)
        )

    def _l10n_sa_api_get_pcsid(self):
        """
            Get CSIDs required to perform ZATCA api calls, and regenerate them if they need to be regenerated.
        """
        self.ensure_one()
        self_sudo = self.sudo()
        if not self_sudo.l10n_sa_production_csid_json or not self_sudo.l10n_sa_production_csid_certificate_id:
            raise UserError(_("Please, make a request to obtain the Compliance CSID and Production CSID before sending "
                            "documents to ZATCA"))
        certificate = self_sudo.l10n_sa_production_csid_certificate_id
        if not certificate.is_valid and self.company_id.l10n_sa_api_mode != 'sandbox':
            raise UserError(_("Production certificate has expired, please renew the PCSID before proceeding"))
        return json.loads(self_sudo.l10n_sa_production_csid_json), certificate.id

    # ====== API Helper Methods =======

    def _l10n_sa_call_api(self, request_data, request_url, method):
        """
            Helper function to make api calls to the ZATCA API Endpoint
        """
        api_url = ZATCA_API_URLS[self.company_id.l10n_sa_api_mode]
        request_url = urljoin(api_url, request_url)
        status_code = False
        try:
            request_response = requests.request(method, request_url, data=request_data.get('body'),
                                                headers={
                                                    **self._l10n_sa_api_headers(),
                                                    **request_data.get('header')
                                                }, timeout=(30, 30))
            request_response.raise_for_status()
        except (ValueError, HTTPError) as ex:
            # The 400 case means that it is rejected by ZATCA, but we need to update the hash as done for accepted.
            # In the 401+ cases, it is like the server is overloaded e.g. and we still need to resend later.  We do not
            # erase the index chain (excepted) because for ZATCA, one ICV (index chain) needs to correspond to one invoice.
            if (status_code := ex.response.status_code) != 400:
                return {
                    'error': (Markup("<b>[%s]</b>") % status_code) + _("Server returned an unexpected error: %(error)s",
                               error=(request_response.text or str(ex))),
                    'blocking_level': 'warning',
                    'status_code': status_code,
                    'excepted': True,
                }
        except RequestException as ex:
            # Usually only happens if a Timeout occurs. In this case we're not sure if the invoice was accepted or
            # rejected, or if it even made it to ZATCA
            return {'error': str(ex), 'blocking_level': 'warning', 'excepted': True}

        if request_response.status_code == '303':
            return {'error': _('Clearance and reporting seem to have been mixed up. '),
                    'blocking_level': 'warning', 'excepted': True}

        try:
            response_data = request_response.json()
        except json.decoder.JSONDecodeError:
            return {
                'error': _("JSON response from ZATCA could not be decoded"),
                'blocking_level': 'error'
            }
        response_data['status_code'] = request_response.status_code

        val_res = response_data.get('validationResults', {})
        if not request_response.ok and (val_res.get('errorMessages') or val_res.get('warningMessages')):
            error = "" if not status_code else Markup("<b>[%s]</b>") % (status_code)
            if isinstance(response_data, dict) and val_res.get('errorMessages'):
                error += _("Invoice submission to ZATCA returned errors")
                return {
                    'error': error,
                    'json_errors': response_data,
                    'blocking_level': 'error',
                }
            error += request_response.reason
            return {
                'error': error,
                'blocking_level': 'error',
            }
        return response_data

    def _l10n_sa_api_headers(self):
        """
            Return the base headers to be included in ZATCA API calls
        """
        return {
            'Content-Type': 'application/json',
            'Accept-Language': 'en',
            'Accept-Version': 'V2'
        }

    def _l10n_sa_authorization_header(self, CSID_data):
        """
            Compute the Authorization header by combining the CSID and the Secret key, then encode to Base64
        """
        auth_data = CSID_data
        auth_str = "%s:%s" % (auth_data['binarySecurityToken'], auth_data['secret'])
        return 'Basic ' + b64encode(auth_str.encode()).decode()

    def _l10n_sa_load_edi_demo_data(self):
        self.ensure_one()
        self.company_id.l10n_sa_private_key_id = self.env['certificate.key']._generate_ec_private_key(self.company_id)
        self.write({
            'l10n_sa_serial_number': 'SIDI3-CBMPR-L2D8X-KM0KN-X4ISJ',
            'l10n_sa_compliance_checks_passed': True,
            'l10n_sa_csr': b'LS0tLS1CRUdJTiBDRVJUSUZJQ0FURSBSRVFVRVNULS0tLS0KTUlJQ2NqQ0NBaGNDQVFBd2djRXhDekFKQmdOVkJBWVRBbE5CTVJNd0VRWURWUVFMREFvek1UQXhOelV6T1RjMApNUk13RVFZRFZRUUtEQXBUUVNCRGIyMXdZVzU1TVJNd0VRWURWUVFEREFwVFFTQkRiMjF3WVc1NU1SZ3dGZ1lEClZRUmhEQTh6TVRBeE56VXpPVGMwTURBd01ETXhEekFOQmdOVkJBZ01CbEpwZVdGa2FERklNRVlHQTFVRUJ3dy8KdzVqQ3A4T1o0b0NldzVuaWdLYkRtTUt2dzVuRm9NT1o0b0NndzVqQ3FTRERtTUtudzVuaWdKN0RtZUtBcHNPWgo0b0NndzVuTGhzT1l3ckhEbU1LcE1GWXdFQVlIS29aSXpqMENBUVlGSzRFRUFBb0RRZ0FFN2ZpZWZWQ21HcTlzCmV0OVl4aWdQNzZWUmJxZlh0VWNtTk1VN3FkTlBiSm5NNGh5R1QwanpPcXUrSWNXWW5IelFJYmxJVmsydENPQnQKYjExanY4MGVwcUNCOVRDQjhnWUpLb1pJaHZjTkFRa09NWUhrTUlIaE1DUUdDU3NHQVFRQmdqY1VBZ1FYRXhWUQpVa1ZhUVZSRFFTMURiMlJsTFZOcFoyNXBibWN3Z2JnR0ExVWRFUVNCc0RDQnJhU0JxakNCcHpFME1ESUdBMVVFCkJBd3JNUzFQWkc5dmZESXRNVFY4TXkxVFNVUkpNeTFEUWsxUVVpMU1Na1E0V0MxTFRUQkxUaTFZTkVsVFNqRWYKTUIwR0NnbVNKb21UOGl4a0FRRU1Eek14TURFM05UTTVOelF3TURBd016RU5NQXNHQTFVRURBd0VNVEV3TURFdgpNQzBHQTFVRUdnd21RV3dnUVcxcGNpQk5iMmhoYlcxbFpDQkNhVzRnUVdKa2RXd2dRWHBwZWlCVGRISmxaWFF4CkRqQU1CZ05WQkE4TUJVOTBhR1Z5TUFvR0NDcUdTTTQ5QkFNQ0Ewa0FNRVlDSVFEb3VCeXhZRDRuQ2pUQ2V6TkYKczV6SmlVWW1QZVBRNnFWNDdZemRHeWRla1FJaEFPRjNVTWF4UFZuc29zOTRFMlNkT2JJcTVYYVAvKzlFYWs5TgozMUtWRUkvTQotLS0tLUVORCBDRVJUSUZJQ0FURSBSRVFVRVNULS0tLS0K',
            'l10n_sa_compliance_csid_json': """{"requestID": 1234567890123, "dispositionMessage": "ISSUED", "binarySecurityToken": "TUlJQ2N6Q0NBaG1nQXdJQkFnSUdBWStWTmxza01Bb0dDQ3FHU000OUJBTUNNQlV4RXpBUkJnTlZCQU1NQ21WSmJuWnZhV05wYm1jd0hoY05NalF3TlRJd01EZzFOVEV6V2hjTk1qa3dOVEU1TWpFd01EQXdXakNCbnpFTE1Ba0dBMVVFQmhNQ1UwRXhFekFSQmdOVkJBc01Dak01T1RrNU9UazVPVGt4RXpBUkJnTlZCQW9NQ2xOQklFTnZiWEJoYm5reEV6QVJCZ05WQkFNTUNsTkJJRU52YlhCaGJua3hHREFXQmdOVkJHRU1Eek01T1RrNU9UazVPVGt3TURBd016RVBNQTBHQTFVRUNBd0dVbWw1WVdSb01TWXdKQVlEVlFRSERCM1lwOW1FMllYWXI5bUsyWWJZcVNEWXA5bUUyWVhaaHRtSTJMSFlxVEJXTUJBR0J5cUdTTTQ5QWdFR0JTdUJCQUFLQTBJQUJOVlB3N0hGNjhUVWtQTkJQb29uT0Y2NnRPMm5IcmxUNlRMcmk3MEpLY1MvYmVMWitoRVE0MmdXdUtYckp5RmxnWm9kUVJzTFQyMEtQZnE0Q3N2YlFJMmpnY3d3Z2Nrd0RBWURWUjBUQVFIL0JBSXdBRENCdUFZRFZSMFJCSUd3TUlHdHBJR3FNSUduTVRRd01nWURWUVFFRENzeExVOWtiMjk4TWkweE5Yd3pMVk5KUkVrekxVTkNUVkJTTFV3eVJEaFlMVXROTUV0T0xWZzBTVk5LTVI4d0hRWUtDWkltaVpQeUxHUUJBUXdQTXprNU9UazVPVGs1T1RBd01EQXpNUTB3Q3dZRFZRUU1EQVF4TVRBd01TOHdMUVlEVlFRYURDWkJiQ0JCYldseUlFMXZhR0Z0YldWa0lFSnBiaUJCWW1SMWJDQkJlbWw2SUZOMGNtVmxkREVPTUF3R0ExVUVEd3dGVDNSb1pYSXdDZ1lJS29aSXpqMEVBd0lEU0FBd1JRSWdTeVhlZExqOUtMVTRUMWFBbVQvL09GZDBGWWxLQnIraFFIeGNDM0c2ajc4Q0lRRGdlNjNsQkVqTU1ETktqTm1pTklaQlBWSnlHRzl5bVJaSHdvUzV5TEQyZXc9PQ==", "secret": "uMpSz85cV0h/e/uqpJ+FaZkdYZ76uoaRYOevGufcup0=", "errors": null}""",
            'l10n_sa_production_csid_json': """{"requestID": 30368, "tokenType": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3", "dispositionMessage": "ISSUED", "binarySecurityToken": "TUlJRDNqQ0NBNFNnQXdJQkFnSVRFUUFBT0FQRjkwQWpzL3hjWHdBQkFBQTRBekFLQmdncWhrak9QUVFEQWpCaU1SVXdFd1lLQ1pJbWlaUHlMR1FCR1JZRmJHOWpZV3d4RXpBUkJnb0praWFKay9Jc1pBRVpGZ05uYjNZeEZ6QVZCZ29Ka2lhSmsvSXNaQUVaRmdkbGVIUm5ZWHAwTVJzd0dRWURWUVFERXhKUVVscEZTVTVXVDBsRFJWTkRRVFF0UTBFd0hoY05NalF3TVRFeE1Ea3hPVE13V2hjTk1qa3dNVEE1TURreE9UTXdXakIxTVFzd0NRWURWUVFHRXdKVFFURW1NQ1FHQTFVRUNoTWRUV0Y0YVcxMWJTQlRjR1ZsWkNCVVpXTm9JRk4xY0hCc2VTQk1WRVF4RmpBVUJnTlZCQXNURFZKcGVXRmthQ0JDY21GdVkyZ3hKakFrQmdOVkJBTVRIVlJUVkMwNE9EWTBNekV4TkRVdE16azVPVGs1T1RrNU9UQXdNREF6TUZZd0VBWUhLb1pJemowQ0FRWUZLNEVFQUFvRFFnQUVvV0NLYTBTYTlGSUVyVE92MHVBa0MxVklLWHhVOW5QcHgydmxmNHloTWVqeThjMDJYSmJsRHE3dFB5ZG84bXEwYWhPTW1Obzhnd25pN1h0MUtUOVVlS09DQWdjd2dnSURNSUd0QmdOVkhSRUVnYVV3Z2FLa2daOHdnWnd4T3pBNUJnTlZCQVFNTWpFdFZGTlVmREl0VkZOVWZETXRaV1F5TW1ZeFpEZ3RaVFpoTWkweE1URTRMVGxpTlRndFpEbGhPR1l4TVdVME5EVm1NUjh3SFFZS0NaSW1pWlB5TEdRQkFRd1BNems1T1RrNU9UazVPVEF3TURBek1RMHdDd1lEVlFRTURBUXhNVEF3TVJFd0R3WURWUVFhREFoU1VsSkVNamt5T1RFYU1CZ0dBMVVFRHd3UlUzVndjR3g1SUdGamRHbDJhWFJwWlhNd0hRWURWUjBPQkJZRUZFWCtZdm1tdG5Zb0RmOUJHYktvN29jVEtZSzFNQjhHQTFVZEl3UVlNQmFBRkp2S3FxTHRtcXdza0lGelZ2cFAyUHhUKzlObk1Ic0dDQ3NHQVFVRkJ3RUJCRzh3YlRCckJnZ3JCZ0VGQlFjd0FvWmZhSFIwY0RvdkwyRnBZVFF1ZW1GMFkyRXVaMjkyTG5OaEwwTmxjblJGYm5KdmJHd3ZVRkphUlVsdWRtOXBZMlZUUTBFMExtVjRkR2RoZW5RdVoyOTJMbXh2WTJGc1gxQlNXa1ZKVGxaUFNVTkZVME5CTkMxRFFTZ3hLUzVqY25Rd0RnWURWUjBQQVFIL0JBUURBZ2VBTUR3R0NTc0dBUVFCZ2pjVkJ3UXZNQzBHSlNzR0FRUUJnamNWQ0lHR3FCMkUwUHNTaHUyZEpJZk8reG5Ud0ZWbWgvcWxaWVhaaEQ0Q0FXUUNBUkl3SFFZRFZSMGxCQll3RkFZSUt3WUJCUVVIQXdNR0NDc0dBUVVGQndNQ01DY0dDU3NHQVFRQmdqY1ZDZ1FhTUJnd0NnWUlLd1lCQlFVSEF3TXdDZ1lJS3dZQkJRVUhBd0l3Q2dZSUtvWkl6ajBFQXdJRFNBQXdSUUloQUxFL2ljaG1uV1hDVUtVYmNhM3ljaThvcXdhTHZGZEhWalFydmVJOXVxQWJBaUE5aEM0TThqZ01CQURQU3ptZDJ1aVBKQTZnS1IzTEUwM1U3NWVxYkMvclhBPT0=", "secret": "CkYsEXfV8c1gFHAtFWoZv73pGMvh/Qyo4LzKM2h/8Hg="}"""
        })
