# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .test_discuss_models import MailTestProperties
from .test_mail_corner_case_models import (
    MailPerformanceThread, MailPerformanceTracking,
    MailTestFieldType, MailTestLang, MailTestMultiCompany, MailTestMultiCompanyRead,
    MailTestMultiCompanyWithActivity, MailTestNothread, MailTestTrackAll, MailTestTrackAllM2m,
    MailTestTrackAllO2m, MailTestTrackCompute, MailTestTrackGroups, MailTestTrackMonetary,
    MailTestTrackSelection,
)
from .test_mail_models import (
    MailTestActivity, MailTestAliasOptional, MailTestComposerMixin,
    MailTestComposerSource, MailTestContainer, MailTestContainerMc, MailTestGateway,
    MailTestGatewayCompany, MailTestGatewayGroups, MailTestGatewayMainAttachment,
    MailTestMailTrackingDuration, MailTestSimple, MailTestSimpleMainAttachment,
    MailTestSimpleUnfollow, MailTestTicket, MailTestTicketEl, MailTestTicketMc, MailTestTrack,
)
from .test_mail_thread_models import MailTestCc
