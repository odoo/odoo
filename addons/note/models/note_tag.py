# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields

class note_tag(osv.osv):
    _name = "note.tag"
    _description = "Note Tag"
    _columns = {
        'name' : fields.char('Tag Name', required=True),
    }
