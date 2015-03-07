# -*- coding: utf-8 -*-

import time
from openerp import models
from openerp.report import report_sxw


class order(report_sxw.rml_parse):

    def get_lines(self, user,objects):
        lines=[]
        for obj in objects:
            if user.id==obj.user_id.id:
                lines.append(obj)
        return lines

    def get_total(self, user,objects):
        lines=[]
        for obj in objects:
            if user.id==obj.user_id.id:
                lines.append(obj)
        total=0.0
        for line in lines:
            total+=line.price
        self.net_total+=total
        return total

    def get_nettotal(self):
        return self.net_total

    def get_users(self, objects):
        users=[]
        for obj in objects:
            if obj.user_id not in users:
                users.append(obj.user_id)
        return users

    def get_note(self,objects):
        notes=[]
        for obj in objects:
            notes.append(obj.note)
        return notes
        
    def __init__(self, cr, uid, name, context):
        super(order, self).__init__(cr, uid, name, context)
        self.net_total=0.0
        self.localcontext.update({
            'time': time,
            'get_lines': self.get_lines,
            'get_users': self.get_users,
            'get_total': self.get_total,
            'get_nettotal': self.get_nettotal,
            'get_note': self.get_note,
        })


class report_lunchorder(models.AbstractModel):
    _name = 'report.lunch.report_lunchorder'
    _inherit = 'report.abstract_report'
    _template = 'lunch.report_lunchorder'
    _wrapped_report_class = order
