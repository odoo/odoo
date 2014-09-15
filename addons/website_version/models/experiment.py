# -*- coding: utf-8 -*-
from openerp.osv import osv, fields

class Experiment_snapshot(osv.Model):
    _name = "website_version.experiment_snapshot"
    
    _columns = {
        'snapshot_id': fields.many2one('website_version.snapshot',string="Snapshot_id",required=True ,ondelete='cascade'),
        'experiment_id': fields.many2one('website_version.experiment',string="Experiment_id",required=True),
        'frequency': fields.selection([('10','Rare'),('50','Sometimes'),('100','Offen')], 'Frequency'),
    }

    _defaults = {
        'frequency': '10',
    }


class Experiment(osv.Model):
    _name = "website_version.experiment"

    def _get_denom(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for exp in self.browse(cr, uid, ids, context=context):
            result[exp.id] = 0
            for exp_snap in exp.experiment_snapshot_ids:
                    result[exp.id] += exp_snap.ponderation
        return result
    
    _columns = {
        'name': fields.char(string="Title", size=256, required=True),
        'experiment_snapshot_ids': fields.one2many('website_version.experiment_snapshot', 'experiment_id',string="experiment_snapshot_ids"),
        'website_id': fields.many2one('website',string="Website", required=True),
        'state': fields.selection([('draft','Draft'),('running','Running'),('done','Done')], 'Status', required=True, copy=False),
        'denominator' : fields.function(_get_denom,type='integer'),
    }

    _defaults = {
        'state': 'draft',
    }

