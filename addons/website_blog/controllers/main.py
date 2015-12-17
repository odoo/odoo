# -*- coding: utf-8 -*-
import json
import werkzeug
import itertools
from datetime import datetime

from odoo import fields, models, _
from odoo.addons.web import http
from odoo.addons.web.http import request
from odoo.addons.website.models.website import slug, unslug
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import html2plaintext


class QueryURL(object):
    def __init__(self, path='', path_args=None, **args):
        self.path = path
        self.args = args
        self.path_args = set(path_args or [])

    def __call__(self, path=None, path_args=None, **kw):
        path = path or self.path
        for k, v in self.args.items():
            kw.setdefault(k, v)
        path_args = set(path_args or []).union(self.path_args)
        paths, fragments = [], []
        for key, value in kw.items():
            if value and key in path_args:
                if isinstance(value, models.BaseModel):
                    paths.append((key, slug(value)))
                else:
                    paths.append((key, value))
            elif value:
                if isinstance(value, list) or isinstance(value, set):
                    fragments.append(werkzeug.url_encode([(key, item) for item in value]))
                else:
                    fragments.append(werkzeug.url_encode([(key, value)]))
        for key, value in paths:
            path += '/' + key + '/%s' % value
        if fragments:
            path += '?' + '&'.join(fragments)
        return path


