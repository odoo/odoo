# -*- coding: utf-8 -*-
# 康虎软件工作室
# http://www.khcloud.net
# QQ: 360026606
# wechat: 360026606
#--------------------------

import logging
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    comment = fields.Char(string="Comment")


class IrModuleCategory(models.Model):
    _inherit = 'ir.module.category'

    comment = fields.Char(string="Comment")
