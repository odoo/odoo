# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    CalendarEvent, DigestDigest, HrApplicant, HrApplicantCategory,
    HrApplicantRefuseReason, HrCandidate, HrDepartment, HrEmployee, HrJob, HrJobPlatform,
    HrRecruitmentDegree, HrRecruitmentSource, HrRecruitmentStage, IrUiMenu, MailActivityPlan,
    ResCompany, ResConfigSettings, ResUsers, UtmCampaign, UtmSource,
)
from .wizard import (
    ApplicantGetRefuseReason, ApplicantSendMail, CandidateSendMail,
    MailActivitySchedule,
)
