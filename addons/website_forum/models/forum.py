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

#TODO: do we need a forum object like blog object Need to check with BE team?
# class Forum(osv.Model):
#     _name = 'blog.blog'
#     _description = 'Blogs'
#     _inherit = ['mail.thread', 'website.seo.metadata']
#     _order = 'name'
# 
#     _columns = {
#         'name': fields.char('Name', required=True),
#         'description': fields.text('Description'),
#         'forum_post_ids': fields.one2many(
#             'website.forum.post', 'forum_id',
#             'Posts',
#         ),
#     }

class Post(osv.Model):
    _name = "website.forum.post"
    _description = "Question"
    _inherit = ['mail.thread', 'website.seo.metadata']

    _columns = {
        #TODO: do we need a forum object like blog object Need to check with BE team?
        #'forum_id': fields.many2one('website.forum', 'Forum'),
        
        'name': fields.char('Topic', size=64),
        'body': fields.html('Contents', help='Automatically sanitized HTML contents'),
        
        'create_date': fields.datetime('Asked on', select=True, readonly=True),
        'create_uid': fields.many2one('res.users', 'Asked by', select=True, readonly=True ),
        'write_date': fields.datetime('Update on', select=True, readonly=True ),
        'write_uid': fields.many2one('res.users', 'Update by', select=True, readonly=True),
        
        'tags': fields.many2many('website.forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', 'Tag'),
        'vote_ids':fields.one2many('website.forum.post.vote', 'Vote'),
        
        'favourite_ids': fields.many2many('res.users', 'forum_favourite_rel', 'forum_id', 'user_id', 'Favourite'),
        
        'state': fields.selection([('active', 'Active'),('close', 'Close'),('offensive', 'Offensive')], 'Status'),
        'active': fields.boolean('Active'),
        'views': fields.integer('Views'),
        
        'parent_id': fields.many2one('website.forum.post', 'Parent'),
        'child_ids': fields.one2many('website.forum.post', 'parent_id', 'Child'),
        
        # TODO FIXME: when website_mail/mail_thread.py inheritance work -> this field won't be necessary
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', ('model', '=', self._name), ('type', '=', 'comment')
            ],
            string='Post Messages',
            help="Comments on forum post",
        ),
    }
    _defaults = {
        'state': 'active',
        'active': True
    }

class PostHistory(osv.Model):
    _name = 'website.forum.post.history'
    _description = "Post History"
    _inherit = ['website.seo.metadata']
    _columns = {
        'post_id': fields.many2one('website.forum.post', 'Post'),
        'name': fields.char('Update Notes', size=64, required=True),
        'body': fields.html('Contents', help='Automatically sanitized HTML contents'),
        'tags': fields.many2many('website.forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', 'Tag'),
    }

class Vote(osv.Model):
    _name = "website.forum.post.vote"
    _description = "Vote"
    _column = {
        'post_id': fields.many2one('website.forum.post', 'Post'),
        'user_id': fields.many2one('res.users', 'User'),
        'vote': fields.integer('rate'), #Value in between wither +1 or -1
    }

class Tags(osv.Model):
    _name = "website.forum.tag"
    _description = "Tags"
    _inherit = ['website.seo.metadata']
    _columns = {
        'name': fields.char('Order Reference', size=64, required=True),
        'post_ids': fields.many2many('website.forum.post', 'forum_tag_que_rel', 'tag_id', 'forum_id', 'Question', readonly=True),
    }