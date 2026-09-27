import logging

from dateutil.relativedelta import relativedelta

from odoo import Command, fields, models
from odoo.addons.account.models.chart_template import template
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(template='it', model='res.partner', demo=True)
    def _l10n_it_get_partner_demo_data(self):
        return {
            'res_partner_it_b2b': {
                'name': 'Azienda IT B2B SRL',
                'is_company': True,
                'street': 'Via Roma 10',
                'zip': '00100',
                'city': 'Roma',
                'country_id': 'base.it',
                'phone': '+39061234567',
                'email': 'amministrazione@aziendait.com',
                'vat': 'IT01234560157',
                'property_payment_term_id': 'account.account_payment_term_30days',
                'property_supplier_payment_term_id': 'account.account_payment_term_30days',
            },
            'res_partner_it_b2c': {
                'name': 'Mario Rossi',
                'street': 'Via Milano 20',
                'zip': '20124',
                'city': 'Milano',
                'country_id': 'base.it',
                'phone': '+393331234567',
                'email': 'mario.rossi@email.it',
                'property_payment_term_id': 'account.account_payment_term_immediate',
                'property_supplier_payment_term_id': 'account.account_payment_term_immediate',
            },
            'res_partner_it_pa': {
                'name': 'Comune di Milano',
                'is_company': True,
                'street': 'Piazza della Scala 2',
                'zip': '20121',
                'city': 'Milano',
                'country_id': 'base.it',
                'phone': '+390288451',
                'email': 'protocollo@pec.comune.milano.it',
                'vat': 'IT01199250158',
                'property_payment_term_id': 'account.account_payment_term_30days',
                'property_supplier_payment_term_id': 'account.account_payment_term_30days',
            },
            'res_partner_eu_b2b': {
                'name': 'EU Company GmbH',
                'is_company': True,
                'street': 'Friedrichstrasse 100',
                'zip': '10117',
                'city': 'Berlin',
                'country_id': 'base.de',
                'phone': '+4930123456',
                'email': 'billing@eucompany.de',
                'vat': 'DE791515202',
                'property_payment_term_id': 'account.account_payment_term_30days',
                'property_supplier_payment_term_id': 'account.account_payment_term_30days',
            },
            'res_partner_eu_b2c': {
                'name': 'Hans Schmidt',
                'is_company': False,
                'street': 'Hauptstrasse 1',
                'zip': '10115',
                'city': 'Berlin',
                'country_id': 'base.de',
                'phone': '+491511234567',
                'email': 'hans.schmidt@email.de',
                'property_payment_term_id': 'account.account_payment_term_immediate',
                'property_supplier_payment_term_id': 'account.account_payment_term_immediate',
            },
            'res_partner_extraeu_b2b': {
                'name': 'US Corp Inc.',
                'is_company': True,
                'street': '123 Broadway',
                'zip': '10001',
                'city': 'New York',
                'country_id': 'base.us',
                'phone': '+12125550199',
                'email': 'accounts@uscorp.com',
                'property_payment_term_id': 'account.account_payment_term_30days',
                'property_supplier_payment_term_id': 'account.account_payment_term_30days',
            },
        }

    @template(template='it', model='account.move', demo=True)
    def _l10n_it_get_demo_data_move(self):
        def create_move_lines(lines_vals):
            return [
                Command.create({
                    'name': name,
                    'quantity': quantity,
                    'price_unit': price_unit,
                    'tax_ids': self.ref(tax_xmlid_suffix),
                })
                for name, quantity, price_unit, tax_xmlid_suffix in lines_vals
            ]

        company_id = self.env.company.id
        today = fields.Date.today()

        return {
            'demo_inv_sale_multi_01': {
                'company_id': company_id,
                'move_type': 'out_invoice',
                'partner_id': 'res_partner_it_b2b',
                'invoice_date': today - relativedelta(day=18),
                'invoice_line_ids': create_move_lines([
                    ('Server Dell PowerEdge', 2, 1200.00, '22v'),
                    ('Installazione e cablaggio', 1, 450.00, '10v'),
                    ('Corso di formazione personale', 1, 300.00, '00v'),
                ]),
            },
            'demo_inv_sale_pa_02': {
                'company_id': company_id,
                'move_type': 'out_invoice',
                'partner_id': 'res_partner_it_pa',
                'invoice_date': today - relativedelta(day=10),
                'invoice_line_ids': create_move_lines([
                    ('Sviluppo Portale Web Cittadino', 1, 4500.00, '22vsp_group'),
                    ('Canone manutenzione annuale', 1, 1200.00, '22vsp_group'),
                ]),
            },
            'demo_inv_sale_eu_rc_03': {
                'company_id': company_id,
                'move_type': 'out_invoice',
                'partner_id': 'res_partner_eu_b2b',
                'invoice_date': today - relativedelta(day=1),
                'invoice_line_ids': create_move_lines([
                    ('Servizi di Marketing (Reverse Charge UE)', 1, 2500.00, '00eus'),
                    ('Rimborso spese di trasferta', 1, 350.00, '00art15v'),
                ]),
            },
            'demo_inv_sale_extraeu_04': {
                'company_id': company_id,
                'move_type': 'out_invoice',
                'partner_id': 'res_partner_extraeu_b2b',
                'invoice_date': today - relativedelta(day=5),
                'invoice_line_ids': create_move_lines([
                    ('Licenza Software Enterprise', 5, 1000.00, '00ex'),
                ]),
            },
            'demo_inv_sale_it_rc_05': {
                'company_id': company_id,
                'move_type': 'out_invoice',
                'partner_id': 'res_partner_it_b2b',
                'invoice_date': today - relativedelta(day=20),
                'invoice_line_ids': create_move_lines([
                    ('Servizi in appalto (Reverse Charge Interno)', 1, 800.00, '0rc_n67'),
                ]),
            },
            'demo_inv_sale_b2c_06': {
                'company_id': company_id,
                'move_type': 'out_invoice',
                'partner_id': 'res_partner_it_b2c',
                'invoice_date': today - relativedelta(day=15),
                'invoice_line_ids': create_move_lines([
                    ('Riparazione Notebook', 1, 150.00, '22v'),
                ]),
            },
            'demo_inv_purch_01': {
                'company_id': company_id,
                'move_type': 'in_invoice',
                'partner_id': 'res_partner_it_b2b',
                'invoice_date': today - relativedelta(day=2),
                'invoice_line_ids': create_move_lines([
                    ('Acquisto Server (Beni)', 2, 1200.00, '22am'),
                ]),
            },
            'demo_inv_purch_02': {
                'company_id': company_id,
                'move_type': 'in_invoice',
                'partner_id': 'res_partner_it_b2b',
                'invoice_date': today - relativedelta(day=7),
                'invoice_line_ids': create_move_lines([
                    ('Consulenza sistemistica (Servizi)', 1, 500.00, '22as'),
                ]),
            },
            'demo_inv_purch_03': {
                'company_id': company_id,
                'move_type': 'in_invoice',
                'partner_id': 'res_partner_eu_b2b',
                'invoice_date': today - relativedelta(day=20),
                'invoice_line_ids': create_move_lines([
                    ('Hosting mensile AWS (Intra-UE)', 1, 120.00, '22rcs'),
                ]),
            },
            'demo_inv_purch_04': {
                'company_id': company_id,
                'move_type': 'in_invoice',
                'partner_id': 'res_partner_extraeu_b2b',
                'invoice_date': today - relativedelta(day=3),
                'invoice_line_ids': create_move_lines([
                    ('Licenze Software (Extra-UE)', 5, 200.00, '22rcs'),
                ]),
            },
            'demo_inv_purch_05': {
                'company_id': company_id,
                'move_type': 'in_invoice',
                'partner_id': 'res_partner_it_b2b',
                'invoice_date': today - relativedelta(day=15),
                'invoice_line_ids': create_move_lines([
                    ('Acquisto Componenti Elettronici (RC Interno)', 50, 15.00, '4rcm'),
                ]),
            },
        }

    def _post_load_demo_data(self, template_code):
        super()._post_load_demo_data(template_code)
        if template_code != 'it':
            return

        bank_data = [
            ('res_partner_it_b2b', 'IT62P0300203280491121199673'),
            ('res_partner_it_b2c', 'IT40H0300203280131617863276'),
            ('res_partner_it_pa', 'IT28K0300203280151118269669'),
            ('res_partner_eu_b2b', 'DE22500105171521155351'),
            ('res_partner_extraeu_b2b', '5790765029392936'),
        ]
        for partner_xmlid, account_number in bank_data:
            partner = self.ref(partner_xmlid, raise_if_not_found=False)
            if partner:
                self.env['res.partner.bank'].create({
                    'partner_id': partner.id,
                    'account_number': account_number,
                    'company_id': self.env.company.id,
                })

        moves = (
            self.ref('demo_inv_sale_multi_01')
            + self.ref('demo_inv_sale_pa_02')
            + self.ref('demo_inv_sale_eu_rc_03')
            + self.ref('demo_inv_sale_extraeu_04')
            + self.ref('demo_inv_sale_it_rc_05')
            + self.ref('demo_inv_sale_b2c_06')
            + self.ref('demo_inv_purch_01')
            + self.ref('demo_inv_purch_02')
            + self.ref('demo_inv_purch_03')
            + self.ref('demo_inv_purch_04')
            + self.ref('demo_inv_purch_05')
        )
        for move in moves:
            try:
                move.action_post()
            except (UserError, ValidationError):
                _logger.exception('Error while posting demo data')
