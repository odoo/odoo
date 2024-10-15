# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    CalendarEvent, CrmLead, CrmLeadScoringFrequency, CrmLeadScoringFrequencyField,
    CrmLostReason, CrmRecurringPlan, CrmStage, CrmTeam, CrmTeamMember, DigestDigest,
    IrConfig_Parameter, MailActivity, ResConfigSettings, ResPartner, ResUsers, UtmCampaign,
)
from .report import CrmActivityReport
from .wizard import (
    CrmLead2opportunityPartner, CrmLead2opportunityPartnerMass, CrmLeadLost,
    CrmLeadPlsUpdate, CrmMergeOpportunity,
)
