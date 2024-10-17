# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

import odoo
from odoo import api, SUPERUSER_ID
from odoo.http import request
from functools import partial

from .models.assets import Web_EditorAssets
from .models.base_partner_merge import BasePartnerMergeAutomaticWizard
from .models.ir_actions_server import IrActionsServer
from .models.ir_binary import IrBinary
from .models.ir_http import IrHttp
from .models.ir_model import Base
from .models.ir_model_data import IrModelData
from .models.ir_module_module import IrModuleModule
from .models.ir_qweb import IrQweb
from .models.ir_qweb_fields import IrQwebFieldContact, IrQwebFieldHtml
from .models.ir_rule import IrRule
from .models.ir_ui_menu import IrUiMenu
from .models.ir_ui_view import IrUiView
from .models.mixins import (
    WebsiteCover_PropertiesMixin, WebsiteMultiMixin,
    WebsitePublishedMixin, WebsiteSearchableMixin, WebsiteSeoMetadata,
)
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_lang import ResLang
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
from .models.theme_models import (
    IrAsset, IrAttachment, ThemeIrAsset, ThemeIrAttachment,
    ThemeIrUiView, ThemeUtils, ThemeWebsiteMenu, ThemeWebsitePage, WebsitePage,
)
from .models.website import Website
from .models.website_configurator_feature import WebsiteConfiguratorFeature
from .models.website_controller_page import WebsiteControllerPage
from .models.website_form import IrModel, IrModelFields
from .models.website_menu import WebsiteMenu
from .models.website_page_properties import WebsitePageProperties, WebsitePagePropertiesBase
from .models.website_rewrite import WebsiteRewrite, WebsiteRoute
from .models.website_snippet_filter import WebsiteSnippetFilter
from .models.website_visitor import WebsiteTrack, WebsiteVisitor
from .wizard.base_language_install import BaseLanguageInstall
from .wizard.blocked_third_party_domains import WebsiteCustom_Blocked_Third_Party_Domains
from .wizard.portal_wizard import PortalWizardUser
from .wizard.website_robots import WebsiteRobots


def uninstall_hook(env):
    # Force remove ondelete='cascade' elements,
    # This might be prevented by another ondelete='restrict' field
    # TODO: This should be an Odoo generic fix, not a website specific one
    website_domain = [('website_id', '!=', False)]
    env['ir.asset'].search(website_domain).unlink()
    env['ir.ui.view'].search(website_domain).with_context(active_test=False, _force_unlink=True).unlink()

    # Cleanup records which are related to websites and will not be autocleaned
    # by the uninstall operation. This must be done here in the uninstall_hook
    # as during an uninstallation, `unlink` is not called for records which were
    # created by the user (not XML data). Same goes for @api.ondelete available
    # from 15.0 and above.
    env['website'].search([])._remove_attachments_on_website_unlink()

    # Properly unlink website_id from ir.model.fields
    def rem_website_id_null(dbname):
        db_registry = odoo.modules.registry.Registry.new(dbname)
        with db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['ir.model.fields'].search([
                ('name', '=', 'website_id'),
                ('model', '=', 'res.config.settings'),
            ]).unlink()

    env.cr.postcommit.add(partial(rem_website_id_null, env.cr.dbname))


def post_init_hook(env):
    if request:
        env = env(context=request.default_context())
        request.website_routing = env['website'].get_current_website().id
