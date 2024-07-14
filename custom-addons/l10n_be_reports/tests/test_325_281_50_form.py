# -*- coding: utf-8 -*-

from freezegun import freeze_time
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
@freeze_time('2022-03-01')
class TestResPartner(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.invoice = cls.init_invoice('in_invoice')

        cls.partner_a.write({
            'street': 'Rue du Jacobet, 9',
            'zip': '7100',
            'city': 'La Louvière',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0475646428',
            'is_company': True,
            'category_id': [Command.link(cls.env.ref('l10n_be_reports.res_partner_tag_281_50').id)]
        })
        cls.partner_b.write({
            'name': 'SPRL Popiul',
            'street': 'Rue Arthur Libert',
            'street2': 'Longueville 8',
            'zip': '1325',
            'city': 'Chaumont-Gistoux',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0807677428',
            'is_company': True,
            'category_id': [Command.link(cls.env.ref('l10n_be_reports.res_partner_tag_281_50').id)]
        })

        cls.tag_281_50_commissions = cls.env.ref('l10n_be_reports.account_tag_281_50_commissions')
        cls.tag_281_50_fees = cls.env.ref('l10n_be_reports.account_tag_281_50_fees')
        cls.tag_281_50_atn = cls.env.ref('l10n_be_reports.account_tag_281_50_atn')
        cls.tag_281_50_exposed_expenses = cls.env.ref('l10n_be_reports.account_tag_281_50_exposed_expenses')

        (cls.company_data['company'] + cls.company_data_2['company']).write({
            'vat': 'BE0477472701',
            'phone': '+3222903490',
            'street': 'Rue du Laid Burniat 5',
            'zip': '1348',
            'city': 'Ottignies-Louvain-la-Neuve ',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.product_a.property_account_expense_id.tag_ids |= cls.tag_281_50_commissions
        cls.product_b.property_account_expense_id.tag_ids |= cls.tag_281_50_fees

        cls.move_a = cls.create_and_post_bill(partner_id=cls.partner_a, product_id=cls.product_a, amount=1000.0, date='2000-05-12')

        cls.debtor = cls.env.company.partner_id
        cls.sender = cls.env.company.partner_id

        cls.wizard_values = {
            'sender_id': cls.sender.id,
            'reference_year': 2000,
            'is_test': False,
            'sending_type': '0',
            'treatment_type': '0',
        }

    @classmethod
    def create_and_post_bill(cls, partner_id, product_id, amount, date):
        invoice = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner_id.id,
            'invoice_payment_term_id': False,
            'invoice_date': fields.Date.from_string(date),
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': product_id.id,
                    'account_id': product_id.property_account_expense_id.id,
                    'partner_id': partner_id.id,
                    'product_uom_id': product_id.uom_id.id,
                    'quantity': 1.0,
                    'discount': 0.0,
                    'price_unit': amount,
                    'tax_ids': [],
                }),
            ]
        })
        invoice.action_post()
        return invoice

    @classmethod
    def pay_bill(cls, bill, amount, date, currency=None):
        if not currency:
            currency = bill.currency_id
        assert amount
        payment_type = 'outbound' if amount > 0 else 'inbound'
        payment = cls.env['account.payment'].create({
            'payment_type': payment_type,
            'amount': abs(amount),
            'currency_id': currency.id,
            'journal_id': cls.company_data['default_journal_bank'].id,
            'date': fields.Date.from_string(date),
            'partner_id': bill.partner_id.id,
            'payment_method_id': cls.env.ref('account.account_payment_method_manual_out').id,
            'partner_type': 'supplier',
        })
        payment.action_post()
        bill_payable_move_lines = bill.line_ids.filtered(lambda x: x.account_type == 'liability_payable')
        bill_payable_move_lines += payment.line_ids.filtered(lambda x: x.account_type == 'liability_payable')
        bill_payable_move_lines.reconcile()

    def create_325_form(self, ref_year=2000, state='generated', test=False):
        form_325 = self.env['l10n_be.form.325'].create({
            'company_id': self.company_data['company'].id,
            'sender_id': self.sender.id,
            'debtor_id': self.debtor.id,
            'reference_year': ref_year,
            'is_test': test,
            'sending_type': '0',
            'treatment_type': '0',
            'state': 'draft',
        })
        form_325._generate_form_281_50()

        if state == 'generated':
            form_325._validate_form()
        return form_325

    def create_form28150(
        self, ref_year=None, form_type='0', company=None, partner=None, commission=0.0, fees=0.0, atn=0.0,
        exposed_expenses=0.0, paid_amount=0.0, state='generated', test=False
    ):
        if not company:
            company = self.company_data['company']
        if not partner:
            partner = self.partner_a

        form325 = self.env['l10n_be.form.325'].create({
            'company_id': company.id,
            'sender_id': company.partner_id.id,
            'debtor_id': company.partner_id.id,
            'reference_year': ref_year,
            'treatment_type': form_type,
            'is_test': test,
            'state': 'draft',
        })

        form_281_50 = self.env['l10n_be.form.281.50'].create({
            'form_325_id': form325.id,
            'company_id': company.id,
            'income_debtor_bce_number': self.debtor._get_bce_number(),
            'partner_id': partner.id,
            'partner_name': partner.name,
            'partner_job_position': '' if partner.is_company else self.function,
            'partner_citizen_identification': '' if partner.is_company else partner.citizen_identification,
            'partner_bce_number': partner.commercial_partner_id._get_bce_number() if partner.is_company else '',
            'partner_address': ", ".join(street for street in [partner.street, partner.street2] if street),
            'partner_zip': partner.zip,
            'partner_city': partner.city,
            'commissions': commission,
            'fees': fees,
            'atn': atn,
            'exposed_expenses': exposed_expenses,
            'paid_amount': paid_amount,
        })
        if state == 'generated':
            form325._validate_form()
        return form_281_50

    def create_tagged_accounts(self):
        account_ids = [
            self.env['account.account'].with_company(self.company_data['company']).create({
                'name': f"Test account {index}",
                'code': f"6000{index}",
                'account_type': 'expense',
                'tag_ids': [Command.link(tag.id)],
            })
            for index, tag in enumerate((self.tag_281_50_commissions, self.tag_281_50_atn, self.tag_281_50_fees,
                                         self.tag_281_50_exposed_expenses))
        ]
        return account_ids

    def test_281_50_xml_generation_1_partner_eligible_no_payment(self):
        """check the values generated and injected in the xml are as expected
        Simple case: 1 partner, invoice for 1.000,00 currency in an account tagged as commission, no payment
        """
        form_325 = self.create_325_form()
        resulting_xml = form_325._generate_325_form_xml()
        expected_281_50_xml = b"""<?xml version='1.0' encoding='utf-8'?>
                    <Verzendingen>
                        <Verzending>
                            <v0002_inkomstenjaar>2000</v0002_inkomstenjaar>
                            <v0010_bestandtype>BELCOTAX</v0010_bestandtype>
                            <v0011_aanmaakdatum>01-03-2022</v0011_aanmaakdatum>
                            <v0014_naam>company_1_data</v0014_naam>
                            <v0015_adres>Rue du Laid Burniat 5</v0015_adres>
                            <v0016_postcode>1348</v0016_postcode>
                            <v0017_gemeente>Ottignies-Louvain-la-Neuve </v0017_gemeente>
                            <v0018_telefoonnummer>3222903490</v0018_telefoonnummer>
                            <v0021_contactpersoon>Because I am accountman!</v0021_contactpersoon>
                            <v0022_taalcode>2</v0022_taalcode>
                            <v0023_emailadres>accountman@test.com</v0023_emailadres>
                            <v0024_nationaalnr>0477472701</v0024_nationaalnr>
                            <v0025_typeenvoi>0</v0025_typeenvoi>
                            <Aangiften>
                                <Aangifte>
                                    <a1002_inkomstenjaar>2000</a1002_inkomstenjaar>
                                    <a1005_registratienummer>0477472701</a1005_registratienummer>
                                    <a1011_naamnl1>company_1_data</a1011_naamnl1>
                                    <a1013_adresnl>Rue du Laid Burniat 5</a1013_adresnl>
                                    <a1014_postcodebelgisch>1348</a1014_postcodebelgisch>
                                    <a1015_gemeente>Ottignies-Louvain-la-Neuve </a1015_gemeente>
                                    <a1016_landwoonplaats>00000</a1016_landwoonplaats>
                                    <a1020_taalcode>1</a1020_taalcode>
                                    <Opgaven>
                                        <Opgave32550>
                                            <Fiche28150>
                                                <f2002_inkomstenjaar>2000</f2002_inkomstenjaar>
                                                <f2005_registratienummer>0477472701</f2005_registratienummer>
                                                <f2008_typefiche>28150</f2008_typefiche>
                                                <f2009_volgnummer>1</f2009_volgnummer>
                                                <f2013_naam>partner_a</f2013_naam>
                                                <f2015_adres>Rue du Jacobet, 9</f2015_adres>
                                                <f2016_postcodebelgisch>7100</f2016_postcodebelgisch>
                                                <f2017_gemeente>La Louvi\xc3\xa8re</f2017_gemeente>
                                                <f2018_landwoonplaats>00000</f2018_landwoonplaats>
                                                <f2028_typetraitement>0</f2028_typetraitement>
                                                <f2029_enkelopgave325>0</f2029_enkelopgave325>
                                                <f2105_birthplace>0</f2105_birthplace>
                                                <f2112_buitenlandspostnummer/>
                                                <f2114_voornamen/>
                                                <f50_2030_aardpersoon>2</f50_2030_aardpersoon>
                                                <f50_2031_nihil>1</f50_2031_nihil>
                                                <f50_2059_totaalcontrole>200000</f50_2059_totaalcontrole>
                                                <f50_2060_commissies>100000</f50_2060_commissies>
                                                <f50_2061_erelonenofvacatie>0</f50_2061_erelonenofvacatie>
                                                <f50_2062_voordelenaardbedrag>0</f50_2062_voordelenaardbedrag>
                                                <f50_2063_kosten>0</f50_2063_kosten>
                                                <f50_2064_totaal>100000</f50_2064_totaal>
                                                <f50_2065_werkelijkbetaaldb>0</f50_2065_werkelijkbetaaldb>
                                                <f50_2066_sportremuneration>0</f50_2066_sportremuneration>
                                                <f50_2067_managerremuneration>0</f50_2067_managerremuneration>
                                                <f50_2099_comment/>
                                                <f50_2103_advantagenature/>
                                                <f50_2107_uitgeoefendberoep/>
                                                <f50_2109_fiscaalidentificat/>
                                                <f50_2110_kbonbr>0475646428</f50_2110_kbonbr>
                                            </Fiche28150>
                                        </Opgave32550>
                                    </Opgaven>
                                    <r8002_inkomstenjaar>2000</r8002_inkomstenjaar>
                                    <r8005_registratienummer>0477472701</r8005_registratienummer>
                                    <r8010_aantalrecords>3</r8010_aantalrecords>
                                    <r8011_controletotaal>1</r8011_controletotaal>
                                    <r8012_controletotaal>200000</r8012_controletotaal>
                                </Aangifte>
                            </Aangiften>
                            <r9002_inkomstenjaar>2000</r9002_inkomstenjaar>
                            <r9010_aantallogbestanden>3</r9010_aantallogbestanden>
                            <r9011_totaalaantalrecords>5</r9011_totaalaantalrecords>
                            <r9012_controletotaal>1</r9012_controletotaal>
                            <r9013_controletotaal>200000</r9013_controletotaal>
                        </Verzending>
                    </Verzendingen>"""
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(resulting_xml),
            self.get_xml_tree_from_string(expected_281_50_xml),
        )

    def test_281_50_xml_generation_1_partner_eligible(self):
        """check the values generated and injected in the xml are as expected
        Simple case: 1 partner, invoice for 1.000,00 currency in an account tagged as commission and a full payment
        """
        # make a payment to the vendor partner_a and reconcile it with the bill
        self.pay_bill(bill=self.move_a, amount=1000, date='2000-05-12')

        form_325 = self.create_325_form()
        resulting_xml = form_325._generate_325_form_xml()
        expected_281_50_xml = b"""<?xml version='1.0' encoding='utf-8'?>
                    <Verzendingen>
                        <Verzending>
                            <v0002_inkomstenjaar>2000</v0002_inkomstenjaar>
                            <v0010_bestandtype>BELCOTAX</v0010_bestandtype>
                            <v0011_aanmaakdatum>01-03-2022</v0011_aanmaakdatum>
                            <v0014_naam>company_1_data</v0014_naam>
                            <v0015_adres>Rue du Laid Burniat 5</v0015_adres>
                            <v0016_postcode>1348</v0016_postcode>
                            <v0017_gemeente>Ottignies-Louvain-la-Neuve </v0017_gemeente>
                            <v0018_telefoonnummer>3222903490</v0018_telefoonnummer>
                            <v0021_contactpersoon>Because I am accountman!</v0021_contactpersoon>
                            <v0022_taalcode>2</v0022_taalcode>
                            <v0023_emailadres>accountman@test.com</v0023_emailadres>
                            <v0024_nationaalnr>0477472701</v0024_nationaalnr>
                            <v0025_typeenvoi>0</v0025_typeenvoi>
                            <Aangiften>
                                <Aangifte>
                                    <a1002_inkomstenjaar>2000</a1002_inkomstenjaar>
                                    <a1005_registratienummer>0477472701</a1005_registratienummer>
                                    <a1011_naamnl1>company_1_data</a1011_naamnl1>
                                    <a1013_adresnl>Rue du Laid Burniat 5</a1013_adresnl>
                                    <a1014_postcodebelgisch>1348</a1014_postcodebelgisch>
                                    <a1015_gemeente>Ottignies-Louvain-la-Neuve </a1015_gemeente>
                                    <a1016_landwoonplaats>00000</a1016_landwoonplaats>
                                    <a1020_taalcode>1</a1020_taalcode>
                                    <Opgaven>
                                        <Opgave32550>
                                            <Fiche28150>
                                                <f2002_inkomstenjaar>2000</f2002_inkomstenjaar>
                                                <f2005_registratienummer>0477472701</f2005_registratienummer>
                                                <f2008_typefiche>28150</f2008_typefiche>
                                                <f2009_volgnummer>1</f2009_volgnummer>
                                                <f2013_naam>partner_a</f2013_naam>
                                                <f2015_adres>Rue du Jacobet, 9</f2015_adres>
                                                <f2016_postcodebelgisch>7100</f2016_postcodebelgisch>
                                                <f2017_gemeente>La Louvi\xc3\xa8re</f2017_gemeente>
                                                <f2018_landwoonplaats>00000</f2018_landwoonplaats>
                                                <f2028_typetraitement>0</f2028_typetraitement>
                                                <f2029_enkelopgave325>0</f2029_enkelopgave325>
                                                <f2105_birthplace>0</f2105_birthplace>
                                                <f2112_buitenlandspostnummer/>
                                                <f2114_voornamen/>
                                                <f50_2030_aardpersoon>2</f50_2030_aardpersoon>
                                                <f50_2031_nihil>0</f50_2031_nihil>
                                                <f50_2059_totaalcontrole>300000</f50_2059_totaalcontrole>
                                                <f50_2060_commissies>100000</f50_2060_commissies>
                                                <f50_2061_erelonenofvacatie>0</f50_2061_erelonenofvacatie>
                                                <f50_2062_voordelenaardbedrag>0</f50_2062_voordelenaardbedrag>
                                                <f50_2063_kosten>0</f50_2063_kosten>
                                                <f50_2064_totaal>100000</f50_2064_totaal>
                                                <f50_2065_werkelijkbetaaldb>100000</f50_2065_werkelijkbetaaldb>
                                                <f50_2066_sportremuneration>0</f50_2066_sportremuneration>
                                                <f50_2067_managerremuneration>0</f50_2067_managerremuneration>
                                                <f50_2099_comment/>
                                                <f50_2103_advantagenature/>
                                                <f50_2107_uitgeoefendberoep/>
                                                <f50_2109_fiscaalidentificat/>
                                                <f50_2110_kbonbr>0475646428</f50_2110_kbonbr>
                                            </Fiche28150>
                                        </Opgave32550>
                                    </Opgaven>
                                    <r8002_inkomstenjaar>2000</r8002_inkomstenjaar>
                                    <r8005_registratienummer>0477472701</r8005_registratienummer>
                                    <r8010_aantalrecords>3</r8010_aantalrecords>
                                    <r8011_controletotaal>1</r8011_controletotaal>
                                    <r8012_controletotaal>300000</r8012_controletotaal>
                                </Aangifte>
                            </Aangiften>
                            <r9002_inkomstenjaar>2000</r9002_inkomstenjaar>
                            <r9010_aantallogbestanden>3</r9010_aantallogbestanden>
                            <r9011_totaalaantalrecords>5</r9011_totaalaantalrecords>
                            <r9012_controletotaal>1</r9012_controletotaal>
                            <r9013_controletotaal>300000</r9013_controletotaal>
                        </Verzending>
                    </Verzendingen>"""
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(resulting_xml),
            self.get_xml_tree_from_string(expected_281_50_xml),
        )

    def test_281_50_xml_generation_2_partners_eligible(self):
        """check the values generated and injected in the xml are as expected
        2 partners, each invoiced for 1.000,00 currency
        partner_a for an account tagged as commission and a full payment
        partner_b for an account tagged as commission, no payment
        """
        self.create_and_post_bill(self.partner_b, self.product_b, 1000.0, '2000-05-12')

        # make a payment to the vendor partner_a and reconcile it with the bill
        self.pay_bill(bill=self.move_a, amount=1000, date='2000-05-12')

        form_325 = self.create_325_form()
        resulting_xml = form_325._generate_325_form_xml()
        expected_281_50_xml = b"""<?xml version='1.0' encoding='utf-8'?>
                    <Verzendingen>
                        <Verzending>
                            <v0002_inkomstenjaar>2000</v0002_inkomstenjaar>
                            <v0010_bestandtype>BELCOTAX</v0010_bestandtype>
                            <v0011_aanmaakdatum>01-03-2022</v0011_aanmaakdatum>
                            <v0014_naam>company_1_data</v0014_naam>
                            <v0015_adres>Rue du Laid Burniat 5</v0015_adres>
                            <v0016_postcode>1348</v0016_postcode>
                            <v0017_gemeente>Ottignies-Louvain-la-Neuve </v0017_gemeente>
                            <v0018_telefoonnummer>3222903490</v0018_telefoonnummer>
                            <v0021_contactpersoon>Because I am accountman!</v0021_contactpersoon>
                            <v0022_taalcode>2</v0022_taalcode>
                            <v0023_emailadres>accountman@test.com</v0023_emailadres>
                            <v0024_nationaalnr>0477472701</v0024_nationaalnr>
                            <v0025_typeenvoi>0</v0025_typeenvoi>
                            <Aangiften>
                                <Aangifte>
                                    <a1002_inkomstenjaar>2000</a1002_inkomstenjaar>
                                    <a1005_registratienummer>0477472701</a1005_registratienummer>
                                    <a1011_naamnl1>company_1_data</a1011_naamnl1>
                                    <a1013_adresnl>Rue du Laid Burniat 5</a1013_adresnl>
                                    <a1014_postcodebelgisch>1348</a1014_postcodebelgisch>
                                    <a1015_gemeente>Ottignies-Louvain-la-Neuve </a1015_gemeente>
                                    <a1016_landwoonplaats>00000</a1016_landwoonplaats>
                                    <a1020_taalcode>1</a1020_taalcode>
                                    <Opgaven>
                                        <Opgave32550>
                                            <Fiche28150>
                                                <f2002_inkomstenjaar>2000</f2002_inkomstenjaar>
                                                <f2005_registratienummer>0477472701</f2005_registratienummer>
                                                <f2008_typefiche>28150</f2008_typefiche>
                                                <f2009_volgnummer>1</f2009_volgnummer>
                                                <f2013_naam>SPRL Popiul</f2013_naam>
                                                <f2015_adres>Rue Arthur Libert, Longueville 8</f2015_adres>
                                                <f2016_postcodebelgisch>1325</f2016_postcodebelgisch>
                                                <f2017_gemeente>Chaumont-Gistoux</f2017_gemeente>
                                                <f2018_landwoonplaats>00000</f2018_landwoonplaats>
                                                <f2028_typetraitement>0</f2028_typetraitement>
                                                <f2029_enkelopgave325>0</f2029_enkelopgave325>
                                                <f2105_birthplace>0</f2105_birthplace>
                                                <f2112_buitenlandspostnummer/>
                                                <f2114_voornamen/>
                                                <f50_2030_aardpersoon>2</f50_2030_aardpersoon>
                                                <f50_2031_nihil>1</f50_2031_nihil>
                                                <f50_2059_totaalcontrole>200000</f50_2059_totaalcontrole>
                                                <f50_2060_commissies>0</f50_2060_commissies>
                                                <f50_2061_erelonenofvacatie>100000</f50_2061_erelonenofvacatie>
                                                <f50_2062_voordelenaardbedrag>0</f50_2062_voordelenaardbedrag>
                                                <f50_2063_kosten>0</f50_2063_kosten>
                                                <f50_2064_totaal>100000</f50_2064_totaal>
                                                <f50_2065_werkelijkbetaaldb>0</f50_2065_werkelijkbetaaldb>
                                                <f50_2066_sportremuneration>0</f50_2066_sportremuneration>
                                                <f50_2067_managerremuneration>0</f50_2067_managerremuneration>
                                                <f50_2099_comment/>
                                                <f50_2103_advantagenature/>
                                                <f50_2107_uitgeoefendberoep/>
                                                <f50_2109_fiscaalidentificat/>
                                                <f50_2110_kbonbr>0807677428</f50_2110_kbonbr>
                                            </Fiche28150>
                                            <Fiche28150>
                                                <f2002_inkomstenjaar>2000</f2002_inkomstenjaar>
                                                <f2005_registratienummer>0477472701</f2005_registratienummer>
                                                <f2008_typefiche>28150</f2008_typefiche>
                                                <f2009_volgnummer>2</f2009_volgnummer>
                                                <f2013_naam>partner_a</f2013_naam>
                                                <f2015_adres>Rue du Jacobet, 9</f2015_adres>
                                                <f2016_postcodebelgisch>7100</f2016_postcodebelgisch>
                                                <f2017_gemeente>La Louvi\xc3\xa8re</f2017_gemeente>
                                                <f2018_landwoonplaats>00000</f2018_landwoonplaats>
                                                <f2028_typetraitement>0</f2028_typetraitement>
                                                <f2029_enkelopgave325>0</f2029_enkelopgave325>
                                                <f2105_birthplace>0</f2105_birthplace>
                                                <f2112_buitenlandspostnummer/>
                                                <f2114_voornamen/>
                                                <f50_2030_aardpersoon>2</f50_2030_aardpersoon>
                                                <f50_2031_nihil>0</f50_2031_nihil>
                                                <f50_2059_totaalcontrole>300000</f50_2059_totaalcontrole>
                                                <f50_2060_commissies>100000</f50_2060_commissies>
                                                <f50_2061_erelonenofvacatie>0</f50_2061_erelonenofvacatie>
                                                <f50_2062_voordelenaardbedrag>0</f50_2062_voordelenaardbedrag>
                                                <f50_2063_kosten>0</f50_2063_kosten>
                                                <f50_2064_totaal>100000</f50_2064_totaal>
                                                <f50_2065_werkelijkbetaaldb>100000</f50_2065_werkelijkbetaaldb>
                                                <f50_2066_sportremuneration>0</f50_2066_sportremuneration>
                                                <f50_2067_managerremuneration>0</f50_2067_managerremuneration>
                                                <f50_2099_comment/>
                                                <f50_2103_advantagenature/>
                                                <f50_2107_uitgeoefendberoep/>
                                                <f50_2109_fiscaalidentificat/>
                                                <f50_2110_kbonbr>0475646428</f50_2110_kbonbr>
                                            </Fiche28150>
                                        </Opgave32550>
                                    </Opgaven>
                                    <r8002_inkomstenjaar>2000</r8002_inkomstenjaar>
                                    <r8005_registratienummer>0477472701</r8005_registratienummer>
                                    <r8010_aantalrecords>4</r8010_aantalrecords>
                                    <r8011_controletotaal>3</r8011_controletotaal>
                                    <r8012_controletotaal>500000</r8012_controletotaal>
                                </Aangifte>
                            </Aangiften>
                            <r9002_inkomstenjaar>2000</r9002_inkomstenjaar>
                            <r9010_aantallogbestanden>3</r9010_aantallogbestanden>
                            <r9011_totaalaantalrecords>6</r9011_totaalaantalrecords>
                            <r9012_controletotaal>3</r9012_controletotaal>
                            <r9013_controletotaal>500000</r9013_controletotaal>
                        </Verzending>
                    </Verzendingen>"""
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(resulting_xml),
            self.get_xml_tree_from_string(expected_281_50_xml),
        )

    def test_281_50_partner_remuneration_should_include_amount_directly_put_in_expense_without_invoice(self):
        expense_account_atn_281_50 = self.copy_account(self.company_data['default_account_expense'])
        expense_account_atn_281_50.tag_ids = self.tag_281_50_atn

        statement = self.env['account.bank.statement'].create({
            'name': '281.50 test',
            'date': fields.Date.from_string('2000-05-12'),
            'balance_end_real': -1000.0,
            'line_ids': [
                (0, 0, {
                    'journal_id': self.company_data['default_journal_bank'].id,
                    'payment_ref': 'line2',
                    'partner_id': self.partner_b.id,
                    'amount': -1000.0,
                    'date': fields.Date.from_string('2000-05-12'),
                }),
            ],
        })

        st_line = statement.line_ids
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        line = wizard.line_ids.filtered(lambda x: x.flag == 'auto_balance')
        wizard._js_action_mount_line_in_edit(line.index)
        line.account_id = expense_account_atn_281_50
        wizard._line_value_changed_account_id(line)
        wizard._action_validate()

        form_325 = self.create_325_form()
        form_281_50 = form_325.form_281_50_ids

        self.assertRecordValues(form_325.form_281_50_ids, [
            # pylint: disable=C0326
            {'partner_id': self.partner_b.id, 'commissions':    0.0, 'fees': 0.0, 'atn': 1000.0, 'exposed_expenses': 0.0, 'total_remuneration': 1000.0, 'paid_amount': 1000.0, },
            {'partner_id': self.partner_a.id, 'commissions': 1000.0, 'fees': 0.0, 'atn':    0.0, 'exposed_expenses': 0.0, 'total_remuneration': 1000.0, 'paid_amount':    0.0, },
        ])
        self.assertRecordValues(form_325, [
            {
                'form_281_50_total_amount': 2000.0,
                'form_281_50_ids': form_281_50.ids,
            }
        ])

    def test_281_50_partner_remuneration_should_not_include_amount_from_last_year_directly_put_as_expense(self):
        expense_account_atn_281_50 = self.copy_account(self.company_data['default_account_expense'])
        expense_account_atn_281_50.tag_ids = self.tag_281_50_atn

        statement = self.env['account.bank.statement'].create({
            'name': '281.50 test',
            'date': fields.Date.from_string('1999-05-12'),
            'balance_end_real': -1000.0,
            'line_ids': [
                (0, 0, {
                    'journal_id': self.company_data['default_journal_bank'].id,
                    'payment_ref': 'line2',
                    'partner_id': self.partner_b.id,
                    'amount': -1000.0,
                    'date': fields.Date.from_string('1999-05-12'),
                }),
            ],
        })

        st_line = statement.line_ids
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        line = wizard.line_ids.filtered(lambda x: x.flag == 'auto_balance')
        wizard._js_action_mount_line_in_edit(line.index)
        line.account_id = expense_account_atn_281_50
        wizard._line_value_changed_account_id(line)
        wizard._action_validate()

        form_325 = self.create_325_form()
        form_281_50_partner_b = form_325.form_281_50_ids.filtered(lambda f: f.partner_id == self.partner_b)

        self.assertEqual(len(form_281_50_partner_b), 0, "Amount paid in 1999 shouldn't be taken into account for ref_year 2020")

    def test_281_50_partner_remuneration_should_not_include_commission_from_previous_year(self):
        previous_year_bill = self.create_and_post_bill(self.partner_b, self.product_b, 500.0, '1999-05-12')
        self.pay_bill(bill=previous_year_bill, amount=250, date='1999-05-12')
        # make a payment to the vendor partner_b and reconcile it with the bill for the previous year
        self.pay_bill(bill=previous_year_bill, amount=250, date='2000-05-12')
        form_325 = self.create_325_form()
        form_281_50 = form_325.form_281_50_ids
        self.assertRecordValues(form_325.form_281_50_ids, [
            # pylint: disable=C0326
            {'partner_id': self.partner_b.id, 'commissions':    0.0, 'fees': 0.0, 'atn': 0.0, 'exposed_expenses': 0.0, 'total_remuneration':    0.0, 'paid_amount': 250.0, },
            {'partner_id': self.partner_a.id, 'commissions': 1000.0, 'fees': 0.0, 'atn': 0.0, 'exposed_expenses': 0.0, 'total_remuneration': 1000.0, 'paid_amount':   0.0, },
        ])
        self.assertRecordValues(form_325, [
            {
                'form_281_50_total_amount': 1000.0,
                'form_281_50_ids': form_281_50.ids,
            }
        ])

    def test_325_50_wizard_should_return_325_form_view(self):
        action = self.env['l10n_be.form.325.wizard']\
            .with_company(self.company_data['company'])\
            .create(self.wizard_values)\
            .action_generate_325_form()
        form_325 = self.env['l10n_be.form.325'].search([('company_id', '=', self.company_data['company'].id)])
        self.assertEqual({
            "name": "325 - 2000",
            "type": "ir.actions.act_window",
            "res_model": "l10n_be.form.325",
            "res_id": form_325.id,
            "views": [[False, "form"]],
            "target": "main",
        }, action)

    def test_action_generate_281_50_form_xml_generate_325_50_xml_file_should_create_xml_attachment(self):
        form_325 = self.create_325_form(ref_year=2000)
        action_create_xml = form_325.action_generate_281_50_form_xml()
        self.assertEqual({'type': 'ir.actions.client', 'tag': 'reload'}, action_create_xml)
        attachment = self.env['ir.attachment'].search([
            ('company_id', '=', form_325.company_id.id),
            ('res_model', '=', form_325._name),
            ('res_id', '=', form_325.id),
        ])
        self.assertTrue(len(attachment), 1)
        self.assertEqual(attachment.name, "2000-325.50.xml")

    def test_action_generate_281_50_form_pdf_flow_should_create_pdf_attachment(self):
        form_325 = self.create_325_form(ref_year=2000)
        action_create_all_pdf = form_325.action_generate_281_50_form_pdf()
        self.assertEqual({'type': 'ir.actions.client', 'tag': 'reload'}, action_create_all_pdf)
        attachment = self.env['ir.attachment'].search([
            ('company_id', '=', form_325.company_id.id),
            ('res_model', '=', form_325._name),
            ('res_id', '=', form_325.id),
        ])
        self.assertTrue(len(attachment), 1)
        self.assertEqual(attachment.name, form_325.form_281_50_ids._get_pdf_file_name())

    def test_action_download_281_50_individual_pdf_flow_should_work_smoothly(self):
        form_325 = self.create_325_form(ref_year=2000)
        form_281_50 = form_325.form_281_50_ids
        action_download_single_pdf = form_281_50.action_download_281_50_individual_pdf()
        self.assertEqual({
            'type': 'ir.actions.act_url',
            'name': "Download 281.50 Form PDF",
            'url': f"/web/content/res.partner/{self.partner_a.id}/form_file/{form_281_50._get_pdf_file_name()}?download=true"
        }, action_download_single_pdf)

    def test_action_generate_325_form_pdf_flow_should_work_smoothly(self):
        form_325 = self.create_325_form(ref_year=2000)
        action_create_325_pdf = form_325.action_generate_325_form_pdf()
        self.assertEqual({'type': 'ir.actions.client', 'tag': 'reload'}, action_create_325_pdf)
        attachment = self.env['ir.attachment'].search([
            ('company_id', '=', form_325.company_id.id),
            ('res_model', '=', form_325._name),
            ('res_id', '=', form_325.id),
        ])
        self.assertTrue(len(attachment), 1)
        self.assertEqual(attachment.name, f"{form_325.reference_year}_325_form.pdf")

    def test_325_50_invoicing_and_paying_subpartner_should_impact_commercial_partner(self):
        parent_partner = self.env['res.partner'].create({
            'name': 'parent partner',
            'is_company': True,
            'street': "Rue des Bourlottes 9",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0477472701',
            'country_id': self.env.ref('base.be').id,
            'category_id': [Command.link(self.env.ref('l10n_be_reports.res_partner_tag_281_50').id)]
        })
        child_partner = self.env['res.partner'].create({
            'name': 'child partner',
            'is_company': False,
            'street': "Rue du doudou",
            'street2': "3",
            'zip': "7000",
            'city': "Mons",
            'citizen_identification': '12345612345',
            'country_id': self.env.ref('base.be').id,
            'parent_id': parent_partner.id,
            'category_id': [Command.link(self.env.ref('l10n_be_reports.res_partner_tag_281_50').id)],
        })
        bill = self.create_and_post_bill(partner_id=child_partner, product_id=self.product_a, amount=1000.0, date='2000-05-12')
        self.pay_bill(bill=bill, amount=1000.0, date='2000-05-12')
        form_325 = self.create_325_form(ref_year=2000)
        form_281_50_from_form_325_ids = form_325.form_281_50_ids
        self.assertRecordValues(form_325.form_281_50_ids, [
            # pylint: disable=C0326
            {'partner_id': parent_partner.id, 'commissions': 1000.0, 'fees': 0.0, 'atn': 0.0, 'exposed_expenses': 0.0, 'total_remuneration': 1000.0, 'paid_amount': 1000.0, 'partner_is_natural_person': False, },
            {'partner_id': self.partner_a.id, 'commissions': 1000.0, 'fees': 0.0, 'atn': 0.0, 'exposed_expenses': 0.0, 'total_remuneration': 1000.0, 'paid_amount':    0.0, 'partner_is_natural_person': False, }
        ])
        self.assertRecordValues(form_325, [{
            'form_281_50_total_amount': 2000.0,
            'form_281_50_ids': form_281_50_from_form_325_ids.ids,
        }])

    def test_325_50_invoicing_and_paying_subpartner_should_impact_commercial_partner_legacy_issue(self):
        """ In previous version from Odoo, the aml could get the partner_id instead of the commercial_partner_id
        set as a partner
        """
        parent_partner = self.env['res.partner'].create({
            'name': 'parent partner',
            'is_company': True,
            'street': "Rue des Bourlottes 9",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0477472701',
            'country_id': self.env.ref('base.be').id,
            'category_id': [Command.link(self.env.ref('l10n_be_reports.res_partner_tag_281_50').id)]
        })
        child_partner = self.env['res.partner'].create({
            'name': 'child partner',
            'is_company': False,
            'street': "Rue du doudou",
            'street2': "3",
            'zip': "7000",
            'city': "Mons",
            'citizen_identification': '12345612345',
            'country_id': self.env.ref('base.be').id,
            'parent_id': parent_partner.id,
            'category_id': [Command.link(self.env.ref('l10n_be_reports.res_partner_tag_281_50').id)],
        })
        bill = self.create_and_post_bill(partner_id=child_partner, product_id=self.product_a, amount=1500.0, date='2000-05-12')
        # simulate the previous behavior of Odoo setting the child_partner on the amls instead of commercial_partner_id
        # for details on this solved issue, see those 2 commits as examples:
        # https://github.com/odoo/odoo/commit/4606d1a8890
        # https://github.com/odoo/odoo/commit/91379d20da6f7114359c9147654a60fe86b904d5
        bill.line_ids.partner_id = child_partner

        self.pay_bill(bill=bill, amount=1500.0, date='2000-05-12')
        form_325 = self.create_325_form(ref_year=2000)
        form_281_50_from_form_325_ids = form_325.form_281_50_ids
        self.assertRecordValues(form_325.form_281_50_ids, [
            # pylint: disable=C0326
            {'partner_id': parent_partner.id, 'commissions': 1500.0, 'fees': 0.0, 'atn': 0.0, 'exposed_expenses': 0.0,
                'total_remuneration': 1500.0, 'paid_amount': 1500.0, 'partner_is_natural_person': False, },
            {'partner_id': self.partner_a.id, 'commissions': 1000.0, 'fees': 0.0, 'atn': 0.0, 'exposed_expenses': 0.0,
                'total_remuneration': 1000.0, 'paid_amount':    0.0, 'partner_is_natural_person': False, }
        ])
        self.assertRecordValues(form_325, [{
            'form_281_50_total_amount': 2500.0,
            'form_281_50_ids': form_281_50_from_form_325_ids.ids,
        }])

    def test_281_50_should_have_basic_sequence(self):
        """Ensure 281_50 gets a sequence assigned and that it is multi_company_safe"""
        form = self.create_form28150(ref_year=2020)
        self.assertEqual(form.official_id, '1')
        form_2 = self.create_form28150(ref_year=2020)
        self.assertEqual(form_2.official_id, '2')

    def test_281_50_sequence_should_be_company_dependent(self):
        """Ensure 281_50 gets a sequence assigned and that it is multi_company_safe"""
        form_company_a = self.create_form28150(ref_year=2020)
        self.assertEqual(form_company_a.official_id, '1')
        company_b = self.company_data_2['company']
        form_company_b = self.create_form28150(ref_year=2020, company=company_b)
        self.assertEqual(form_company_b.official_id, '1')

    def test_281_50_sequence_should_reset_on_different_year(self):
        """Ensure 281_50 gets its sequence reset when created on another year"""
        form_year_1 = self.create_form28150(ref_year=2020)
        self.assertEqual(form_year_1.official_id, '1')
        form_year_2 = self.create_form28150(ref_year=2021)
        self.assertEqual(form_year_2.official_id, '1')

    def test_281_50_shouldnt_have_any_sequence_while_state_is_draft(self):
        form = self.create_form28150(ref_year=2020, state='draft')
        self.assertEqual(form.official_id, False)
        form_2 = self.create_form28150(ref_year=2020, state='draft')
        self.assertEqual(form_2.official_id, False)

    def test_281_50_in_test_mode_should_not_consume_sequence_number(self):
        test_form = self.create_form28150(ref_year=2020, test=True)
        self.assertEqual(test_form.official_id, '1')
        test_form_2 = self.create_form28150(ref_year=2020, test=False)
        self.assertEqual(test_form_2.official_id, '1')

    def test_281_50_partner_relation(self):
        """Ensure Many2one and One2many are working as expected"""
        form = self.create_form28150(ref_year=2020)
        self.assertEqual(self.partner_a.forms_281_50, form)
        form_2 = self.create_form28150(ref_year=2020, partner=self.partner_b)
        self.assertEqual(self.partner_b.forms_281_50, form_2)
        form_3 = self.create_form28150(ref_year=2020)

        self.assertEqual(len(self.partner_a.forms_281_50), 2)
        self.assertIn(form, self.partner_a.forms_281_50)
        self.assertIn(form_3, self.partner_a.forms_281_50)
        self.assertNotIn(form_2, self.partner_a.forms_281_50)

    def test_325_and_281_50_should_raise_error_when_unlink_and_state_is_generated(self):
        form = self.create_form28150(ref_year=2020)
        with self.assertRaises(UserError):
            form.form_325_id.unlink()
        with self.assertRaises(UserError):
            form.unlink()

    def test_delete_testing_325_and_281_50_should_succeed(self):
        # deletion from 325 form
        form = self.create_form28150(ref_year=2020, test=True)
        form.form_325_id.unlink()
        self.assertEqual(len(form.exists()), 0)
        # deletion from 281_50
        form_2 = self.create_form28150(ref_year=2020, test=True)
        form_2.unlink()

    def test_281_50_fields_should_remain_the_same_even_if_partner_info_changed(self):
        partner = self.partner_a
        form = self.create_form28150(ref_year=2020, commission=1000.0, fees=2000.0, atn=3000.0, exposed_expenses=4000.0, paid_amount=10000.0)

        self.assertRecordValues(form, [{
            'commissions': 1000.0,
            'fees': 2000.0,
            'atn': 3000.0,
            'exposed_expenses': 4000.0,
            'total_remuneration': 10000.0,
            'paid_amount': 10000.0,
        }])
        self.assertRecordValues(form, [{
            'partner_name': 'partner_a',
            'partner_address': 'Rue du Jacobet, 9',
            'partner_zip': '7100',
            'partner_city': 'La Louvière',
            'partner_job_position': '',
            'partner_citizen_identification': '',
            'partner_bce_number': '0475646428',
        }])
        partner.write({
            'street': 'changed',
            'zip': '6666',
            'city': 'woot',
        })
        self.assertRecordValues(form, [{
            'partner_name': 'partner_a',
            'partner_address': 'Rue du Jacobet, 9',
            'partner_zip': '7100',
            'partner_city': 'La Louvière',
            'partner_job_position': '',
            'partner_citizen_identification': '',
            'partner_bce_number': '0475646428',
        }])

    def test_281_50_should_know_partner_is_natural_person(self):
        self.partner_a.write({'is_company': False})
        form_325 = self.create_325_form(ref_year=2000)
        self.assertRecordValues(form_325.form_281_50_ids, [
                {
                    'partner_id': self.partner_a.id,
                    'partner_is_natural_person': True,
                }
        ])

    def test_325_form_should_update_data_when_generating(self):
        form_325 = self.create_325_form(state='draft', ref_year=2000)
        # Change values
        self.sender = form_325.sender_id = self.partner_b
        self.sender.write({'name': 'Brad'})
        self.debtor.write({'name': 'George'})
        self.assertRecordValues(form_325, [{
            'state': 'draft',
            'sender_name': 'Brad',
            'debtor_name': 'George',
        }])
        # Validate the form
        form_325._validate_form()
        self.sender.write({'name': 'Jean'})
        self.debtor.write({'name': 'Léon'})
        self.assertRecordValues(form_325, [{
            'state': 'generated',
            'sender_name': 'Brad',
            'debtor_name': 'George',
        }])

    def test_281_50_bill_with_4_lines_tagged_with_1_payment(self):
        """ This test should create a bill with 4 lines
            Each line has to have a tag (commission, atn, fee, exposed_expense)
            Generate one payment for the entire bill
        """
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_b.id,
            'invoice_date': fields.Date.from_string('2000-06-01'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [
                Command.create({
                    'name': f"{account_id.name} - Test invoice line",
                    'account_id': account_id.id,
                    'partner_id': self.partner_b.id,
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': [],
                })
                for account_id in self.create_tagged_accounts()
            ],
        })
        bill.action_post()
        self.pay_bill(bill, 4000.0, '2000-06-01')
        form_325 = self.create_325_form(ref_year=2000)
        self.assertRecordValues(form_325.form_281_50_ids.filtered(lambda x: x.partner_id.id == self.partner_b.id), [
            {
                'partner_id': self.partner_b.id,
                'commissions': 1000.0,
                'atn': 1000.0,
                'fees': 1000.0,
                'exposed_expenses': 1000.0,
                'total_remuneration': 4000.0,
                'paid_amount': 4000.0,
            }
        ])

    def test_281_50_bill_with_4_lines_tagged_with_multiple_payments(self):
        """ This test should create a bill with 4 lines
            Each line has to have a tag (commission, atn, fee, exposed_expense)
            Generate 6 payments for the bill
        """
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_b.id,
            'invoice_date': fields.Date.from_string('2000-06-01'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [
                Command.create({
                    'name': f"{account_id.name} - Test invoice line",
                    'account_id': account_id.id,
                    'partner_id': self.partner_b.id,
                    'quantity': 1.0,
                    'price_unit': 1500.0,
                    'tax_ids': [],
                })
                for account_id in self.create_tagged_accounts()
            ],
        })
        bill.action_post()
        payments = self.env['account.payment']
        for date in ['1995-06-01', '2000-07-02', '2000-08-03', '2001-06-04', '2001-07-05', '2001-08-06']:
            payments |= self.env['account.payment'].create({
                'payment_type': 'outbound',
                'amount': 1000.0,
                'currency_id': bill.currency_id.id,
                'journal_id': self.company_data['default_journal_bank'].id,
                'date': fields.Date.from_string(date),
                'partner_id': bill.partner_id.id,
                'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
                'partner_type': 'supplier',
            })

        payments.action_post()
        bill_payable_move_lines = bill.line_ids.filtered(lambda x: x.account_type == 'liability_payable')
        bill_payable_move_lines += payments.line_ids.filtered(lambda x: x.account_type == 'liability_payable')
        bill_payable_move_lines.reconcile()

        form_325 = self.create_325_form(ref_year=2000)
        self.assertRecordValues(form_325.form_281_50_ids.filtered(lambda x: x.partner_id.id == self.partner_b.id), [
            {
                'partner_id': self.partner_b.id,
                'commissions': 1500.0,
                'atn': 1500.0,
                'fees': 1500.0,
                'exposed_expenses': 1500.0,
                'total_remuneration': 6000.0,
                'paid_amount': 3000.0,
            }
        ])

    def test_281_50_bill_in_currency(self):
        foreign_currency = self.currency_data['currency']
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_b.id,
            'invoice_date': fields.Date.from_string('2018-06-01'),  # 2018 because first rate of gold coin is in 2017
            'currency_id': foreign_currency.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_b.id,
                    'account_id': self.product_b.property_account_expense_id.id,
                    'product_uom_id': self.product_b.uom_id.id,
                    'quantity': 1.0,
                    'discount': 0.0,
                    'price_unit': 1000.0,  # 1000 Gold coin -> 500 USD,
                    'tax_ids': [],
                }),
            ],
        })
        bill.action_post()
        self.pay_bill(bill, 1000, '2018-06-01', currency=foreign_currency)

        form_325 = self.create_325_form(ref_year=2018)
        form_281_50_from_form_325_ids = form_325.form_281_50_ids
        self.assertRecordValues(form_325.form_281_50_ids, [
            # pylint: disable=C0326
            {
                'partner_id': self.partner_b.id, 'commissions': 0.0, 'fees': 500.0, 'atn': 0.0, 'exposed_expenses': 0.0,
                'total_remuneration': 500.0, 'paid_amount': 500.0, 'partner_is_natural_person': False,
            },
        ])
        self.assertRecordValues(form_325, [{
            'form_281_50_total_amount': 500.0,
            'form_281_50_ids': form_281_50_from_form_325_ids.ids,
        }])

    def test_281_50_vendor_bill_and_credit_note_without_payment(self):
        """ Ensure form 281.50 handles correctly credit note in its computation """
        bill = self.create_and_post_bill(partner_id=self.partner_b, product_id=self.product_b, amount=1000.0, date='2000-05-12')

        credit_note = bill._reverse_moves([{'invoice_date': '2000-05-12'}])
        credit_note.action_post()

        form_325 = self.create_325_form(ref_year=2000)
        self.assertRecordValues(form_325.form_281_50_ids.filtered(lambda x: x.partner_id.id == self.partner_b.id), [
            {
                'partner_id': self.partner_b.id,
                'commissions': 0.0,
                'atn': 0.0,
                'fees': 0.0,
                'exposed_expenses': 0.0,
                'total_remuneration': 0.0,
                'paid_amount': 0.0,
            }
        ])

    def test_281_50_vendor_bill_and_credit_note_with_payment(self):
        """ Ensure form 281.50 handles correctly credit note and their payments in its computation """
        bill = self.create_and_post_bill(partner_id=self.partner_b, product_id=self.product_b, amount=1000.0, date='2000-05-12')
        self.pay_bill(bill=bill, amount=1000.0, date='2000-05-12')

        credit_note = bill._reverse_moves([{'invoice_date': '2000-05-12'}])
        credit_note.action_post()
        self.pay_bill(bill=credit_note, amount=-1000.0, date='2000-05-12')

        form_325 = self.create_325_form(ref_year=2000)
        self.assertRecordValues(form_325.form_281_50_ids.filtered(lambda x: x.partner_id.id == self.partner_b.id), [
            {
                'partner_id': self.partner_b.id,
                'commissions': 0.0,
                'atn': 0.0,
                'fees': 0.0,
                'exposed_expenses': 0.0,
                'total_remuneration': 0.0,
                'paid_amount': 0.0,
            }
        ])

    def test_281_50_positive_and_negative_line_should_compensate(self):
        """Ensure form 281.50 handles negative lines put on the same account"""
        partner_id = self.partner_b
        product_id = self.product_b
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner_id.id,
            'invoice_payment_term_id': False,
            'invoice_date': fields.Date.from_string('2000-05-12'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': product_id.id,
                    'account_id': product_id.property_account_expense_id.id,
                    'partner_id': partner_id.id,
                    'product_uom_id': product_id.uom_id.id,
                    'quantity': 1.0,
                    'discount': 0.0,
                    'price_unit': 1000,
                    'tax_ids': [],
                }),
                Command.create({
                    'product_id': product_id.id,
                    'account_id': product_id.property_account_expense_id.id,
                    'partner_id': partner_id.id,
                    'product_uom_id': product_id.uom_id.id,
                    'quantity': 1.0,
                    'discount': 0.0,
                    'price_unit': -100,
                    'tax_ids': [],
                }),
            ]
        })
        bill.action_post()
        self.pay_bill(bill=bill, amount=900.0, date='2000-05-12')

        form_325 = self.create_325_form(ref_year=2000)
        self.assertRecordValues(form_325.form_281_50_ids.filtered(lambda x: x.partner_id.id == self.partner_b.id), [
            {
                'partner_id': self.partner_b.id,
                'commissions': 0.0,
                'atn': 0.0,
                'fees': 900.0,
                'exposed_expenses': 0.0,
                'total_remuneration': 900.0,
                'paid_amount': 900.0,
            }
        ])
