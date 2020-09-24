# -*- coding: utf-8 -*-

from contextlib import contextmanager
from functools import partial
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.iap.tools import iap_tools
from odoo.addons.crm_iap_lead_enrich.models.iap_enrich_api import IapEnrichAPI
from odoo.tests import common


class MockIAPEnrich(common.BaseCase):

    @contextmanager
    def mockIAPEnrichGateway(self, default_data=None, email_data=None, sim_error=None, failing_emails=None):

        def _contact_iap(local_endpoint, params):
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
            # mock single sms sending
            if local_endpoint == '/iap/clearbit/1/lead_enrichment_email':
                result = {}
                for lead_id, email in params['domains'].items():
                    if sim_error and sim_error == 'credit':
                        raise iap_tools.InsufficientCreditError('InsufficientCreditError')
                    elif sim_error and sim_error == 'jsonrpc_exception':
                        raise exceptions.AccessError(
                            'The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was ' + local_endpoint
                        )
                    result[str(lead_id)] = dict(sim_result)
                    if email_data and email_data.get(email):
                        result[str(lead_id)].update(email_data[email])
                return result

        try:
            with patch.object(IapEnrichAPI, '_contact_iap', side_effect=_contact_iap) as contact_iap_mock:
                yield
        finally:
            pass
