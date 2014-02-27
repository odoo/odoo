# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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

from openerp.osv import osv


class MailComposeMessage(osv.Model):
    _inherit = 'mail.compose.message'

    def generate_email_for_composer_batch(self, cr, uid, template_id, res_ids, context=None, fields=None):
        """ Add a post processing after rendering, aka replace local URLs to absolute URLs. """
        results = super(MailComposeMessage, self).generate_email_for_composer_batch(cr, uid, template_id, res_ids, context=context, fields=fields)
        for res_id, value in results.iteritems():
            if 'body' in value:
                results[res_id]['body'] = self.pool['email.template']._postprocess_html_replace_links(cr, uid, value['body'], context=context)
        return results
