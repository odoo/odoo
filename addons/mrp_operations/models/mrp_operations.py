# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv


class mrp_operations_operation(osv.osv):
    _name="mrp_operations.operation"

    def initialize_workflow_instance(self, cr, uid, context=None):
        mrp_production_workcenter_line = self.pool.get('mrp.production.workcenter.line')
        line_ids = mrp_production_workcenter_line.search(cr, uid, [], context=context)
        mrp_production_workcenter_line.create_workflow(cr, uid, line_ids)
        return True
