# -*- coding: utf-8 -*-

from datetime import datetime
import difflib
import lxml
import random

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.website.models.website import slug
from openerp.osv import osv, fields
from openerp.tools.translate import _


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

    def all_tags(self, cr, uid, ids, min_limit=1, context=None):
        req = """
            SELECT
                p.blog_id, count(*), r.blog_tag_id
            FROM
                blog_post_blog_tag_rel r
                    join blog_post p on r.blog_post_id=p.id
            WHERE
                p.blog_id in %s
            GROUP BY
                p.blog_id,
                r.blog_tag_id
            ORDER BY
                count(*) DESC
        """
        cr.execute(req, [tuple(ids)])
        tag_by_blog = {i: [] for i in ids}
        for blog_id, freq, tag_id in cr.fetchall():
            if freq >= min_limit:
                tag_by_blog[blog_id].append(tag_id)

        tag_obj = self.pool['blog.tag']
        for blog_id in tag_by_blog:
            tag_by_blog[blog_id] = tag_obj.browse(cr, uid, tag_by_blog[blog_id], context=context)
        return tag_by_blog


class BlogTag(osv.Model):
    _name = 'blog.tag'
    _description = 'Blog Tag'
    _inherit = ['website.seo.metadata']
    _order = 'name'
    _columns = {
        'name': fields.char('Name', required=True),
        'post_ids': fields.many2many(
            'blog.post', string='Posts',
        ),
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
        'author_avatar': fields.related(
            'author_id', 'image_small',
            string="Avatar", type="binary"),
        'visits': fields.integer('No of Views'),
        'ranking': fields.function(_compute_ranking, string='Ranking', type='float'),
    }

    _defaults = {
        'name': _('Blog Post Title'),
        'subtitle': _('Subtitle'),
        'author_id': lambda self, cr, uid, ctx=None: self.pool['res.users'].browse(cr, uid, uid, context=ctx).partner_id.id,
    }

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

    def _check_for_publication(self, cr, uid, ids, vals, context=None):
        if vals.get('website_published'):
            base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
            for post in self.browse(cr, uid, ids, context=context):
                post.blog_id.message_post(
                    body='<p>%(post_publication)s <a href="%(base_url)s/blog/%(blog_slug)s/post/%(post_slug)s">%(post_link)s</a></p>' % {
                        'post_publication': _('A new post %s has been published on the %s blog.') % (post.name, post.blog_id.name),
                        'post_link': _('Click here to access the post.'),
                        'base_url': base_url,
                        'blog_slug': slug(post.blog_id),
                        'post_slug': slug(post),
                    },
                    subtype='website_blog.mt_blog_blog_published',
                    context=context)
            return True
        return False

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if 'content' in vals:
            vals['content'] = self._postproces_content(cr, uid, None, vals['content'], context=context)
        create_context = dict(context, mail_create_nolog=True)
        post_id = super(BlogPost, self).create(cr, uid, vals, context=create_context)
        self._check_for_publication(cr, uid, [post_id], vals, context=context)
        return post_id

    def write(self, cr, uid, ids, vals, context=None):
        if 'content' in vals:
            vals['content'] = self._postproces_content(cr, uid, None, vals['content'], context=context)
        result = super(BlogPost, self).write(cr, uid, ids, vals, context)
        self._check_for_publication(cr, uid, ids, vals, context=context)
        return result
