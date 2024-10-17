# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Updating mako environement in order to be able to use slug
try:
    from odoo.tools.rendering_tools import template_env_globals
    from odoo.http import request

    template_env_globals.update({
        'slug': lambda value: request.env['ir.http']._slug(value)  # noqa: PLW0108
    })
except ImportError:
    pass

from . import controllers
from . import models
from . import utils
from . import wizard

from .models.ir_http import IrHttp
from .models.ir_qweb import IrQweb
from .models.ir_ui_view import IrUiView
from .models.mail_message import MailMessage
from .models.mail_thread import MailThread
from .models.portal_mixin import PortalMixin
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .models.res_users_apikeys_description import ResUsersApikeysDescription
from .wizard.portal_share import PortalShare
from .wizard.portal_wizard import PortalWizard, PortalWizardUser
