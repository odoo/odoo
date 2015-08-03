# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields

class note_base_config_settings(osv.osv_memory):
    _inherit = 'base.config.settings'
    _columns = {
        'module_note_pad': fields.boolean('Use collaborative pads (etherpad)'),
    }
