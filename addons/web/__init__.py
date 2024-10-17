# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from .models.base_document_layout import BaseDocumentLayout
from .models.ir_http import IrHttp
from .models.ir_model import IrModel
from .models.ir_qweb_fields import IrQwebFieldImage, IrQwebFieldImage_Url
from .models.ir_ui_menu import IrUiMenu
from .models.ir_ui_view import IrUiView
from .models.models import Base, ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
