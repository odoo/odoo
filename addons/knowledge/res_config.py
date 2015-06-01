# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class knowledge_config_settings(osv.osv_memory):
    _name = 'knowledge.config.settings'
    _inherit = 'res.config.settings'
    _columns = {
        'module_document': fields.boolean('Manage documents',
            help='Document indexation, full text search of attachements.\n'
                 '-This installs the module document.'),
    }
