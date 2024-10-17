# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from .models.avatar_mixin import AvatarMixin
from .models.decimal_precision import DecimalPrecision
from .models.image_mixin import ImageMixin
from .models.ir_actions import (
    IrActionsAct_Url, IrActionsAct_Window, IrActionsAct_WindowView,
    IrActionsAct_Window_Close, IrActionsActions, IrActionsClient, IrActionsServer,
    IrActionsTodo,
)
from .models.ir_actions_report import IrActionsReport
from .models.ir_asset import IrAsset
from .models.ir_attachment import IrAttachment
from .models.ir_autovacuum import IrAutovacuum
from .models.ir_binary import IrBinary
from .models.ir_config_parameter import IrConfig_Parameter
from .models.ir_cron import IrCron, IrCronProgress, IrCronTrigger
from .models.ir_default import IrDefault
from .models.ir_demo import IrDemo
from .models.ir_demo_failure import IrDemo_Failure, IrDemo_FailureWizard
from .models.ir_embedded_actions import IrEmbeddedActions
from .models.ir_exports import IrExports, IrExportsLine
from .models.ir_fields import IrFieldsConverter
from .models.ir_filters import IrFilters
from .models.ir_http import IrHttp
from .models.ir_logging import IrLogging
from .models.ir_mail_server import IrMail_Server
from .models.ir_model import (
    IrModel, IrModelAccess, IrModelConstraint, IrModelData,
    IrModelFields, IrModelFieldsSelection, IrModelInherit, IrModelRelation,
    WizardIrModelMenuCreate,
)
from .models.ir_module import (
    IrModuleCategory, IrModuleModule, IrModuleModuleDependency,
    IrModuleModuleExclusion,
)
from .models.ir_profile import BaseEnableProfilingWizard, IrProfile
from .models.ir_qweb import IrQweb
from .models.ir_qweb_fields import (
    IrQwebField, IrQwebFieldBarcode, IrQwebFieldContact,
    IrQwebFieldDate, IrQwebFieldDatetime, IrQwebFieldDuration, IrQwebFieldFloat,
    IrQwebFieldFloat_Time, IrQwebFieldHtml, IrQwebFieldImage, IrQwebFieldImage_Url,
    IrQwebFieldInteger, IrQwebFieldMany2many, IrQwebFieldMany2one, IrQwebFieldMonetary,
    IrQwebFieldQweb, IrQwebFieldRelative, IrQwebFieldSelection, IrQwebFieldText,
    IrQwebFieldTime,
)
from .models.ir_rule import IrRule
from .models.ir_sequence import IrSequence, IrSequenceDate_Range
from .models.ir_ui_menu import IrUiMenu
from .models.ir_ui_view import Base, IrUiView, IrUiViewCustom, ResetViewArchWizard
from .models.report_layout import ReportLayout
from .models.report_paperformat import ReportPaperformat
from .models.res_bank import ResBank, ResPartnerBank
from .models.res_company import ResCompany
from .models.res_config import ResConfig, ResConfigSettings
from .models.res_country import ResCountry, ResCountryGroup, ResCountryState
from .models.res_currency import ResCurrency, ResCurrencyRate
from .models.res_device import ResDevice, ResDeviceLog
from .models.res_lang import ResLang
from .models.res_partner import (
    FormatAddressMixin, FormatVatLabelMixin, ResPartner,
    ResPartnerCategory, ResPartnerIndustry, ResPartnerTitle,
)
from .models.res_users import (
    ChangePasswordOwn, ChangePasswordUser, ChangePasswordWizard,
    ResGroups, ResUsers, ResUsersApikeys, ResUsersApikeysDescription, ResUsersApikeysShow,
    ResUsersIdentitycheck, ResUsersLog,
)
from .models.res_users_deletion import ResUsersDeletion
from .models.res_users_settings import ResUsersSettings
from .report.report_base_report_irmodulereference import ReportBaseReport_Irmodulereference
from .wizard.base_export_language import BaseLanguageExport
from .wizard.base_import_language import BaseLanguageImport
from .wizard.base_language_install import BaseLanguageInstall
from .wizard.base_module_uninstall import BaseModuleUninstall
from .wizard.base_module_update import BaseModuleUpdate
from .wizard.base_module_upgrade import BaseModuleUpgrade
from .wizard.base_partner_merge import BasePartnerMergeAutomaticWizard, BasePartnerMergeLine


def post_init(env):
    """Rewrite ICP's to force groups"""
    env['ir.config_parameter'].init(force=True)
