# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv

class mail_template(osv.osv):
    _inherit = "mail.template"
    _defaults = {
        'model_id': lambda obj, cr, uid, context: context.get('object_id',False),
    }

    # TODO: add constraint to prevent disabling / disapproving an email account used in a running campaign


