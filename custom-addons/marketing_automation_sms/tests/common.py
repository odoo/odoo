# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.marketing_automation.tests.common import MarketingAutomationCase, MarketingAutomationCommon
from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon


class MarketingAutomationSMSCase(MarketingAutomationCase, MassSMSCommon):

    def assertMarketAutoTraces(self, participants_info, activity, **trace_values):
        super().assertMarketAutoTraces(participants_info, activity, **trace_values)
        for info in participants_info:
            if info.get('trace_status'):
                if activity.mass_mailing_id.mailing_type == 'sms':
                    self.assertSMSTraces(
                        [{
                            'partner': record.customer_id,  # TDE FIXME: make it generic
                            'number': record.phone_sanitized,  # TDE FIXME: make it generic
                            'failure_type': info.get('failure_type', False),
                            'trace_status': info['trace_status'],
                            'record': record,
                            'content': info.get('trace_content')
                         } for record in info['records']
                        ],
                        activity.mass_mailing_id,
                        info['records'],
                        sent_unlink=True,
                    )

class MarketingAutomationSMSCommon(MarketingAutomationCommon, MarketingAutomationSMSCase):
    pass
