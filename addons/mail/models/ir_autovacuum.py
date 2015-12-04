# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models

class AutoVacuum(models.TransientModel):
    _inherit = 'ir.autovacuum'

    def power_on(self, cr, uid, *args, **kwargs):
        self.pool['mail.thread']._garbage_collect_attachments(cr, uid)
        return super(AutoVacuum, self).power_on(cr, uid, *args, **kwargs)
