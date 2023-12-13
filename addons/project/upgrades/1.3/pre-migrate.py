# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


def migrate(cr, version):
    cr.execute("""
        UPDATE ir_model_access a
           SET perm_read = true
          FROM ir_model_data d
         WHERE d.res_id = a.id
           AND d.model = 'ir.model.access'
           AND d.module = 'project'
           AND d.name = 'access_project_milestone_portal'
        """)
