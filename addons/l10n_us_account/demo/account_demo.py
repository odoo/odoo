# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import time

from odoo import Command, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _l10n_us_demo_tax_values(self, name, amount, tax_group, state, **values):
        """ Return the values of a US sale tax, reported under its own jurisdiction. """
        def repartition_lines():
            return [
                Command.create({'repartition_type': 'base'}),
                Command.create({'repartition_type': 'tax', 'account_id': 'account_account_us_tax_received'}),
            ]

        return {
            'name': name,
            'amount': amount,
            'type_tax_use': 'sale',
            'tax_group_id': tax_group,
            'l10n_us_jurisdiction_type': 'state',
            'l10n_us_state_id': state,
            'invoice_repartition_line_ids': repartition_lines(),
            'refund_repartition_line_ids': repartition_lines(),
            **values,
        }

    @template('us', model='account.tax.group', demo=True)
    def _get_us_demo_account_tax_group(self):
        return {
            'account_tax_group_us_demo_4_25': {
                'name': "Tax 4.25%",
                'country_id': 'base.us',
                'tax_payable_account_id': 'account_account_us_tax_payable',
                'tax_receivable_account_id': 'account_account_us_tax_receivable',
            },
        }

    @template('us', model='account.tax', demo=True)
    def _get_us_demo_account_tax(self):
        return {
            'account_tax_us_demo_ca_state': self._l10n_us_demo_tax_values(
                "CA State 6%", 6.0, 'account_tax_group_us_6', state='base.state_us_5',
            ),
            'account_tax_us_demo_ca_alameda': self._l10n_us_demo_tax_values(
                "CA Alameda County 4.25%", 4.25, 'account_tax_group_us_demo_4_25', state='base.state_us_5',
                l10n_us_jurisdiction_type='county',
                l10n_us_county_id='l10n_us.county_us_06001',
            ),
            'account_tax_us_demo_ca_exempt': self._l10n_us_demo_tax_values(
                "CA State 6% Exempt", 0.0, 'account_tax_group_us_0', state='base.state_us_5',
                l10n_us_exempt_parent_tax_id='account_tax_us_demo_ca_state',
            ),
            'account_tax_us_demo_ca_nontaxable': self._l10n_us_demo_tax_values(
                "CA State 6% Non-Taxable", 0.0, 'account_tax_group_us_0', state='base.state_us_5',
                l10n_us_nontaxable_parent_tax_id='account_tax_us_demo_ca_state',
            ),
            'account_tax_us_demo_ca_reduced': self._l10n_us_demo_tax_values(
                "CA State 6% reduced to 4%", 4.0, 'account_tax_group_us_4', state='base.state_us_5',
                l10n_us_nontaxable_parent_tax_id='account_tax_us_demo_ca_state',
            ),
            'account_tax_us_demo_tx_state': self._l10n_us_demo_tax_values(
                "TX State 6.25%", 6.25, 'account_tax_group_us_6_25', state='base.state_us_44',
            ),
            'account_tax_us_demo_tx_exempt': self._l10n_us_demo_tax_values(
                "TX State 6.25% Exempt", 0.0, 'account_tax_group_us_0', state='base.state_us_44',
                l10n_us_exempt_parent_tax_id='account_tax_us_demo_tx_state',
            ),
        }

    @template('us', model='res.partner', demo=True)
    def _get_us_demo_res_partner(self):
        return {
            'partner_demo_us_tx': {
                'name': "Lone Star Furnishings",
                'is_company': True,
                'street': "2200 Barton Springs Rd",
                'city': "Austin",
                'state_id': 'base.state_us_44',
                'zip': '78704',
                'country_id': 'base.us',
                'phone': '+1 555-555-0142',
                'email': 'contact@lone-star-furnishings.example.com',
            },
        }

    @template('us', model='account.move', demo=True)
    def _get_us_demo_account_move(self):
        return {
            self.company_xmlid('demo_invoice_us_tax'): {
                'move_type': 'out_invoice',
                'partner_id': 'base.res_partner_12',
                'invoice_user_id': 'base.user_admin',
                'invoice_date': time.strftime('%Y-%m-01'),
                'delivery_date': time.strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({
                        'name': "Taxable sale",
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set([
                            'account_tax_us_demo_ca_state',
                            'account_tax_us_demo_ca_alameda',
                        ])],
                    }),
                    Command.create({
                        'name': "Exempt sale, resale certificate on file",
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(['account_tax_us_demo_ca_exempt'])],
                    }),
                    Command.create({
                        'name': "Non-taxable sale, grocery food",
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(['account_tax_us_demo_ca_nontaxable'])],
                    }),
                    Command.create({
                        'name': "Manufacturing equipment, taxed at the reduced rate",
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(['account_tax_us_demo_ca_reduced'])],
                    }),
                ],
            },
            self.company_xmlid('demo_invoice_us_tax_tx'): {
                'move_type': 'out_invoice',
                'partner_id': 'partner_demo_us_tx',
                'invoice_user_id': 'base.user_admin',
                'invoice_date': time.strftime('%Y-%m-01'),
                'delivery_date': time.strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({
                        'name': "Taxable sale",
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(['account_tax_us_demo_tx_state'])],
                    }),
                    Command.create({
                        'name': "Exempt sale, resale certificate on file",
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(['account_tax_us_demo_tx_exempt'])],
                    }),
                ],
            },
        }

    def _post_load_demo_data(self, template_code):
        super()._post_load_demo_data(template_code)
        for xmlid in ('demo_invoice_us_tax', 'demo_invoice_us_tax_tx'):
            invoice = self.ref(xmlid, raise_if_not_found=False)
            if not invoice:
                continue
            try:
                invoice.action_post()
            except (UserError, ValidationError):
                _logger.exception('Error while posting US demo data')
