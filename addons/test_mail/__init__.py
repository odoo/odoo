# -*- coding: utf-8 -*-

from . import data
from . import models

from .models.test_discuss_models import MailTestProperties
from .models.test_mail_corner_case_models import (
    MailPerformanceThread,
    MailPerformanceTracking, MailTestFieldType, MailTestLang, MailTestMultiCompany,
    MailTestMultiCompanyRead, MailTestMultiCompanyWithActivity, MailTestNothread,
    MailTestTrackAll, MailTestTrackAllM2m, MailTestTrackAllO2m, MailTestTrackCompute,
    MailTestTrackGroups, MailTestTrackMonetary, MailTestTrackSelection,
)
from .models.test_mail_models import (
    MailTestActivity, MailTestAliasOptional,
    MailTestComposerMixin, MailTestComposerSource, MailTestContainer, MailTestContainerMc,
    MailTestGateway, MailTestGatewayCompany, MailTestGatewayGroups,
    MailTestGatewayMainAttachment, MailTestMailTrackingDuration, MailTestSimple,
    MailTestSimpleMainAttachment, MailTestSimpleUnfollow, MailTestTicket, MailTestTicketEl,
    MailTestTicketMc, MailTestTrack,
)
from .models.test_mail_thread_models import MailTestCc
