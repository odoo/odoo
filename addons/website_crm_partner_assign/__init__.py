# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from .models.crm_lead import CrmLead
from .models.res_partner import ResPartner
from .models.res_partner_activation import ResPartnerActivation
from .models.res_partner_grade import ResPartnerGrade
from .models.website import Website
from .report.crm_partner_report import CrmPartnerReportAssign
from .wizard.crm_forward_to_partner import CrmLeadAssignation, CrmLeadForwardToPartner
