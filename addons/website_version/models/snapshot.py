# -*- coding: utf-8 -*-
from openerp.osv import osv, fields


class Snapshot(osv.Model):
    _name = "website_version.snapshot"
    
    _columns = {
        'name' : fields.char(string="Title", required=True),
        'view_ids': fields.one2many('ir.ui.view', 'snapshot_id',string="view_ids",copy=True),
        'website_id': fields.many2one('website',ondelete='cascade', string="Website"),
        'create_date': fields.datetime('Create Date'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'You cannot have multiple snapshots with the same name!'),
    ]