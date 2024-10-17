# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.calendar import CalendarEvent
from .models.digest import DigestDigest
from .models.hr_applicant import HrApplicant
from .models.hr_applicant_category import HrApplicantCategory
from .models.hr_applicant_refuse_reason import HrApplicantRefuseReason
from .models.hr_candidate import HrCandidate
from .models.hr_department import HrDepartment
from .models.hr_employee import HrEmployee
from .models.hr_job import HrJob
from .models.hr_job_platform import HrJobPlatform
from .models.hr_recruitment_degree import HrRecruitmentDegree
from .models.hr_recruitment_source import HrRecruitmentSource
from .models.hr_recruitment_stage import HrRecruitmentStage
from .models.ir_ui_menu import IrUiMenu
from .models.mail_activity_plan import MailActivityPlan
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_users import ResUsers
from .models.utm_campaign import UtmCampaign
from .models.utm_source import UtmSource
from .wizard.applicant_refuse_reason import ApplicantGetRefuseReason
from .wizard.applicant_send_mail import ApplicantSendMail
from .wizard.candidate_send_mail import CandidateSendMail
from .wizard.mail_activity_schedule import MailActivitySchedule
