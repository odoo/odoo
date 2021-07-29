# -*- coding: utf-8 -*-
import base64

from freezegun import freeze_time

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo import fields, Command


class TestUBLCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None, edi_format_ref='account_edi_ubl.edi_ubl_bis3'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        # Ensure the testing currency is using a valid ISO code.
        real_usd = cls.env.ref('base.USD')
        real_usd.name = 'FUSD'
        real_usd.flush(['name'])
        cls.currency_data['currency'].name = 'USD'

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        # OVERRIDE to force the company with EUR currency.
        eur = cls.env.ref('base.EUR')
        if not eur.active:
            eur.active = True

        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].currency_id = eur
        return res

    @classmethod
    def _get_tax_by_xml_id(cls, tax_xml_id):
        """ Helper to retrieve a tax easily.

        :param tax_xml_id:  The tax template's xml id.
        :return:            An account.tax record
        """
        module, trailing_id = tax_xml_id.split('.')
        return cls.env.ref(f'{module}.{cls.env.company.id}_{trailing_id}')

    def assert_same_invoice(self, invoice1, invoice2, **invoice_kwargs):
        self.assertRecordValues(invoice2, [{
            'partner_id': invoice1.company_id.partner_id.id,
            'invoice_date': fields.Date.from_string(invoice1.date),
            'currency_id': invoice1.currency_id.id,
            'amount_untaxed': invoice1.amount_untaxed,
            'amount_tax': invoice1.amount_tax,
            'amount_total': invoice1.amount_total,
            **invoice_kwargs,
        }])

        default_invoice_line_kwargs_list = [{}] * len(invoice1.invoice_line_ids)
        invoice_line_kwargs_list = invoice_kwargs.get('invoice_line_ids', default_invoice_line_kwargs_list)
        self.assertRecordValues(invoice2.invoice_line_ids, [{
            'quantity': line.quantity,
            'price_unit': line.price_unit,
            'discount': line.discount,
            'product_id': line.product_id.id,
            'tax_ids': line.tax_ids.ids,
            **invoice_line_kwargs,
        } for line, invoice_line_kwargs in zip(invoice1.invoice_line_ids, invoice_line_kwargs_list)])

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    @freeze_time('2017-01-01')
    def _import_invoice_bis3(self, invoice, xml_etree, xml_filename):
        new_invoice = self.edi_format._create_invoice_from_xml_tree(
            self.company_data['default_journal_purchase'],
            xml_filename,
            xml_etree,
        )

        self.assertTrue(new_invoice)
        self.assert_same_invoice(invoice, new_invoice)

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    @freeze_time('2017-01-01')
    def _export_invoice_bis3(self, seller, buyer, xpaths='', export_file=False, **invoice_kwargs):
        # Setup the seller.
        self.env.company.write({
            'partner_id': seller.id,
            'name': seller.name,
            'street': seller.street,
            'zip': seller.zip,
            'city': seller.city,
            'vat': seller.vat,
            'country_id': seller.country_id.id,
        })

        move_type = invoice_kwargs['move_type']
        invoice = self.env['account.move'].create({
            'partner_id': buyer.id,
            'partner_bank_id': (seller if move_type == 'out_invoice' else buyer).bank_ids[:1].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_origin': 'test invoice origin',
            'narration': 'test narration',
            **invoice_kwargs,
            'invoice_line_ids': [
                Command.create({
                    'sequence': i,
                    'product_id': self.product_a.id,
                    **invoice_line_kwargs,
                })
                for i, invoice_line_kwargs in enumerate(invoice_kwargs.get('invoice_line_ids', []))
            ],
        })
        invoice.action_post()

        attachment = invoice._get_edi_attachment(self.edi_format)
        self.assertTrue(attachment)
        xml_filename = attachment.name
        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)

        # DEBUG: uncomment these lines to get the xml and then, be able to submit it online for validation.
        # if export_file:
        #     with open(export_file, 'wb+') as f:
        #         f.write(xml_content)

        if invoice.move_type == 'out_invoice':
            invoice_tag = 'Invoice'
            invoice_type_code = 380
            invoice_type_code_tag = 'InvoiceTypeCode'
        else:
            invoice_tag = 'CreditNote'
            invoice_type_code = 381
            invoice_type_code_tag = 'CreditNoteTypeCode'

        xml_etree = self.get_xml_tree_from_string(xml_content)
        self.assertXmlTreeEqual(
            xml_etree,
            self.with_applied_xpath(
                self.get_xml_tree_from_string(f'''
                    <{invoice_tag}>
                        <UBLVersionID>2.1</UBLVersionID>
                        <CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</CustomizationID>
                        <ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</ProfileID>
                        <ID>{invoice.name}</ID>
                        <IssueDate>2017-01-01</IssueDate>
                        <{invoice_type_code_tag}>{invoice_type_code}</{invoice_type_code_tag}>
                        <Note>test narration</Note>
                        <DocumentCurrencyCode>USD</DocumentCurrencyCode>
                        <OrderReference>
                            <ID>test invoice origin</ID>
                        </OrderReference>
                        <AccountingSupplierParty>
                            <Party>
                                <EndpointID>{seller.vat}</EndpointID>
                                <PartyName>
                                    <Name>{seller.name}</Name>
                                </PartyName>
                                <PostalAddress>
                                    <StreetName>{seller.street}</StreetName>
                                    <CityName>{seller.city}</CityName>
                                    <PostalZone>{seller.zip}</PostalZone>
                                    <Country>
                                        <IdentificationCode>{seller.country_id.code}</IdentificationCode>
                                    </Country>
                                </PostalAddress>
                                <PartyTaxScheme>
                                    <CompanyID>{seller.vat}</CompanyID>
                                    <TaxScheme>
                                        <ID>VAT</ID>
                                    </TaxScheme>
                                </PartyTaxScheme>
                                <PartyLegalEntity>
                                    <RegistrationName>{seller.name}</RegistrationName>
                                    <CompanyID>{seller.vat}</CompanyID>
                                </PartyLegalEntity>
                                <Contact>
                                    <Name>{seller.name}</Name>
                                </Contact>
                            </Party>
                        </AccountingSupplierParty>
                        <AccountingCustomerParty>
                            <Party>
                                <EndpointID>{buyer.vat}</EndpointID>
                                <PartyName>
                                    <Name>{buyer.name}</Name>
                                </PartyName>
                                <PostalAddress>
                                    <StreetName>{buyer.street}</StreetName>
                                    <CityName>{buyer.city}</CityName>
                                    <PostalZone>{buyer.zip}</PostalZone>
                                    <Country>
                                        <IdentificationCode>{buyer.country_id.code}</IdentificationCode>
                                    </Country>
                                </PostalAddress>
                                <PartyTaxScheme>
                                    <CompanyID>{buyer.vat}</CompanyID>
                                    <TaxScheme>
                                        <ID>VAT</ID>
                                    </TaxScheme>
                                </PartyTaxScheme>
                                <PartyLegalEntity>
                                    <RegistrationName>{buyer.name}</RegistrationName>
                                    <CompanyID>{buyer.vat}</CompanyID>
                                </PartyLegalEntity>
                                <Contact>
                                    <Name>{buyer.name}</Name>
                                </Contact>
                            </Party>
                        </AccountingCustomerParty>
                        <PaymentMeans>
                            <PaymentMeansCode>30</PaymentMeansCode>
                            <PaymentID>{invoice.name}</PaymentID>
                        </PaymentMeans>
                        <PaymentTerms>
                            <Note>30% Advance End of Following Month</Note>
                        </PaymentTerms>
                    </{invoice_tag}>
                '''),
                xpaths,
            ),
        )
        return invoice, xml_etree, xml_filename
