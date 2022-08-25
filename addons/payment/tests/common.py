# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from unittest.mock import patch

from lxml import objectify

from odoo.fields import Command
from odoo.tools.misc import hmac as hmac_tool

from odoo.addons.account.models.account_payment_method import AccountPaymentMethod
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_logger = logging.getLogger(__name__)


class PaymentCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        Method_get_payment_method_information = AccountPaymentMethod._get_payment_method_information

        def _get_payment_method_information(self):
            res = Method_get_payment_method_information(self)
            res['none'] = {'mode': 'multi', 'domain': [('type', '=', 'bank')]}
            return res

        cls.currency_euro = cls._prepare_currency('EUR')
        cls.currency_usd = cls._prepare_currency('USD')

        cls.country_belgium = cls.env.ref('base.be')
        cls.country_france = cls.env.ref('base.fr')
        cls.europe = cls.env.ref('base.europe')

        cls.group_user = cls.env.ref('base.group_user')
        cls.group_portal = cls.env.ref('base.group_portal')
        cls.group_public = cls.env.ref('base.group_public')

        cls.admin_user = cls.env.ref('base.user_admin')
        cls.internal_user = cls.env['res.users'].create({
            'name': 'Internal User (Test)',
            'login': 'internal',
            'password': 'internal',
            'groups_id': [Command.link(cls.group_user.id)]
        })
        cls.portal_user = cls.env['res.users'].create({
            'name': 'Portal User (Test)',
            'login': 'payment_portal',
            'password': 'payment_portal',
            'groups_id': [Command.link(cls.group_portal.id)]
        })
        cls.public_user = cls.env.ref('base.public_user')

        cls.admin_partner = cls.admin_user.partner_id
        cls.internal_partner = cls.internal_user.partner_id
        cls.portal_partner = cls.portal_user.partner_id
        cls.default_partner = cls.env['res.partner'].create({
            'name': 'Norbert Buyer',
            'lang': 'en_US',
            'email': 'norbert.buyer@example.com',
            'street': 'Huge Street',
            'street2': '2/543',
            'phone': '0032 12 34 56 78',
            'city': 'Sin City',
            'zip': '1000',
            'country_id': cls.country_belgium.id,
        })

        # Create a dummy acquirer to allow basic tests without any specific acquirer implementation
        arch = """
        <form action="dummy" method="post">
            <input type="hidden" name="view_id" t-att-value="viewid"/>
            <input type="hidden" name="user_id" t-att-value="user_id.id"/>
        </form>
        """  # We exploit the default values `viewid` and `user_id` from QWeb's rendering context
        redirect_form = cls.env['ir.ui.view'].create({
            'name': "Dummy Redirect Form",
            'type': 'qweb',
            'arch': arch,
        })

        with patch.object(AccountPaymentMethod, '_get_payment_method_information', _get_payment_method_information):
            cls.env['account.payment.method'].create({
                'name': 'Dummy method',
                'code': 'none',
                'payment_type': 'inbound'
            })
        cls.dummy_acquirer = cls.env['payment.acquirer'].create({
            'name': "Dummy Acquirer",
            'provider': 'none',
            'state': 'test',
            'is_published': True,
            'allow_tokenization': True,
            'redirect_form_view_id': redirect_form.id,
            'journal_id': cls.company_data['default_journal_bank'].id,
        })

        cls.acquirer = cls.dummy_acquirer
        cls.amount = 1111.11
        cls.company = cls.env.company
        cls.company_id = cls.company.id
        cls.currency = cls.currency_euro
        cls.partner = cls.default_partner
        cls.reference = "Test Transaction"
        cls.account = cls.company.account_journal_payment_credit_account_id
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'account_id': cls.account.id,
                    'currency_id': cls.currency_euro.id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                (0, 0, {
                    'account_id': cls.account.id,
                    'currency_id': cls.currency_euro.id,
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -200.0,
                }),
            ],
        })

    #=== Utils ===#

    @classmethod
    def _prepare_currency(cls, currency_code):
        currency = cls.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', currency_code.upper())]
        )
        currency.action_unarchive()
        return currency

    @classmethod
    def _prepare_acquirer(cls, provider='none', company=None, update_values=None):
        """ Prepare and return the first acquirer matching the given provider and company.

        If no acquirer is found in the given company, we duplicate the one from the base company.

        All other acquirers belonging to the same company are disabled to avoid any interferences.

        :param str provider: The provider of the acquirer to prepare
        :param recordset company: The company of the acquirer to prepare, as a `res.company` record
        :param dict update_values: The values used to update the acquirer
        :return: The acquirer to prepare, if found
        :rtype: recordset of `payment.acquirer`
        """
        company = company or cls.env.company
        update_values = update_values or {}

        acquirer = cls.env['payment.acquirer'].sudo().search(
            [('provider', '=', provider), ('company_id', '=', company.id)], limit=1
        )
        if not acquirer:
            base_acquirer = cls.env['payment.acquirer'].sudo().search(
                [('provider', '=', provider)], limit=1
            )
            if not base_acquirer:
                _logger.error("no payment.acquirer found for provider %s", provider)
                return cls.env['payment.acquirer']
            else:
                acquirer = base_acquirer.copy({'company_id': company.id})

        acquirer.write(update_values)
        if not acquirer.journal_id:
            acquirer.journal_id = cls.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'bank')
            ], limit=1)
        acquirer.state = 'test'
        return acquirer

    def _create_transaction(self, flow, sudo=True, **values):
        default_values = {
            'amount': self.amount,
            'currency_id': self.currency.id,
            'acquirer_id': self.acquirer.id,
            'reference': self.reference,
            'operation': f'online_{flow}',
            'partner_id': self.partner.id,
        }
        return self.env['payment.transaction'].sudo(sudo).create(dict(default_values, **values))

    def _create_token(self, sudo=True, **values):
        default_values = {
            'payment_details': "1234",
            'acquirer_id': self.acquirer.id,
            'partner_id': self.partner.id,
            'acquirer_ref': "Acquirer Ref (TEST)",
            'active': True,
        }
        return self.env['payment.token'].sudo(sudo).create(dict(default_values, **values))

    def _get_tx(self, reference):
        return self.env['payment.transaction'].sudo().search([
            ('reference', '=', reference),
        ])

    def _prepare_transaction_values(self, payment_option_id, flow):
        """ Prepare the basic payment/transaction route values.

        :param int payment_option_id: The payment option handling the transaction, as a
                                      `payment.acquirer` id or a `payment.token` id
        :param str flow: The payment flow
        :return: The route values
        :rtype: dict
        """
        return {
            'amount': self.amount,
            'currency_id': self.currency.id,
            'partner_id': self.partner.id,
            'access_token': self._generate_test_access_token(
                self.partner.id, self.amount, self.currency.id
            ),
            'payment_option_id': payment_option_id,
            'reference_prefix': 'test',
            'tokenization_requested': True,
            'landing_route': 'Test',
            'is_validation': False,
            'invoice_id': self.invoice.id,
            'flow': flow,
        }

    def _generate_test_access_token(self, *values):
        """ Generate an access token based on the provided values for testing purposes.

        This methods returns a token identical to that generated by
        payment.utils.generate_access_token but uses the test class environment rather than the
        environment of odoo.http.request.

        See payment.utils.generate_access_token for additional details.

        :param list values: The values to use for the generation of the token
        :return: The generated access token
        :rtype: str
        """
        token_str = '|'.join(str(val) for val in values)
        access_token = hmac_tool(self.env(su=True), 'generate_access_token', token_str)
        return access_token

    def _extract_values_from_html_form(self, html_form):
        """ Extract the transaction rendering values from an HTML form.

        :param str html_form: The HTML form
        :return: The extracted information (action & inputs)
        :rtype: dict[str:str]
        """
        html_tree = objectify.fromstring(html_form)
        if hasattr(html_tree, 'input'):
            inputs = {input_.get('name'): input_.get('value') for input_ in html_tree.input}
        else:
            inputs = {}
        return {
            'action': html_tree.get('action'),
            'method': html_tree.get('method'),
            'inputs': inputs,
        }

    def _assert_does_not_raise(self, exception_class, func, *args, **kwargs):
        """ Fail if an exception of the provided class is raised when calling the function.

        If an exception of any other class is raised, it is caught and silently ignored.

        This method cannot be used with functions that make requests. Any exception raised in the
        scope of the new request will not be caught and will make the test fail.

        :param class exception_class: The class of the exception to monitor
        :param function fun: The function to call when monitoring for exceptions
        :param list args: The positional arguments passed as-is to the called function
        :param dict kwargs: The keyword arguments passed as-is to the called function
        :return: None
        """
        try:
            func(*args, **kwargs)
        except exception_class:
            self.fail(f"{func.__name__} should not raise error of class {exception_class.__name__}")
        except Exception:
            pass  # Any exception whose class is not monitored is caught and ignored
