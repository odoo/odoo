# -*- coding: utf-8 -*-

from datetime import datetime
import lxml
import random

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.website.models.website import slug
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools.translate import html_translate


class Blog(osv.Model):
    _name = 'blog.blog'
    _description = 'Blogs'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = 'name'
    _columns = {
        'name': fields.char('Blog Name', required=True, translate=True),
        'subtitle': fields.char('Blog Subtitle', translate=True),
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
    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class BlogPost(osv.Model):
    _name = "blog.post"
    _description = "Blog Post"
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.mixin']
    _order = 'id DESC'
    _mail_post_access = 'read'

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = super(BlogPost, self)._website_url(cr, uid, ids, field_name, arg, context=context)
        for blog_post in self.browse(cr, uid, ids, context=context):
            res[blog_post.id] = "/blog/%s/post/%s" % (slug(blog_post.blog_id), slug(blog_post))
        return res

    def _compute_ranking(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for blog_post in self.browse(cr, uid, ids, context=context):
            age = datetime.now() - datetime.strptime(blog_post.create_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            res[blog_post.id] = blog_post.visits * (0.5+random.random()) / max(3, age.days)
        return res

    def _default_content(self, cr, uid, context=None):
        return '''  <div class="container">
                        <section class="mt16 mb16">
                            <p class="o_default_snippet_text">''' + _("Start writing here...") + '''</p>
                        </section>
                    </div> '''

    _columns = {
        'name': fields.char('Title', required=True, translate=True),
        'subtitle': fields.char('Sub Title', translate=True),
        'author_id': fields.many2one('res.partner', 'Author'),
        'cover_properties': fields.text('Cover Properties'),
        'blog_id': fields.many2one(
            'blog.blog', 'Blog',
            required=True, ondelete='cascade',
        ),
        'tag_ids': fields.many2many(
            'blog.tag', string='Tags',
        ),
        'content': fields.html('Content', translate=html_translate, sanitize=False),
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', '&', ('model', '=', self._name), ('message_type', '=', 'comment'), ('path', '=', False)
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
        'visits': fields.integer('No of Views', copy=False),
        'ranking': fields.function(_compute_ranking, string='Ranking', type='float'),
    }

    _defaults = {
        'name': '',
        'content': _default_content,
        'cover_properties': '{"background-image": "none", "background-color": "oe_none", "opacity": "0.6", "resize_class": ""}',
        'author_id': lambda self, cr, uid, ctx=None: self.pool['res.users'].browse(cr, uid, uid, context=ctx).partner_id.id,
    }

    def html_tag_nodes(self, html, attribute=None, tags=None, context=None):
        """ Processing of html content to tag paragraphs and set them an unique
        ID.
        :return result: (html, mappin), where html is the updated html with ID
                        and mapping is a list of (old_ID, new_ID), where old_ID
                        is None is the paragraph is a new one. """

        existing_attributes = []
        mapping = []
        if not html:
            return html, mapping
        if tags is None:
            tags = ['p']
        if attribute is None:
            attribute = 'data-unique-id'

        # form a tree
        root = lxml.html.fragment_fromstring(html, create_parent='div')
        if not len(root) and root.text is None and root.tail is None:
            return html, mapping

        # check all nodes, replace :
        # - img src -> check URL
        # - a href -> check URL
        for node in root.iter():
            if node.tag not in tags:
                continue
            ancestor_tags = [parent.tag for parent in node.iterancestors()]

            old_attribute = node.get(attribute)
            new_attribute = old_attribute
            if not new_attribute or (old_attribute in existing_attributes):
                if ancestor_tags:
                    ancestor_tags.pop()
                counter = random.randint(10000, 99999)
                ancestor_tags.append('counter_%s' % counter)
                new_attribute = '/'.join(reversed(ancestor_tags))
                node.set(attribute, new_attribute)

            existing_attributes.append(new_attribute)
            mapping.append((old_attribute, new_attribute))

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
        if id:  # not creating
            existing = [x[0] for x in mapping if x[0]]
            msg_ids = self.pool['mail.message'].search(cr, SUPERUSER_ID, [
                ('res_id', '=', id),
                ('model', '=', self._name),
                ('path', 'not in', existing),
                ('path', '!=', False)
            ], context=context)
            self.pool['mail.message'].unlink(cr, SUPERUSER_ID, msg_ids, context=context)

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
                    subtype='website_blog.mt_blog_blog_published')
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
        if isinstance(ids, (int, long)):
            ids = [ids]
        if 'content' in vals:
            vals['content'] = self._postproces_content(cr, uid, ids[0], vals['content'], context=context)
        result = super(BlogPost, self).write(cr, uid, ids, vals, context)
        self._check_for_publication(cr, uid, ids, vals, context=context)
        return result

    def get_access_action(self, cr, uid, ids, context=None):
        """ Override method that generated the link to access the document. Instead
        of the classic form view, redirect to the post on the website directly """
        post = self.browse(cr, uid, ids[0], context=context)
        return {
            'type': 'ir.actions.act_url',
            'url': '/blog/%s/post/%s' % (post.blog_id.id, post.id),
            'target': 'self',
            'res_id': post.id,
        }

    def _notification_get_recipient_groups(self, cr, uid, ids, message, recipients, context=None):
        """ Override to set the access button: everyone can see an access button
        on their notification email. It will lead on the website view of the
        post. """
        res = super(BlogPost, self)._notification_get_recipient_groups(cr, uid, ids, message, recipients, context=context)
        access_action = self._notification_link_helper(cr, uid, ids, 'view', model=message.model, res_id=message.res_id)
        for category, data in res.iteritems():
            res[category]['button_access'] = {'url': access_action, 'title': _('View Blog Post')}
        return res


class Website(osv.Model):
    _inherit = "website"

    def page_search_dependencies(self, cr, uid, view_id, context=None):
        dep = super(Website, self).page_search_dependencies(cr, uid, view_id, context=context)

        post_obj = self.pool.get('blog.post')

        view = self.pool.get('ir.ui.view').browse(cr, uid, view_id, context=context)
        name = view.key.replace("website.", "")
        fullname = "website.%s" % name

        dom = [
            '|', ('content', 'ilike', '/page/%s' % name), ('content', 'ilike', '/page/%s' % fullname)
        ]
        posts = post_obj.search(cr, uid, dom, context=context)
        if posts:
            page_key = _('Blog Post')
            dep[page_key] = []
        for p in post_obj.browse(cr, uid, posts, context=context):
            dep[page_key].append({
                'text': _('Blog Post <b>%s</b> seems to have a link to this page !') % p.name,
                'link': p.website_url
            })

        return dep
