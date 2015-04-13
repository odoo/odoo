# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tools import html2plaintext
from openerp.osv import osv, fields, expression

class MailMessage(osv.Model):
    _inherit = 'mail.message'

    def _get_description_short(self, cr, uid, ids, name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for message in self.browse(cr, uid, ids, context=context):
            if message.subject:
                res[message.id] = message.subject
            else:
                plaintext_ct = '' if not message.body else html2plaintext(message.body)
                res[message.id] = plaintext_ct[:30] + '%s' % (' [...]' if len(plaintext_ct) >= 30 else '')
        return res

    _columns = {
        'description': fields.function(
            _get_description_short, type='char',
            help='Message description: either the subject, or the beginning of the body'
        ),
        'website_published': fields.boolean(
            'Published', help="Visible on the website as a comment", copy=False,
        ),
    }

    def default_get(self, cr, uid, fields_list, context=None):
        defaults = super(MailMessage, self).default_get(cr, uid, fields_list, context=context)

        # Note: explicitly implemented in default_get() instead of _defaults,
        # to avoid setting to True for all existing messages during upgrades.
        # TODO: this default should probably be dynamic according to the model
        # on which the messages are attached, thus moved to create().
        if 'website_published' in fields_list:
            defaults.setdefault('website_published', True)

        return defaults

class IrRule(osv.Model):
    _inherit = 'ir.rule'

    def _compute_domain(self, cr, uid, model_name, mode="read"):
        domain = super(IrRule, self)._compute_domain(cr, uid, model_name, mode=mode)
        if model_name == 'mail.message' and self.pool['res.users'].has_group(cr, uid, 'base.group_public'):
            domain = expression.AND([domain, [('website_published', '=', True)]])
        return domain

