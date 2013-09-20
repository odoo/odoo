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

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields


class WebsiteDocumentPage(osv.Model):
    """ Inherit document.page to add website-related columns

     - website_published: standard publish column
     - website_message_ids: messages to display on website, aka comments

    """
    _inherit = "blog.post"
    # maximum number of characters to display in summary
    _shorten_max_char = 10

    def get_shortened_content(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for page in self.browse(cr, uid, ids, context=context):
            try:
                body_short = tools.html_email_clean(page.content, remove=True, shorten=True, max_length=self._shorten_max_char)
            except Exception:
                body_short = False
            res[page.id] = body_short
        return res

    _columns = {
        'website_published': fields.boolean(
            'Publish', help="Publish on the website"
        ),
        'website_published_datetime': fields.datetime(
            'Publish Date'
        ),
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', ('model', '=', self._name), ('type', '=', 'comment')
            ],
            auto_join=True,
            string='Website Messages',
            help="Website communication history",
        ),
        'shortened_content': fields.function(
            get_shortened_content,
            type='text',
            string='Shortened Content',
            help="Shortened content of the page that serves as a summary"
        ),
    }

    def img(self, cr, uid, ids, field='image_small', context=None):
        post = self.browse(cr, SUPERUSER_ID, ids[0], context=context)
        return "/website/image?model=%s&field=%s&id=%s" % ('res.users', field, post.create_uid.id)
