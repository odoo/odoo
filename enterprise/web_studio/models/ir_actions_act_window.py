# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrActionsActWindow(models.Model):
    _name = 'ir.actions.act_window'
    _inherit = ['studio.mixin', 'ir.actions.act_window']


class IrActionsActWindowView(models.Model):
    _name = 'ir.actions.act_window.view'
    _inherit = ['studio.mixin', 'ir.actions.act_window.view']
