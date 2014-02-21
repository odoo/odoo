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

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

from openerp.tools.translate import _
import re

from openerp.addons.website.models.website import slug

#class WebsiteForum(osv.Model):
#    _inhrit = "website"

class website_form_post_rate(osv.Model):
    _name = "website.forum.post.rate"
    _column = {
        'post_id': fields.many2one('website.forum.post', 'Forum Post'),
        'user_id': fields.many2one('res.users', 'User'),
        'rate': fields.integer('rate'),
    }

class website_forum_post(osv.Model):
    _name = "website.forum.post"
    _description = "Website forum post"
    _inherit = ['mail.thread', 'website.seo.metadata']

    _columns = {
        #add version and category , instead of page use category in website,
        'name': fields.char('Topic', size=64),
        'body': fields.html('Contents', help='Automatically sanitized HTML contents'),
        #'forum_id': fields.many2one('website.forum', 'Forum'),
        'create_date': fields.datetime('Created on', select=True, readonly=True),
        'create_uid': fields.many2one('res.users', 'Author', select=True, readonly=True ),
        'write_date': fields.datetime('Last Modified on', select=True, readonly=True ),
        'write_uid': fields.many2one('res.users', 'Last Contributor', select=True, readonly=True),
        'tags': fields.many2many('website.forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', 'Tag'),
        'up_votes': fields.many2many('res.users', 'forum_user_upvotes_rel', 'forum_id', 'user_id', 'Up votes'),
        'favourite_que_ids': fields.many2many('res.users', 'forum_user_fav_rel', 'forum_id', 'user_id', 'Down votes'),
        'views': fields.integer('Views'),
        'state': fields.selection([('active', 'Active'),('close', 'Close'),('offensive', 'Offensive')], 'Status'),
        'parent_id': fields.many2one('website.forum.post', 'Parent'),
        'child_ids': fields.one2many('website.forum.post', 'parent_id', 'Child'),
        # TODO FIXME: when website_mail/mail_thread.py inheritance work -> this field won't be necessary
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', ('model', '=', self._name), ('type', '=', 'comment')
            ],
            string='Website Messages',
            help="Website communication history",
        ),
    }
    _defaults = {
        'state': 'active',
    }

class website_forum_tag(osv.Model):
    _name = "website.forum.tag"
    _description = "Website forum tag"
    _inherit = ['website.seo.metadata']
    _columns = {
        'name': fields.char('Order Reference', size=64, required=True),
        #'forum_id': fields.many2one('website.forum', 'Forum'),
        'post_ids': fields.many2many('website.forum.post', 'forum_tag_que_rel', 'tag_id', 'forum_id', 'Question', readonly=True),
    }

