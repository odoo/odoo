# -*- coding: utf-8 -*-

from contextlib import contextmanager
from functools import partial
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.iap.tools import iap_tools
from odoo.addons.iap_crm.models.iap_services import IapServices
from odoo.tests import common, new_test_user

crm_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


class MockIAPEnrich(common.BaseCase):

    @contextmanager
    def mockIAPEnrichGateway(self, default_data=None, email_data=None, sim_error=None, failing_emails=None):

        def _iap_request_enrich(domains):
            sim_result = {
                'name': 'Simulator INC',
                'location': 'Simulator Street',
                'city': 'SimCity',
                'postal_code': '9876',
                'country_code': 'BE',
                'clearbit_id': 'idontknow',
                'phone_numbers': ['+3269001122', '+32456001122'],
                'twitter': 'testtwitter',
                'facebook': 'testfacebook',
            }
            if default_data:
                sim_result.update(default_data)
            result = {}
            for lead_id, email in domains.items():
                if sim_error and sim_error == 'credit':
                    raise iap_tools.InsufficientCreditError('InsufficientCreditError')
                if sim_error and sim_error == 'jsonrpc_exception':
                    raise exceptions.AccessError(
                        'The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was <mock for test>'
                    )
                result[str(lead_id)] = dict(sim_result)
                if email_data and email_data.get(email):
                    result[str(lead_id)].update(email_data[email])
            return result

        try:
            with patch.object(IapServices, '_iap_request_enrich', side_effect=_iap_request_enrich) as iap_request_enrich_mock:
                yield
        finally:
            pass


class CrmCase(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(CrmCase, cls).setUpClass()

        cls.sales_manager = crm_new_test_user(
            cls.env, login='sales_manager', groups='base.group_user,sales_team.group_sale_manager',
            name='Martine SalesManager', email='"Martine SalesManager" <martine@example.com>')
