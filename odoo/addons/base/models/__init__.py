# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import assetsbundle

from .ir_model import (
    Base, IrModel, IrModelAccess, IrModelConstraint, IrModelData, IrModelFields,
    IrModelFieldsSelection, IrModelInherit, IrModelRelation, WizardIrModelMenuCreate,
)
from .ir_sequence import IrSequence, IrSequenceDate_Range
from .ir_ui_menu import IrUiMenu
from .ir_ui_view import Base, IrUiView, IrUiViewCustom, ResetViewArchWizard
from .ir_asset import IrAsset
from .ir_actions import (
    IrActionsAct_Url, IrActionsAct_Window, IrActionsAct_WindowView,
    IrActionsAct_Window_Close, IrActionsActions, IrActionsClient, IrActionsServer, IrActionsTodo,
)
from .ir_embedded_actions import IrEmbeddedActions
from .ir_actions_report import IrActionsReport
from .ir_attachment import IrAttachment
from .ir_binary import IrBinary
from .ir_cron import IrCron, IrCronProgress, IrCronTrigger
from .ir_filters import IrFilters
from .ir_default import IrDefault
from .ir_exports import IrExports, IrExportsLine
from .ir_rule import IrRule
from .ir_config_parameter import IrConfig_Parameter
from .ir_autovacuum import IrAutovacuum
from .ir_mail_server import IrMail_Server
from .ir_fields import IrFieldsConverter
from .ir_qweb import IrQweb
from .ir_qweb_fields import (
    IrQwebField, IrQwebFieldBarcode, IrQwebFieldContact, IrQwebFieldDate,
    IrQwebFieldDatetime, IrQwebFieldDuration, IrQwebFieldFloat, IrQwebFieldFloat_Time,
    IrQwebFieldHtml, IrQwebFieldImage, IrQwebFieldImage_Url, IrQwebFieldInteger,
    IrQwebFieldMany2many, IrQwebFieldMany2one, IrQwebFieldMonetary, IrQwebFieldQweb,
    IrQwebFieldRelative, IrQwebFieldSelection, IrQwebFieldText, IrQwebFieldTime,
)
from .ir_http import IrHttp
from .ir_logging import IrLogging
from .ir_module import (
    IrModuleCategory, IrModuleModule, IrModuleModuleDependency,
    IrModuleModuleExclusion,
)
from .ir_demo import IrDemo
from .ir_demo_failure import IrDemo_Failure, IrDemo_FailureWizard
from .report_layout import ReportLayout
from .report_paperformat import ReportPaperformat

from .ir_profile import BaseEnableProfilingWizard, IrProfile
from .image_mixin import ImageMixin
from .avatar_mixin import AvatarMixin

from .res_country import ResCountry, ResCountryGroup, ResCountryState
from .res_lang import ResLang
from .res_partner import (
    FormatAddressMixin, FormatVatLabelMixin, ResPartner, ResPartnerCategory,
    ResPartnerIndustry, ResPartnerTitle,
)
from .res_bank import ResBank, ResPartnerBank
from .res_config import ResConfig, ResConfigSettings
from .res_currency import ResCurrency, ResCurrencyRate
from .res_company import ResCompany
from .res_users import (
    ChangePasswordOwn, ChangePasswordUser, ChangePasswordWizard, ResGroups,
    ResUsers, ResUsersApikeys, ResUsersApikeysDescription, ResUsersApikeysShow,
    ResUsersIdentitycheck, ResUsersLog,
)
from .res_users_settings import ResUsersSettings
from .res_users_deletion import ResUsersDeletion
from .res_device import ResDevice, ResDeviceLog

from .decimal_precision import DecimalPrecision