class WebsiteBlog(http.Controller):
    _blog_post_per_page = 20
    _post_comment_per_page = 10

    def nav_list(self, blog=None):
        domain = blog and [('blog_id', '=', blog.id)] or []
        groups = request.env['blog.post'].read_group(domain, ['name', 'create_date'],
            groupby="create_date", orderby="create_date desc")
        for group in groups:
            begin_date = fields.Datetime.from_string(group['__domain'][0][2]).date()
            end_date = fields.Datetime.from_string(group['__domain'][1][2]).date()
            group['date_begin'] = '%s' % fields.Date.to_string(begin_date)
            group['date_end'] = '%s' % fields.Date.to_string(end_date)
            group['month'], group['year'] = group['create_date'].rsplit(' ', 1)
        return {year: [m for m in months] for year, months in itertools.groupby(groups, lambda g: g['year'])}

    @http.route([
        '/blog',
        '/blog/page/<int:page>',
    ], type='http', auth="public", website=True)
    def blogs(self, page=1, **post):
        BlogPost = request.env['blog.post']
        total = BlogPost.search_count([])
        pager = request.website.pager(
            url='/blog',
            total=total,
            page=page,
            step=self._blog_post_per_page,
        )
        posts = BlogPost.search([], offset=(page - 1) * self._blog_post_per_page, limit=self._blog_post_per_page)
        blog_url = QueryURL('', ['blog', 'tag'])
        return request.website.render("website_blog.latest_blogs", {
            'posts': posts,
            'pager': pager,
            'blog_url': blog_url,
        })

    @http.route([
        '/blog/<model("blog.blog"):blog>',
        '/blog/<model("blog.blog"):blog>/page/<int:page>',
        '/blog/<model("blog.blog"):blog>/tag/<string:tag>',
        '/blog/<model("blog.blog"):blog>/tag/<string:tag>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def blog(self, blog=None, tag=None, page=1, **opt):
        """ Prepare all values to display the blog.

        :return dict values: values for the templates, containing

         - 'blog': current blog
         - 'blogs': all blogs for navigation
         - 'pager': pager of posts
         - 'active_tag_ids' :  list of active tag ids,
         - 'tags_list' : function to built the comma-separated tag list ids (for the url),
         - 'tags': all tags, for navigation
         - 'nav_list': a dict [year][month] for archives navigation
         - 'date': date_begin optional parameter, used in archives navigation
         - 'blog_url': help object to create URLs
        """
        date_begin, date_end = opt.get('date_begin'), opt.get('date_end')
        blogs = request.env['blog.blog'].search([], order="create_date")

        # build the domain for blog post to display
        domain = []
        # retrocompatibility to accept tag as slug
        active_tag_ids = tag and map(int, [unslug(t)[1] for t in tag.split(',')]) or []
        if active_tag_ids:
            domain += [('tag_ids', 'in', active_tag_ids)]
        if blog:
            domain += [('blog_id', '=', blog.id)]
        if date_begin and date_end:
            domain += [("create_date", ">=", date_begin), ("create_date", "<=", date_end)]

        blog_url = QueryURL('', ['blog', 'tag'], blog=blog, tag=tag, date_begin=date_begin, date_end=date_end)

        blog_posts = request.env['blog.post'].search(domain, order="create_date desc")

        pager = request.website.pager(
            url=blog_url(),
            total=len(blog_posts),
            page=page,
            step=self._blog_post_per_page,
        )
        pager_begin = (page - 1) * self._blog_post_per_page
        pager_end = page * self._blog_post_per_page
        blog_posts = blog_posts[pager_begin:pager_end]

        all_tags = blog.all_tags()[blog.id]

        # function to create the string list of tag ids, and toggle a given one.
        # used in the 'Tags Cloud' template.
        def tags_list(tag_ids, current_tag):
            tag_ids = list(tag_ids) # required to avoid using the same list
            if current_tag in tag_ids:
                tag_ids.remove(current_tag)
            else:
                tag_ids.append(current_tag)
            tags = request.env['blog.tag'].browse(tag_ids).exists()
            return ','.join(map(slug, tags))

        values = {
            'blog': blog,
            'blogs': blogs,
            'main_object': blog,
            'tags': all_tags,
            'active_tag_ids': active_tag_ids,
            'tags_list': tags_list,
            'blog_posts': blog_posts,
            'blog_posts_cover_properties': [json.loads(b.cover_properties) for b in blog_posts],
            'pager': pager,
            'nav_list': self.nav_list(blog),
            'blog_url': blog_url,
            'date': date_begin,
        }
        response = request.website.render("website_blog.blog_post_short", values)
        return response

    @http.route(['/blog/<model("blog.blog"):blog>/feed'], type='http', auth="public")
    def blog_feed(self, blog, limit='15'):
        v = {}
        v['blog'] = blog
        v['base_url'] = request.env['ir.config_parameter'].get_param('web.base.url')
        v['posts'] = request.env['blog.post'].search([('blog_id','=', blog.id)], limit=min(int(limit), 50))
        r = request.render("website_blog.blog_feed", v, headers=[('Content-Type', 'application/atom+xml')])
        return r

    @http.route([
            '''/blog/<model("blog.blog"):blog>/post/<model("blog.post", "[('blog_id','=',blog[0])]"):blog_post>''',
    ], type='http', auth="public", website=True)
    def blog_post(self, blog, blog_post, page=1, enable_editor=None, **post):
        """ Prepare all values to display the blog.

        :return dict values: values for the templates, containing

         - 'blog_post': browse of the current post
         - 'blog': browse of the current blog
         - 'blogs': list of browse records of blogs
         - 'tag': current tag, if tag_id in parameters
         - 'tags': all tags, for tag-based navigation
         - 'pager': a pager on the comments
         - 'nav_list': a dict [year][month] for archives navigation
         - 'next_post': next blog post, to direct the user towards the next interesting post
        """
        date_begin, date_end = post.get('date_begin'), post.get('date_end')

        pager_url = "/blogpost/%s" % blog_post.id

        filtered_message = blog_post.website_message_ids.filtered(lambda message: message.path == False)
        pager = request.website.pager(
            url=pager_url,
            total=len(filtered_message),
            page=page,
            step=self._post_comment_per_page,
            scope=7
        )
        pager_begin = (page - 1) * self._post_comment_per_page
        pager_end = page * self._post_comment_per_page
        comments = filtered_message[pager_begin: pager_end]

        blog_url = QueryURL('', ['blog', 'tag'], blog=blog_post.blog_id, tag=None, date_begin=date_begin, date_end=date_end)

        if not blog_post.blog_id.id == blog.id:
            return request.redirect("/blog/%s/post/%s" % (slug(blog_post.blog_id), slug(blog_post)))

        tags = request.env['blog.tag'].search([])

        # Find next Post
        all_posts = request.env['blog.post'].search([('blog_id', '=', blog.id)])
        # should always return at least the current post
        current_blog_post_index = all_posts.ids.index(blog_post.id)
        next_post = all_posts[0 if current_blog_post_index == len(all_posts) - 1 \
                            else current_blog_post_index + 1]
        values = {
            'tags': tags,
            'blog': blog,
            'blog_post': blog_post,
            'blog_post_cover_properties': json.loads(blog_post.cover_properties),
            'main_object': blog_post,
            'nav_list': self.nav_list(blog),
            'enable_editor': enable_editor,
            'next_post': next_post,
            'next_post_cover_properties': json.loads(next_post.cover_properties) if next_post else {},
            'date': date_begin,
            'blog_url': blog_url,
            'pager': pager,
            'comments': comments,
        }
        response = request.website.render("website_blog.blog_post_complete", values)

        request.session[request.session_id] = request.session.get(request.session_id, [])
        if not (blog_post.id in request.session[request.session_id]):
            request.session[request.session_id].append(blog_post.id)
            # Increase counter
            blog_post.sudo().visits = blog_post.visits + 1
        return response

    def _blog_post_message(self, blog_post_id, message_content, **post):
        # for now, only portal and user can post comment on blog post.
        if request.env.uid == request.website.user_id.id:
            raise UserError(_('Public user cannot post comments on blog post.'))

        blog_post = request.env['blog.post'].browse(int(blog_post_id))
        message = blog_post.message_post(
            body=message_content,
            message_type='comment',
            subtype='mt_comment',
            author_id=request.env.user.partner_id.id,
            path=post.get('path', False))
        return message

    def _get_discussion_detail(self, messages, publish=False):
        values = []
        for message in messages:
            values.append({
                "id": message.id,
                "author_name": message.author_id.name,
                "author_image": message.author_id.image and \
                    ("data:image/png;base64,%s" % message.author_id.image) or \
                    '/website_blog/static/src/img/anonymous.png',
                "date": message.date,
                'body': html2plaintext(message.body),
                'website_published': message.website_published,
                'publish': publish,
            })
        return values

    @http.route(['/blog/post_discussion'], type='json', auth="public", website=True)
    def post_discussion(self, blog_post_id, **post):
        publish = request.env['res.users'].has_group('base.group_website_publisher')
        message = self._blog_post_message(blog_post_id, post.get('comment'), **post)
        return self._get_discussion_detail(message, publish)

    @http.route('/blog/<int:blog_id>/post/new', type='http', auth="public", website=True)
    def blog_post_create(self, blog_id, **post):
        new_blog_post = request.env['blog.post'].create({
            'blog_id': blog_id,
            'website_published': False,
        })
        return werkzeug.utils.redirect("/blog/%s/post/%s?enable_editor=1" % (slug(new_blog_post.blog_id), slug(new_blog_post)))

    @http.route('/blog/post_duplicate', type='http', auth="public", website=True, methods=['POST'])
    def blog_post_copy(self, blog_post_id, **post):
        """ Duplicate a blog.

        :param blog_post_id: id of the blog post currently browsed.

        :return redirect to the new blog created
        """
        blog_post = request.env['blog.post'].browse(int(blog_post_id))
        new_blog_post = blog_post.with_context(mail_create_nosubcribe=True).copy()
        return werkzeug.utils.redirect("/blog/%s/post/%s?enable_editor=1" % (slug(new_blog_post.blog_id), slug(new_blog_post)))

    @http.route('/blog/post_get_discussion/', type='json', auth="public", website=True)
    def discussion(self, post_id=0, path=None, count=False, **post):
        MailMessageSudo = request.env['mail.message'].sudo()
        domain = [('res_id', '=', int(post_id)), ('model', '=', 'blog.post'), ('path', '=', path)]
        #check current user belongs to website publisher group
        publish = request.env['res.users'].has_group('base.group_website_publisher')
        if not publish:
            domain.append(('website_published', '=', True))
        if count:
            return MailMessageSudo.search_count(domain)
        return self._get_discussion_detail(MailMessageSudo.search(domain), publish)

    @http.route('/blog/post_get_discussions/', type='json', auth="public", website=True)
    def discussions(self, post_id=0, paths=None, count=False, **post):
        ret = []
        for path in paths:
            result = self.discussion(post_id=post_id, path=path, count=count, **post)
            ret.append({"path": path, "val": result})
        return ret

    @http.route('/blog/post_change_background', type='json', auth="public", website=True)
    def change_bg(self, post_id=0, cover_properties={}, **post):
        if not post_id:
            return False
        return request.env['blog.post'].browse(int(post_id)).write({'cover_properties': json.dumps(cover_properties)})

    @http.route('/blog/get_user/', type='json', auth="public", website=True)
    def get_user(self, **post):
        return [False if request.session.uid else True]
