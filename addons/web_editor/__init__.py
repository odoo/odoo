# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from .models.assets import Web_EditorAssets
from .models.html_field_history_mixin import HtmlFieldHistoryMixin
from .models.ir_http import IrHttp
from .models.ir_qweb_fields import (
    IrQweb, IrQwebField, IrQwebFieldContact, IrQwebFieldDate,
    IrQwebFieldDatetime, IrQwebFieldDuration, IrQwebFieldFloat, IrQwebFieldHtml,
    IrQwebFieldImage, IrQwebFieldInteger, IrQwebFieldMany2one, IrQwebFieldMonetary,
    IrQwebFieldQweb, IrQwebFieldRelative, IrQwebFieldSelection, IrQwebFieldText,
)
from .models.ir_ui_view import IrUiView
from .models.ir_websocket import IrWebsocket
from .models.models import Base
from .models.test_models import Web_EditorConverterTest, Web_EditorConverterTestSub
