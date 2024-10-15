# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .ir_qweb import IrQweb
from .ir_qweb_fields import (
    IrQwebField, IrQwebFieldContact, IrQwebFieldDate, IrQwebFieldDatetime,
    IrQwebFieldDuration, IrQwebFieldFloat, IrQwebFieldHtml, IrQwebFieldImage, IrQwebFieldInteger,
    IrQwebFieldMany2one, IrQwebFieldMonetary, IrQwebFieldQweb, IrQwebFieldRelative,
    IrQwebFieldSelection, IrQwebFieldText,
)
from .ir_ui_view import IrUiView
from .ir_http import IrHttp
from .ir_websocket import IrWebsocket
from .models import Base
from .html_field_history_mixin import HtmlFieldHistoryMixin

from .assets import Web_EditorAssets

from .test_models import Web_EditorConverterTest, Web_EditorConverterTestSub
