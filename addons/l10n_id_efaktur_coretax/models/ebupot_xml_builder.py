# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import models
from odoo.addons.account.tools import dict_to_xml


class EbupotXMLBuilder(models.AbstractModel):
    _name = 'l10n_id_efaktur_coretax.ebupot.xml.builder'
    _description = 'E-Bupot XML Builder'

    def _build_ebupot_xml(self, tin, data):
        document_node = self._get_ebupot_document_node(tin, data)
        xml_content = dict_to_xml(
            document_node,
            nsmap=self._get_ebupot_document_nsmap(),
            template=self._get_ebupot_document_template(),
        )
        return etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8')

    def _get_ebupot_document_nsmap(self):
        return {'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}

    def _get_ebupot_document_template(self):
        return {
            'TIN': {},
            'ListOfBpu': {
                'Bpu': {
                    'TaxPeriodMonth': {},
                    'TaxPeriodYear': {},
                    'CounterpartTin': {},
                    'IDPlaceOfBusinessActivityOfIncomeRecipient': {},
                    'TaxCertificate': {},
                    'TaxObjectCode': {},
                    'TaxBase': {},
                    'Rate': {},
                    'Document': {},
                    'DocumentNumber': {},
                    'DocumentDate': {},
                    'IDPlaceOfBusinessActivity': {},
                    'GovTreasurerOpt': {},
                    'SP2DNumber': {},
                    'WithholdingDate': {},
                },
            },
        }

    def _get_ebupot_document_node(self, tin, data):
        return {
            '_tag': 'BpuBulk',
            'TIN': {'_text': tin},
            'ListOfBpu': {
                'Bpu': [self._get_ebupot_bpu_node(line) for line in data],
            },
        }

    def _get_ebupot_bpu_node(self, line):
        sp2d_number = {'xsi:nil': 'true'} if not line['SP2DNumber'] else {'_text': line['SP2DNumber']}
        return {
            'TaxPeriodMonth': {'_text': line['TaxPeriodMonth']},
            'TaxPeriodYear': {'_text': line['TaxPeriodYear']},
            'CounterpartTin': {'_text': line['CounterpartTin']},
            'IDPlaceOfBusinessActivityOfIncomeRecipient': {'_text': line['IDPlaceOfBusinessActivityOfIncomeRecipient']},
            'TaxCertificate': {'_text': line['TaxCertificate']},
            'TaxObjectCode': {'_text': line['TaxObjectCode']},
            'TaxBase': {'_text': line['TaxBase']},
            'Rate': {'_text': line['Rate']},
            'Document': {'_text': line['Document']},
            'DocumentNumber': {'_text': line['DocumentNumber']},
            'DocumentDate': {'_text': line['DocumentDate']},
            'IDPlaceOfBusinessActivity': {'_text': line['IDPlaceOfBusinessActivity']},
            'GovTreasurerOpt': {'_text': line['GovTreasurerOpt']},
            'SP2DNumber': sp2d_number,
            'WithholdingDate': {'_text': line['WithholdingDate']},
        }
