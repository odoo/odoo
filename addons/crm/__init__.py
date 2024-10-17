# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from .models.calendar import CalendarEvent
from .models.crm_lead import CrmLead
from .models.crm_lead_scoring_frequency import (
    CrmLeadScoringFrequency,
    CrmLeadScoringFrequencyField,
)
from .models.crm_lost_reason import CrmLostReason
from .models.crm_recurring_plan import CrmRecurringPlan
from .models.crm_stage import CrmStage
from .models.crm_team import CrmTeam
from .models.crm_team_member import CrmTeamMember
from .models.digest import DigestDigest
from .models.ir_config_parameter import IrConfig_Parameter
from .models.mail_activity import MailActivity
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
from .models.utm import UtmCampaign
from .report.crm_activity_report import CrmActivityReport
from .wizard.crm_lead_lost import CrmLeadLost
from .wizard.crm_lead_pls_update import CrmLeadPlsUpdate
from .wizard.crm_lead_to_opportunity import CrmLead2opportunityPartner
from .wizard.crm_lead_to_opportunity_mass import CrmLead2opportunityPartnerMass
from .wizard.crm_merge_opportunities import CrmMergeOpportunity
