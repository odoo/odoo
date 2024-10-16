# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    AvatarMixin, Base, BaseEnableProfilingWizard, ChangePasswordOwn,
    ChangePasswordUser, ChangePasswordWizard, DecimalPrecision, FormatAddressMixin,
    FormatVatLabelMixin, ImageMixin, IrActionsAct_Url, IrActionsAct_Window,
    IrActionsAct_WindowView, IrActionsAct_Window_Close, IrActionsActions, IrActionsClient,
    IrActionsReport, IrActionsServer, IrActionsTodo, IrAsset, IrAttachment, IrAutovacuum,
    IrBinary, IrConfig_Parameter, IrCron, IrCronProgress, IrCronTrigger, IrDefault, IrDemo,
    IrDemo_Failure, IrDemo_FailureWizard, IrEmbeddedActions, IrExports, IrExportsLine,
    IrFieldsConverter, IrFilters, IrHttp, IrLogging, IrMail_Server, IrModel, IrModelAccess,
    IrModelConstraint, IrModelData, IrModelFields, IrModelFieldsSelection, IrModelInherit,
    IrModelRelation, IrModuleCategory, IrModuleModule, IrModuleModuleDependency,
    IrModuleModuleExclusion, IrProfile, IrQweb, IrQwebField, IrQwebFieldBarcode,
    IrQwebFieldContact, IrQwebFieldDate, IrQwebFieldDatetime, IrQwebFieldDuration,
    IrQwebFieldFloat, IrQwebFieldFloat_Time, IrQwebFieldHtml, IrQwebFieldImage,
    IrQwebFieldImage_Url, IrQwebFieldInteger, IrQwebFieldMany2many, IrQwebFieldMany2one,
    IrQwebFieldMonetary, IrQwebFieldQweb, IrQwebFieldRelative, IrQwebFieldSelection,
    IrQwebFieldText, IrQwebFieldTime, IrRule, IrSequence, IrSequenceDate_Range, IrUiMenu,
    IrUiView, IrUiViewCustom, ReportLayout, ReportPaperformat, ResBank, ResCompany, ResConfig,
    ResConfigSettings, ResCountry, ResCountryGroup, ResCountryState, ResCurrency, ResCurrencyRate,
    ResDevice, ResDeviceLog, ResGroups, ResLang, ResPartner, ResPartnerBank, ResPartnerCategory,
    ResPartnerIndustry, ResPartnerTitle, ResUsers, ResUsersApikeys, ResUsersApikeysDescription,
    ResUsersApikeysShow, ResUsersDeletion, ResUsersIdentitycheck, ResUsersLog, ResUsersSettings,
    ResetViewArchWizard, WizardIrModelMenuCreate,
)
from . import report
from .wizard import (
    BaseLanguageExport, BaseLanguageImport, BaseLanguageInstall,
    BaseModuleUninstall, BaseModuleUpdate, BaseModuleUpgrade, BasePartnerMergeAutomaticWizard,
    BasePartnerMergeLine,
)


def post_init(env):
    """Rewrite ICP's to force groups"""
    env['ir.config_parameter'].init(force=True)
