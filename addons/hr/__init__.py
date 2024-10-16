# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    Base, DiscussChannel, HrContractType, HrDepartment, HrDepartureReason,
    HrEmployee, HrEmployeeBase, HrEmployeeCategory, HrEmployeePublic, HrJob, HrWorkLocation,
    IrUiMenu, MailActivityPlan, MailActivityPlanTemplate, MailAlias, ResCompany,
    ResConfigSettings, ResPartner, ResUsers, ResourceResource,
)
from .wizard import HrDepartureWizard, MailActivitySchedule
from .report import HrManagerDepartmentReport


def _install_hr_localization(env):
    if env["res.company"].search_count([('partner_id.country_id.code', '=', 'MX')], limit=1):
        l10n_mx = env['ir.module.module'].sudo().search([
            ('name', '=', 'l10n_mx_hr'),
            ('state', 'not in', ['installed', 'to install', 'to upgrade']),
        ])
        if l10n_mx:
            l10n_mx.button_install()
