from contextlib import contextmanager
from unittest.mock import patch

from odoo.addons.l10n_co_dian.tests.common import TestCoDianCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class TestL10nCoEdiPosCommon(TestCoDianCommon, TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        cls.config = cls.basic_config
        cls.config.invoice_journal_id = cls.company_data['default_journal_sale']
        cls.config.l10n_co_edi_credit_note_journal_id = cls.company_data['default_journal_sale'].copy({
            'name': 'CO Credit Notes',
            'code': 'SETC',
        })
        cls.config.l10n_co_edi_final_consumer_invoices_journal_id = cls.company_data['default_journal_sale'].copy({
            'name': 'CO Final Consumer Invoices',
            'code': 'SETF',
        })
        cls.config.l10n_co_edi_final_consumer_invoices_journal_id.l10n_co_edi_pos_is_final_consumer = True

        cls.default_pos_payment_method = cls.config.payment_method_ids.filtered(lambda p: p.name == 'Card')[0]
        cls.default_pos_payment_option = cls.env.ref('l10n_co_edi.payment_option_2')
        cls.default_pos_payment_method.l10n_co_edi_pos_payment_option_id = cls.default_pos_payment_option

        cls.product_a.available_in_pos = True

    def _create_and_send_order(self, pos_order_ui_data, response_file_name, response_code=200):
        with (
            self._pos_session(),
            self._mock_get_status(),
            patch(f'{self.utils_path}._build_and_send_request', return_value=self._mocked_response(response_file_name, response_code)),
        ):
            return self._create_order(pos_order_ui_data)

    @contextmanager
    def _pos_session(self):
        session = self.open_new_session(0.0)
        yield session
        session.post_closing_cash_details(0.0)
        session.close_session_from_ui()

    def _create_order(self, ui_data, extra_data=None):
        order_data = self.create_ui_order_data(**ui_data)
        if extra_data:
            order_data |= extra_data
        results = self.env['pos.order'].sync_from_ui([order_data])
        return self.env['pos.order'].browse(results['pos.order'][0]['id'])

    @classmethod
    def _create_taxes(cls):
        # OVERRIDE TestPosCommon
        """
        The taxes created in the TestPosCommon implementation do not add
        the required field 'l10n_co_edi_type' to the taxes resulting in an error
        """
        return {}
