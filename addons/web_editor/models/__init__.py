# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .ir_qweb import IrQweb
from .ir_qweb_fields import IrQwebFieldImage, IrQwebFieldHtml, IrQwebFieldContact, IrQwebFieldSelection, IrQwebFieldMonetary, IrQwebFieldDuration, IrQwebFieldRelative, IrQwebFieldQweb, IrQwebFieldMany2one, IrQwebFieldDatetime, IrQwebFieldFloat, IrQwebField, IrQwebFieldInteger, IrQweb, IrQwebFieldDate, IrQwebFieldText
from .ir_ui_view import IrUiView
from .ir_http import IrHttp
from .ir_websocket import IrWebsocket
from .models import BaseModel, Base
from .html_field_history_mixin import HtmlFieldHistoryMixin

from .assets import WebEditorAssets

from .test_models import WebEditorConverterTestSub, WebEditorConverterTest
