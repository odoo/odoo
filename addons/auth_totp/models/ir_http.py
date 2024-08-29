# -*- coding: utf-8 -*-
from odoo.addons import base
from odoo import models
from odoo.http import request

class IrHttp(models.AbstractModel, base.IrHttp):

    def session_info(self):
        info = super().session_info()
        # because frontend session_info uses this key and is embedded in
        # the view source
        info["user_id"] = request.session.uid,
        return info
