from odoo import models
from lxml import etree
from base64 import b64encode, b64decode
from odoo.modules.module import get_module_resource


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _l10n_sa_get_compliance_files(self):
        """
            Override to add simplified invoices to compliance checks
        """
        compliance_files = super()._l10n_sa_get_compliance_files()
        file_names = ['simplified/invoice.xml', 'simplified/credit.xml', 'simplified/debit.xml']
        for file in file_names:
            fpath = get_module_resource('l10n_sa_edi_pos', 'tests/compliance', file)
            with open(fpath, 'rb') as ip:
                compliance_files[file] = ip.read().decode()
        return compliance_files

    def _l10n_sa_prepare_compliance_xml(self, xml_name, xml_raw, PCSID, signature):
        """
            Override to process simplified invoices
        """
        signed_xml = super()._l10n_sa_prepare_compliance_xml(xml_name, xml_raw, PCSID, signature)
        if xml_name.startswith('simplified'):
            qr_code_str = self.env['account.move'].with_context(from_pos=True)._l10n_sa_get_qr_code(self, signed_xml, b64decode(PCSID).decode(), signature)
            root = etree.fromstring(signed_xml)
            qr_node = root.xpath('//*[local-name()="ID"][text()="QR"]/following-sibling::*/*')[0]
            qr_node.text = b64encode(qr_code_str).decode()
            return etree.tostring(root, with_tail=False)
        return signed_xml