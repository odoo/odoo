# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import assetsbundle

from .ir_model import IrModelRelation, Base, IrModelInherit, IrModelFieldsSelection, IrModel, IrModelData, IrModelAccess, Unknown, WizardIrModelMenuCreate, IrModelConstraint, IrModelFields
from .ir_sequence import IrSequenceDateRange, IrSequence
from .ir_ui_menu import IrUiMenu
from .ir_ui_view import IrUiView, Base, ResetViewArchWizard, IrUiViewCustom
from .ir_asset import IrAsset
from .ir_actions import IrActionsActUrl, IrActionsTodo, IrActionsActWindow, IrActionsServer, IrActionsClient, IrActionsActions, IrActionsActWindowClose, IrActionsActWindowView
from .ir_embedded_actions import IrEmbeddedActions
from .ir_actions_report import IrActionsReport
from .ir_attachment import IrAttachment
from .ir_binary import IrBinary
from .ir_cron import IrCronProgress, IrCron, IrCronTrigger
from .ir_filters import IrFilters
from .ir_default import IrDefault
from .ir_exports import IrExportsLine, IrExports
from .ir_rule import IrRule
from .ir_config_parameter import IrConfigParameter
from .ir_autovacuum import IrAutovacuum
from .ir_mail_server import IrMailServer
from .ir_fields import IrFieldsConverter
from .ir_qweb import IrQweb
from .ir_qweb_fields import IrQwebFieldFloat, IrQwebFieldDatetime, IrQwebFieldDate, IrQwebFieldFloatTime, IrQwebField, IrQwebFieldRelative, IrQwebFieldContact, IrQwebFieldImageUrl, IrQwebFieldSelection, IrQwebFieldDuration, IrQwebFieldMonetary, IrQwebFieldTime, IrQwebFieldQweb, IrQwebFieldInteger, IrQwebFieldBarcode, IrQwebFieldHtml, IrQwebFieldText, IrQwebFieldMany2many, IrQwebFieldImage, IrQwebFieldMany2one
from .ir_http import IrHttp
from .ir_logging import IrLogging
from .ir_property import IrProperty
from .ir_module import IrModuleCategory, IrModuleModuleExclusion, IrModuleModuleDependency, IrModuleModule
from .ir_demo import IrDemo
from .ir_demo_failure import IrDemoFailureWizard, IrDemoFailure
from .report_layout import ReportLayout
from .report_paperformat import ReportPaperformat

from .ir_profile import IrProfile, BaseEnableProfilingWizard
from .image_mixin import ImageMixin
from .avatar_mixin import AvatarMixin

from .res_country import ResCountryState, ResCountryGroup, ResCountry
from .res_lang import ResLang
from .res_partner import FormatAddressMixin, ResPartner, ResPartnerTitle, ResPartnerCategory, ResPartnerIndustry, FormatVATLabelMixin
from .res_bank import ResPartnerBank, ResBank
from .res_config import ResConfig, ResConfigSettings
from .res_currency import ResCurrencyRate, ResCurrency
from .res_company import ResCompany
from .res_users import ResUsers, ResGroups, ResUsersApikeysShow, IrModuleCategory, ResUsersLog, ResUsersApikeys, ResUsersApikeysDescription, ChangePasswordUser, ChangePasswordWizard, ResUsersIdentitycheck, ResUsers, ChangePasswordOwn, ResGroups
from .res_users_settings import ResUsersSettings
from .res_users_deletion import ResUsersDeletion
from .res_device import ResDeviceLog, ResDevice

from .decimal_precision import DecimalPrecision
