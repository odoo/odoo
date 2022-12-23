import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.modules.module import get_module_resource
from datetime import datetime
from base64 import b64decode, b64encode
from lxml import etree


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_sa_csr = fields.Binary(attachment=False, copy=False, compute="_l10n_sa_compute_csr", store=True,
                                help="The Certificate Signing Request that is submitted to the Compliance API")

    l10n_sa_compliance_csid_json = fields.Char("CCSID JSON", copy=False,
                                               help="Compliance CSID data received from the Compliance CSID API "
                                                    "in dumped json format")
    l10n_sa_production_csid_json = fields.Char("PCSID JSON", copy=False,
                                               help="Production CSID data received from the Production CSID API "
                                                    "in dumped json format")
    l10n_sa_production_csid_validity = fields.Datetime("PCSID Expiration", help="Production CSID expiration date",
                                                       compute="_l10n_sa_compute_production_csid_validity", store=True)
    l10n_sa_compliance_checks_passed = fields.Boolean("Compliance Checks Done", default=False, copy=False,
                                                      help="Specifies if the Compliance Checks have been completed successfully")

    def _l10n_sa_csr_required_fields(self):
        return ['l10n_sa_private_key', 'l10n_sa_serial_number', 'l10n_sa_organization_unit', 'vat', 'name', 'city',
                'country_id', 'state_id']

    @api.depends('company_id.l10n_sa_private_key', 'company_id.l10n_sa_serial_number',
                 'company_id.l10n_sa_organization_unit', 'company_id.vat', 'company_id.name', 'company_id.city',
                 'company_id.country_id', 'company_id.state_id')
    def _l10n_sa_compute_csr(self):
        """
            Generate a certificate signing request (CSR) that will be used to obtain an X509 certificate from the
            ZATCA Compliance API
        """
        for journal in self:
            journal._l10n_sa_reset_certificates()
            if all(journal.company_id[f] for f in self._l10n_sa_csr_required_fields()):
                journal.l10n_sa_csr = journal.company_id._l10n_sa_generate_company_csr()

    def l10n_sa_regen_csr(self):
        self.ensure_one()
        if any(not self.company_id[f] for f in self._l10n_sa_csr_required_fields()):
            raise UserError(_("Please, make sure all the following fields have been correctly set on the Company: \n")
                            + "\n".join(" - %s" % self.company_id._fields[f].string for f in self._l10n_sa_csr_required_fields() if not self.company_id[f]))
        self._l10n_sa_compute_csr()

    @api.depends('l10n_sa_production_csid_json')
    def _l10n_sa_compute_production_csid_validity(self):
        """
            Compute the expiration date of the Production certificate
        """
        for company in self:
            company.l10n_sa_production_csid_validity = False
            if company.l10n_sa_production_csid_json:
                company.l10n_sa_production_csid_validity = self.env.ref(
                    'l10n_sa_edi.edi_sa_zatca')._l10n_sa_get_pcsid_validity(
                    json.loads(company.l10n_sa_production_csid_json))

    def _l10n_sa_reset_certificates(self):
        """
            Reset all certificate values, including CSR and compliance checks
        """
        for journal in self:
            journal.l10n_sa_csr = False
            journal.l10n_sa_production_csid_json = False
            journal.l10n_sa_compliance_csid_json = False
            journal.l10n_sa_compliance_checks_passed = False

    @api.model
    def _l10n_sa_get_edi_format(self):
        """
            Helper function that returns the ZATCA EDI Format
        :return: ZATCA EDI Format
        """
        return self.env.ref('l10n_sa_edi.edi_sa_zatca')

    def l10n_sa_api_get_compliance_CSID(self, otp):
        """
            Request a Compliance Cryptographic Stamp Identifier (CCSID) from ZATCA
        :return: Either raise an error in case the API returns one, or display a success notification
        """
        CCSID_data = self._l10n_sa_get_edi_format()._l10n_sa_generate_compliance_csid(self, otp)
        if CCSID_data.get('error'):
            raise UserError(_("Could not obtain Compliance CSID: %s") % CCSID_data['error'])
        self.write({
            'l10n_sa_compliance_csid_json': json.dumps(CCSID_data),
            'l10n_sa_production_csid_json': False,
            'l10n_sa_compliance_checks_passed': False,
        })

    def l10n_sa_api_get_production_CSID(self, OTP=None):
        """
            Request a Production Cryptographic Stamp Identifier (PCSID) from ZATCA
        :return: Either raise an error in case the API returns one, or display a success notification
        """

        if not self.l10n_sa_compliance_csid_json:
            raise UserError(_("Cannot request a Production CSID before requesting a CCSID first"))
        elif not self.l10n_sa_compliance_checks_passed:
            raise UserError(_("Cannot request a Production CSID before completing the Compliance Checks"))

        edi_format = self._l10n_sa_get_edi_format()
        renew = False

        if self.l10n_sa_production_csid_json:
            time_now = edi_format._l10n_sa_get_zatca_datetime(datetime.now())
            if edi_format._l10n_sa_get_zatca_datetime(self.l10n_sa_production_csid_validity) < time_now:
                renew = True
            else:
                raise UserError(_("The Production CSID is still valid. You can only renew it once it has expired."))

        CCSID_data = json.loads(self.l10n_sa_compliance_csid_json)
        PCSID_data = edi_format._l10n_sa_generate_production_csid(self, CCSID_data, renew, OTP)
        if PCSID_data.get('error'):
            raise UserError(_("Could not obtain Production CSID: %s") % PCSID_data['error'])
        self.l10n_sa_production_csid_json = json.dumps(PCSID_data)

    @api.model
    def _l10n_sa_api_compliance_checks(self, signed_xml, ccsid):
        """
            Helper function that runs the Compliance Checks once the CCSID has been successfully obtained
        :param signed_xml: Signed UBL representation of the Invoice
        :param ccsid: CCSID obtained from the Compliance CSID API
        """
        return self.env.ref('l10n_sa_edi.edi_sa_zatca')._l10n_sa_api_compliance_checks(signed_xml, ccsid)

    @api.model
    def _l10n_sa_sign_xml(self, xml_content, certificate_str, signature):
        """
            Helper function that calls the _l10n_sa_sign_xml method available on the EDI Format model to sign
            the UBL document of an invoice
        """
        return self.env.ref('l10n_sa_edi.edi_sa_zatca')._l10n_sa_sign_xml(xml_content, certificate_str, signature)

    def _l10n_sa_get_compliance_files(self):
        """
            Return the list of files to be used for the compliance checks.
        """
        file_names, compliance_files = ['standard/invoice.xml', 'standard/credit.xml', 'standard/debit.xml'], {}
        for file in file_names:
            fpath = get_module_resource('l10n_sa_edi', 'tests/compliance', file)
            with open(fpath, 'rb') as ip:
                compliance_files[file] = ip.read().decode()
        return compliance_files

    def l10n_sa_run_compliance_checks(self):
        """
            Run Compliance Checks once the CCSID has been obtained.

            The goal of the Compliance Checks is to make sure our system is able to produce, sign and send Invoices
            correctly. For this we use dummy invoice UBL files available under the tests/compliance folder:

            Standard Invoice, Standard Credit Note, Standard Debit Note, Simplified Invoice, Simplified Credit Note,
            Simplified Debit Note.

            We read each one of these files separately, sign them, then process them through the Compliance Checks API.
        """
        if self.country_code != 'SA':
            raise UserError(_("Compliance checks can only be run for companies operating from KSA"))
        if not self.l10n_sa_compliance_csid_json:
            raise UserError(_("You need to request the CCSID first before you can proceed"))
        edi_format = self.env.ref('l10n_sa_edi.edi_sa_zatca')
        CCSID_data = json.loads(self.l10n_sa_compliance_csid_json)
        compliance_files = self._l10n_sa_get_compliance_files()
        for fname, fval in compliance_files.items():
            invoice_hash_hex = edi_format._l10n_sa_generate_invoice_xml_hash(fval).decode()
            digital_signature = edi_format._l10n_sa_get_digital_signature(self.company_id, invoice_hash_hex).decode()
            prepared_xml = self._l10n_sa_prepare_compliance_xml(fname, fval, CCSID_data['binarySecurityToken'], digital_signature)
            result = self._l10n_sa_api_compliance_checks(prepared_xml.decode(), CCSID_data)
            if result.get('error'):
                raise UserError(_("Could not complete Compliance Checks for the following file: %s") % fname)
            if result['validationResults']['status'] != 'PASS':
                raise UserError(_("Could not complete Compliance Checks for the following file: %s") % fname)
        self.l10n_sa_compliance_checks_passed = True

    def _l10n_sa_prepare_compliance_xml(self, xml_name, xml_raw, PCSID, signature):
        """
            Prepare XML content to be used for Compliance checks
        :param xml_name: Name of the compliance file to be used
        :param xml_raw: Raw content of the compliance file
        :param PCSID: X509 certificate obtained for the journal
        :return: prepared & signed xml content for compliance checks
        """
        xml_content = self._l10n_sa_prepare_invoice_xml(xml_raw)
        signed_xml = self._l10n_sa_sign_xml(xml_content, PCSID, signature)
        return signed_xml

    def _l10n_sa_prepare_invoice_xml(self, xml_content):
        """
            Prepare the XML content of the test invoices before running the compliance checks
        :param xml_content:
        :return: processed string of the provided XML content
        """
        ubl_extensions = etree.fromstring(self.env.ref('l10n_sa_edi.export_sa_zatca_ubl_extensions')._render())
        root = etree.fromstring(xml_content.encode())
        root.insert(0, ubl_extensions)
        ns_map = self._l10n_sa_get_edi_format()._l10n_sa_get_namespaces()

        def _get_node(xpath_str):
            return root.xpath(xpath_str, namespaces=ns_map)[0]

        # Update the Company VAT number in the test invoice
        vat_el = _get_node('//cbc:CompanyID')
        vat_el.text = self.company_id.vat

        # Update the Company Name in the test invoice
        comp_name_el = _get_node('//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name')
        comp_name_el.text = self.company_id.name

        return etree.tostring(root)

    def _l10n_sa_can_submit_einvoices(self):
        """
            Helper function to know if the required CSIDs have been obtained, and the compliance checks have been
            completed
        """
        self.ensure_one()
        return self.country_code != 'SA' or self.l10n_sa_production_csid_json