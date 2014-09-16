# -*- coding: utf-8 -*-

from datetime import datetime
import difflib
import lxml
import random

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug

class Blog(osv.Model):
    _name = 'blog.blog'
    _description = 'Blogs'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = 'name'
    _columns = {
        'name': fields.char('Blog Name', required=True),
        'subtitle': fields.char('Blog Subtitle'),
        'description': fields.text('Description'),
    }


class BlogTag(osv.Model):
    _name = 'blog.tag'
    _description = 'Blog Tag'
    _inherit = ['website.seo.metadata']
    _order = 'name'
    _columns = {
        'name': fields.char('Name', required=True),
    }


class BlogPost(osv.Model):
    _name = "blog.post"
    _description = "Blog Post"
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = 'id DESC'

    def _compute_ranking(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for blog_post in self.browse(cr, uid, ids, context=context):
            age = datetime.now() - datetime.strptime(blog_post.create_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            res[blog_post.id] = blog_post.visits * (0.5+random.random()) / max(3, age.days)
        return res

    _columns = {
        'name': fields.char('Title', required=True, translate=True),
        'subtitle': fields.char('Sub Title', translate=True),
        'author_id': fields.many2one('res.partner', 'Author'),
        'background_image': fields.binary('Background Image', oldname='content_image'),
        'blog_id': fields.many2one(
            'blog.blog', 'Blog',
            required=True, ondelete='cascade',
        ),
        'tag_ids': fields.many2many(
            'blog.tag', string='Tags',
        ),
        'content': fields.html('Content', translate=True, sanitize=False),
        # website control
        'website_published': fields.boolean(
            'Publish', help="Publish on the website", copy=False,
        ),
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', '&', ('model', '=', self._name), ('type', '=', 'comment'), ('path', '=', False)
            ],
            string='Website Messages',
            help="Website communication history",
        ),
        # creation / update stuff
        'create_date': fields.datetime(
            'Created on',
            select=True, readonly=True,
        ),
        'create_uid': fields.many2one(
            'res.users', 'Author',
            select=True, readonly=True,
        ),
        'write_date': fields.datetime(
            'Last Modified on',
            select=True, readonly=True,
        ),
        'write_uid': fields.many2one(
            'res.users', 'Last Contributor',
            select=True, readonly=True,
        ),
        'visits': fields.integer('No of Views'),
        'ranking': fields.function(_compute_ranking, string='Ranking', type='float'),
        'website_size_x': fields.integer('Size X'),
        'website_size_y': fields.integer('Size Y'),
        'website_sequence': fields.integer('Sequence', help="Determine the display order in the Website"),
    }

    def get_sequence(self, cr, uid, domain=[], order=None, context=None):
        order = 'website_sequence DESC' if order == 'DESC' else 'website_sequence'
        blogpost = [blogpost for blogpost in self.search_read(cr, uid, domain, ['website_sequence'], limit=1, order=order, context=context)]
        return blogpost and blogpost[0] or {'website_sequence': 0}

    _defaults = {
        'name': _('Blog Post Title'),
        'subtitle': _('Subtitle'),
        'author_id': lambda self, cr, uid, ctx=None: self.pool['res.users'].browse(cr, uid, uid, context=ctx).partner_id.id,
        'website_size_x': 1,
        'website_size_y': 1,
        'website_sequence': lambda self, cr, uid, ctx=None: self.get_sequence(cr, uid, order='DESC', context=ctx)['website_sequence'] + 1
    }

    def set_sequence_top(self, cr, uid, ids, context=None):
        max_sequence = self.get_sequence(cr, uid, order='DESC', context=context)
        return self.write(cr, uid, ids, {"website_sequence": max_sequence['website_sequence'] + 1}, context=context)

    def set_sequence_bottom(self, cr, uid, ids, context=None):
        min_sequence = self.get_sequence(cr, uid, context=context)
        return self.write(cr, uid, ids, {"website_sequence": min_sequence['website_sequence'] - 1}, context=context)

    def set_sequence_up(self, cr, uid, ids, context=None):
        blog_post = self.browse(cr, uid, ids, context=context)
        domain = [('website_sequence', '>', blog_post.website_sequence), ('website_published', '=', blog_post.website_published)]
        prev = self.get_sequence(cr, uid, domain=domain, context=context)
        if prev['website_sequence']:
            self.write(cr, uid, [prev['id']], {"website_sequence": blog_post.website_sequence}, context=context)
            return self.write(cr, uid, ids, {"website_sequence": prev['website_sequence']}, context=context)
        else:
            return self.set_sequence_top(cr, uid, ids, context=context)

    def set_sequence_down(self, cr, uid, ids, context=None):
        blog_post = self.browse(cr, uid, ids, context=context)
        domain = [('website_sequence', '<', blog_post.website_sequence), ('website_published', '=', blog_post.website_published)]
        next = self.get_sequence(cr, uid, domain=domain, order='DESC', context=context)
        if next['website_sequence']:
            self.write(cr, uid, [next['id']], {"website_sequence": blog_post.website_sequence}, context=context)
            return self.write(cr, uid, ids, {"website_sequence": next['website_sequence']}, context=context)
        else:
            return self.set_sequence_bottom(cr, uid, ids, context=context)

    def _get_share_url(self, cr, uid, ids, context=None):
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        for blog_post in self.browse(cr, uid, ids, context=context):
            share_url = "%s/blog/%s/post/%s" % (base_url, slug(blog_post.blog_id), slug(blog_post))
        return share_url

    def html_tag_nodes(self, html, attribute=None, tags=None, context=None):
        """ Processing of html content to tag paragraphs and set them an unique
        ID.
        :return result: (html, mappin), where html is the updated html with ID
                        and mapping is a list of (old_ID, new_ID), where old_ID
                        is None is the paragraph is a new one. """
        mapping = []
        if not html:
            return html, mapping
        if tags is None:
            tags = ['p']
        if attribute is None:
            attribute = 'data-unique-id'
        counter = 0

        # form a tree
        root = lxml.html.fragment_fromstring(html, create_parent='div')
        if not len(root) and root.text is None and root.tail is None:
            return html, mapping

        # check all nodes, replace :
        # - img src -> check URL
        # - a href -> check URL
        for node in root.iter():
            if not node.tag in tags:
                continue
            ancestor_tags = [parent.tag for parent in node.iterancestors()]
            if ancestor_tags:
                ancestor_tags.pop()
            ancestor_tags.append('counter_%s' % counter)
            new_attribute = '/'.join(reversed(ancestor_tags))
            old_attribute = node.get(attribute)
            node.set(attribute, new_attribute)
            mapping.append((old_attribute, counter))
            counter += 1

        html = lxml.html.tostring(root, pretty_print=False, method='html')
        # this is ugly, but lxml/etree tostring want to put everything in a 'div' that breaks the editor -> remove that
        if html.startswith('<div>') and html.endswith('</div>'):
            html = html[5:-6]
        return html, mapping

    def _postproces_content(self, cr, uid, id, content=None, context=None):
        if content is None:
            content = self.browse(cr, uid, id, context=context).content
        if content is False:
            return content
        content, mapping = self.html_tag_nodes(content, attribute='data-chatter-id', tags=['p'], context=context)
        for old_attribute, new_attribute in mapping:
            if not old_attribute:
                continue
            msg_ids = self.pool['mail.message'].search(cr, SUPERUSER_ID, [('path', '=', old_attribute)], context=context)
            self.pool['mail.message'].write(cr, SUPERUSER_ID, msg_ids, {'path': new_attribute}, context=context)
        return content

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if 'content' in vals:
            vals['content'] = self._postproces_content(cr, uid, None, vals['content'], context=context)
        create_context = dict(context, mail_create_nolog=True)
        post_id = super(BlogPost, self).create(cr, uid, vals, context=create_context)
        return post_id

    def write(self, cr, uid, ids, vals, context=None):
        if 'content' in vals:
            vals['content'] = self._postproces_content(cr, uid, None, vals['content'], context=context)
        result = super(BlogPost, self).write(cr, uid, ids, vals, context)
        return result
