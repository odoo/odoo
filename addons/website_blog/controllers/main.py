# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug
import itertools
import pytz
import babel.dates
from collections import defaultdict

from odoo import http, fields, tools, models
from odoo.addons.http_routing.models.ir_http import slug, unslug
from odoo.addons.website.controllers.main import QueryURL
from odoo.http import request
from odoo.tools import html2plaintext
from odoo.tools.misc import get_lang
from odoo.tools import sql


class WebsiteBlog(http.Controller):
    _blog_post_per_page = 12  # multiple of 2,3,4
    _post_comment_per_page = 10

    def tags_list(self, tag_ids, current_tag):
        tag_ids = list(tag_ids)  # required to avoid using the same list
        if current_tag in tag_ids:
            tag_ids.remove(current_tag)
        else:
            tag_ids.append(current_tag)
        tag_ids = request.env['blog.tag'].browse(tag_ids)
        return ','.join(slug(tag) for tag in tag_ids)

    def nav_list(self, blog=None):
        dom = blog and [('blog_id', '=', blog.id)] or []
        if not request.env.user.has_group('website.group_website_designer'):
            dom += [('post_date', '<=', fields.Datetime.now())]
        groups = request.env['blog.post']._read_group(
            dom, groupby=['post_date:month'])

        locale = get_lang(request.env).code
        tzinfo = pytz.timezone(request.context.get('tz', 'utc') or 'utc')
        fmt = tools.DEFAULT_SERVER_DATETIME_FORMAT

        res = defaultdict(list)
        for [start] in groups:
            year = babel.dates.format_datetime(start, format='yyyy', tzinfo=tzinfo, locale=locale)
            res[year].append({
                'date_begin': start.strftime(fmt),
                'date_end': (start + models.READ_GROUP_TIME_GRANULARITY['month']).strftime(fmt),
                'month': babel.dates.format_datetime(start, format='MMMM', tzinfo=tzinfo, locale=locale),
                'year': year,
            })
        return res

    def _get_blog_post_search_options(self, blog=None, active_tags=None, date_begin=None, date_end=None, state=None, **post):
        return {
            'displayDescription': True,
            'displayDetail': False,
            'displayExtraDetail': False,
            'displayExtraLink': False,
            'displayImage': False,
            'allowFuzzy': not post.get('noFuzzy'),
            'blog': str(blog.id) if blog else None,
            'tag': ','.join([str(id) for id in active_tags.ids]),
            'date_begin': date_begin,
            'date_end': date_end,
            'state': state,
        }

    def _prepare_blog_values(self, blogs, blog=False, date_begin=False, date_end=False, tags=False, state=False, page=False, search=None, **post):
        """ Prepare all values to display the blogs index page or one specific blog"""
        BlogPost = request.env['blog.post']
        BlogTag = request.env['blog.tag']

        # prepare domain
        domain = request.website.website_domain()

        if blog:
            domain += [('blog_id', '=', blog.id)]

        if date_begin and date_end:
            domain += [("post_date", ">=", date_begin), ("post_date", "<=", date_end)]
        active_tag_ids = tags and [unslug(tag)[1] for tag in tags.split(',')] or []
        active_tags = BlogTag
        if active_tag_ids:
            active_tags = BlogTag.browse(active_tag_ids).exists()
            fixed_tag_slug = ",".join(slug(t) for t in active_tags)
            if fixed_tag_slug != tags:
                path = request.httprequest.full_path
                new_url = path.replace("/tag/%s" % tags, fixed_tag_slug and "/tag/%s" % fixed_tag_slug or "", 1)
                if new_url != path:  # check that really replaced and avoid loop
                    return request.redirect(new_url, 301)
            domain += [('tag_ids', 'in', active_tags.ids)]

        if request.env.user.has_group('website.group_website_designer'):
            count_domain = domain + [("website_published", "=", True), ("post_date", "<=", fields.Datetime.now())]
            published_count = BlogPost.search_count(count_domain)
            unpublished_count = BlogPost.search_count(domain) - published_count

            if state == "published":
                domain += [("website_published", "=", True), ("post_date", "<=", fields.Datetime.now())]
            elif state == "unpublished":
                domain += ['|', ("website_published", "=", False), ("post_date", ">", fields.Datetime.now())]
        else:
            domain += [("post_date", "<=", fields.Datetime.now())]

        use_cover = request.website.is_view_active('website_blog.opt_blog_cover_post')
        fullwidth_cover = request.website.is_view_active('website_blog.opt_blog_cover_post_fullwidth_design')

        # if blog, we show blog title, if use_cover and not fullwidth_cover we need pager + latest always
        offset = (page - 1) * self._blog_post_per_page
        if not blog and use_cover and not fullwidth_cover and not tags and not date_begin and not date_end and not search:
            offset += 1

        options = self._get_blog_post_search_options(
            blog=blog,
            active_tags=active_tags,
            date_begin=date_begin,
            date_end=date_end,
            state=state,
            **post
        )
        total, details, fuzzy_search_term = request.website._search_with_fuzzy("blog_posts_only", search,
            limit=page * self._blog_post_per_page, order="is_published desc, post_date desc, id asc", options=options)
        posts = details[0].get('results', BlogPost)
        first_post = BlogPost
        if posts and not blog and posts[0].website_published:
            first_post = posts[0]
        posts = posts[offset:offset + self._blog_post_per_page]

        url_args = dict()
        if search:
            url_args["search"] = search

        if date_begin and date_end:
            url_args["date_begin"] = date_begin
            url_args["date_end"] = date_end

        pager = tools.lazy(lambda: request.website.pager(
            url=request.httprequest.path.partition('/page/')[0],
            total=total,
            page=page,
            step=self._blog_post_per_page,
            url_args=url_args,
        ))

        if not blogs:
            all_tags = request.env['blog.tag']
        else:
            all_tags = tools.lazy(lambda: blogs.all_tags(join=True) if not blog else blogs.all_tags().get(blog.id, request.env['blog.tag']))
        tag_category = tools.lazy(lambda: sorted(all_tags.mapped('category_id'), key=lambda category: category.name.upper()))
        other_tags = tools.lazy(lambda: sorted(all_tags.filtered(lambda x: not x.category_id), key=lambda tag: tag.name.upper()))
        nav_list = tools.lazy(self.nav_list)
        # for performance prefetch the first post with the others
        post_ids = (first_post | posts).ids
        # and avoid accessing related blogs one by one
        posts.blog_id

        return {
            'date_begin': date_begin,
            'date_end': date_end,
            'first_post': first_post.with_prefetch(post_ids),
            'other_tags': other_tags,
            'tag_category': tag_category,
            'nav_list': nav_list,
            'tags_list': self.tags_list,
            'pager': pager,
            'posts': posts.with_prefetch(post_ids),
            'tag': tags,
            'active_tag_ids': active_tags.ids,
            'domain': domain,
            'state_info': state and {"state": state, "published": published_count, "unpublished": unpublished_count},
            'blogs': blogs,
            'blog': blog,
            'search': fuzzy_search_term or search,
            'search_count': total,
            'original_search': fuzzy_search_term and search,
        }

    @http.route([
        '/blog',
        '/blog/page/<int:page>',
        '/blog/tag/<string:tag>',
        '/blog/tag/<string:tag>/page/<int:page>',
        '''/blog/<model("blog.blog"):blog>''',
        '''/blog/<model("blog.blog"):blog>/page/<int:page>''',
        '''/blog/<model("blog.blog"):blog>/tag/<string:tag>''',
        '''/blog/<model("blog.blog"):blog>/tag/<string:tag>/page/<int:page>''',
    ], type='http', auth="public", website=True, sitemap=True)
    def blog(self, blog=None, tag=None, page=1, search=None, **opt):
        Blog = request.env['blog.blog']
        blogs = tools.lazy(lambda: Blog.search(request.website.website_domain(), order="create_date asc, id asc"))

        if not blog and len(blogs) == 1:
            url = QueryURL('/blog/%s' % slug(blogs[0]), search=search, **opt)()
            return request.redirect(url, code=302)

        date_begin, date_end = opt.get('date_begin'), opt.get('date_end')

        if tag and request.httprequest.method == 'GET':
            # redirect get tag-1,tag-2 -> get tag-1
            tags = tag.split(',')
            if len(tags) > 1:
                url = QueryURL('' if blog else '/blog', ['blog', 'tag'], blog=blog, tag=tags[0], date_begin=date_begin, date_end=date_end, search=search)()
                return request.redirect(url, code=302)

        values = self._prepare_blog_values(blogs=blogs, blog=blog, tags=tag, page=page, search=search, **opt)

        # in case of a redirection need by `_prepare_blog_values` we follow it
        if isinstance(values, werkzeug.wrappers.Response):
            return values

        if blog:
            values['main_object'] = blog
        values['blog_url'] = QueryURL('/blog', ['blog', 'tag'], blog=blog, tag=tag, date_begin=date_begin, date_end=date_end, search=search)

        return request.render("website_blog.blog_post_short", values)

    @http.route(['''/blog/<model("blog.blog"):blog>/feed'''], type='http', auth="public", website=True, sitemap=True)
    def blog_feed(self, blog, limit='15', **kwargs):
        v = {}
        v['blog'] = blog
        v['base_url'] = blog.get_base_url()
        v['posts'] = request.env['blog.post'].search([('blog_id', '=', blog.id)], limit=min(int(limit), 50), order="post_date DESC")
        v['html2plaintext'] = html2plaintext
        r = request.render("website_blog.blog_feed", v, headers=[('Content-Type', 'application/atom+xml')])
        return r

    @http.route([
        '''/blog/<model("blog.blog"):blog>/post/<model("blog.post"):blog_post>''',
    ], type='http', auth="public", website=True, sitemap=False)
    def old_blog_post(self, blog, blog_post, **post):
        # Compatibility pre-v14
        return request.redirect("/blog/%s/%s" % (slug(blog), slug(blog_post)), code=301)

    @http.route([
        '''/blog/<model("blog.blog"):blog>/<model("blog.post", "[('blog_id','=',blog.id)]"):blog_post>''',
    ], type='http', auth="public", website=True, sitemap=True)
    def blog_post(self, blog, blog_post, tag_id=None, page=1, enable_editor=None, **post):
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
        BlogPost = request.env['blog.post']
        date_begin, date_end = post.get('date_begin'), post.get('date_end')

        domain = request.website.website_domain()
        blogs = blog.search(domain, order="create_date, id asc")

        tag = None
        if tag_id:
            tag = request.env['blog.tag'].browse(int(tag_id))
        blog_url = QueryURL('', ['blog', 'tag'], blog=blog_post.blog_id, tag=tag, date_begin=date_begin, date_end=date_end)

        if not blog_post.blog_id.id == blog.id:
            return request.redirect("/blog/%s/%s" % (slug(blog_post.blog_id), slug(blog_post)), code=301)

        tags = request.env['blog.tag'].search([])

        # Find next Post
        blog_post_domain = [('blog_id', '=', blog.id)]
        if not request.env.user.has_group('website.group_website_designer'):
            blog_post_domain += [('post_date', '<=', fields.Datetime.now())]

        all_post = BlogPost.search(blog_post_domain)

        if blog_post not in all_post:
            return request.redirect("/blog/%s" % (slug(blog_post.blog_id)))

        # should always return at least the current post
        all_post_ids = all_post.ids
        current_blog_post_index = all_post_ids.index(blog_post.id)
        nb_posts = len(all_post_ids)
        next_post_id = all_post_ids[(current_blog_post_index + 1) % nb_posts] if nb_posts > 1 else None
        next_post = next_post_id and BlogPost.browse(next_post_id) or False

        values = {
            'tags': tags,
            'tag': tag,
            'blog': blog,
            'blog_post': blog_post,
            'blogs': blogs,
            'main_object': blog_post,
            'nav_list': self.nav_list(blog),
            'enable_editor': enable_editor,
            'next_post': next_post,
            'date': date_begin,
            'blog_url': blog_url,
        }
        response = request.render("website_blog.blog_post_complete", values)

        if blog_post.id not in request.session.get('posts_viewed', []):
            if sql.increment_fields_skiplock(blog_post, 'visits'):
                if not request.session.get('posts_viewed'):
                    request.session['posts_viewed'] = []
                request.session['posts_viewed'].append(blog_post.id)
                request.session.touch()
        return response
