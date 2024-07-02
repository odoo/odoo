# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import assetsbundle

from .ir_model import IrModelData, IrModelAccess
from .ir_sequence import IrSequence
from .ir_ui_menu import IrUiMenu
from .ir_ui_view import IrUiView
from . import ir_asset
from .ir_actions import IrActions
from . import ir_embedded_actions
from .ir_actions_report import IrActionsReport
from . import ir_attachment
from . import ir_binary
from . import ir_cron
from . import ir_filters
from . import ir_default
from . import ir_exports
from .ir_rule import IrRule
from .ir_config_parameter import IrConfigParameter
from . import ir_autovacuum
from . import ir_mail_server
from . import ir_fields
from . import ir_qweb
from . import ir_qweb_fields
from . import ir_http
from . import ir_logging
from . import ir_property
from .ir_module import IrModuleCategory
from . import ir_demo
from . import ir_demo_failure
from . import report_layout
from . import report_paperformat

from . import ir_profile
from . import image_mixin
from . import avatar_mixin

from .res_country import Country
from .res_lang import Lang
from .res_partner import Partner
from . import res_bank
from .res_config import ResConfigSettings
from .res_currency import Currency
from .res_company import Company
from .res_users import ResUsers
from . import res_users_settings
from . import res_users_deletion

from .decimal_precision import DecimalPrecision
