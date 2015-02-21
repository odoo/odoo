# -*- coding: utf-8 -*-

import datetime
import werkzeug

from openerp import tools
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models.website import slug
from openerp.osv.orm import browse_record
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp.tools import html2plaintext


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
                if isinstance(value, browse_record):
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


class WebsitePortal(http.Controller):
    _portal_post_per_page = 20
    _post_comment_per_page = 10

    def nav_list(self):
        portal_post_obj = request.registry['portal.post']
        groups = portal_post_obj.read_group(
            request.cr, request.uid, [], ['name', 'create_date'],
            groupby="create_date", orderby="create_date desc", context=request.context)
        for group in groups:
            begin_date = datetime.datetime.strptime(group['__domain'][0][2], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            end_date = datetime.datetime.strptime(group['__domain'][1][2], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            group['date_begin'] = '%s' % datetime.date.strftime(begin_date, tools.DEFAULT_SERVER_DATE_FORMAT)
            group['date_end'] = '%s' % datetime.date.strftime(end_date, tools.DEFAULT_SERVER_DATE_FORMAT)
        return groups

    @http.route([
        '/portal',
        '/portal/page/<int:page>',
    ], type='http', auth="public", website=True)
    def portals(self, page=1, **post):
        cr, uid, context = request.cr, request.uid, request.context
        portal_obj = request.registry['portal.post']
        total = portal_obj.search(cr, uid, [], count=True, context=context)
        pager = request.website.pager(
            url='/portal',
            total=total,
            page=page,
            step=self._portal_post_per_page,
        )
        post_ids = portal_obj.search(cr, uid, [], offset=(page-1)*self._portal_post_per_page, limit=self._portal_post_per_page, context=context)
        posts = portal_obj.browse(cr, uid, post_ids, context=context)
        portal_url = QueryURL('', ['portal', 'tag'])
        return request.website.render("website_portal.latest_portals", {
            'posts': posts,
            'pager': pager,
            'portal_url': portal_url,
        })

    @http.route([
        '/portal/<model("portal.portal"):portal>',
        '/portal/<model("portal.portal"):portal>/page/<int:page>',
        '/portal/<model("portal.portal"):portal>/tag/<model("portal.tag"):tag>',
        '/portal/<model("portal.portal"):portal>/tag/<model("portal.tag"):tag>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def portal(self, portal=None, tag=None, page=1, **opt):
        """ Prepare all values to display the portal.

        :return dict values: values for the templates, containing

         - 'portal': current portal
         - 'portals': all portals for navigation
         - 'pager': pager of posts
         - 'tag': current tag
         - 'tags': all tags, for navigation
         - 'nav_list': a dict [year][month] for archives navigation
         - 'date': date_begin optional parameter, used in archives navigation
         - 'portal_url': help object to create URLs
        """
        date_begin, date_end = opt.get('date_begin'), opt.get('date_end')

        cr, uid, context = request.cr, request.uid, request.context
        portal_post_obj = request.registry['portal.post']

        portal_obj = request.registry['portal.portal']
        portal_ids = portal_obj.search(cr, uid, [], order="create_date asc", context=context)
        portals = portal_obj.browse(cr, uid, portal_ids, context=context)

        domain = []
        if portal:
            domain += [('portal_id', '=', portal.id)]
        if tag:
            domain += [('tag_ids', 'in', tag.id)]
        if date_begin and date_end:
            domain += [("create_date", ">=", date_begin), ("create_date", "<=", date_end)]

        portal_url = QueryURL('', ['portal', 'tag'], portal=portal, tag=tag, date_begin=date_begin, date_end=date_end)
        post_url = QueryURL('', ['portalpost'], tag_id=tag and tag.id or None, date_begin=date_begin, date_end=date_end)

        portal_post_ids = portal_post_obj.search(cr, uid, domain, order="create_date desc", context=context)
        portal_posts = portal_post_obj.browse(cr, uid, portal_post_ids, context=context)

        pager = request.website.pager(
            url=portal_url(),
            total=len(portal_posts),
            page=page,
            step=self._portal_post_per_page,
        )
        pager_begin = (page - 1) * self._portal_post_per_page
        pager_end = page * self._portal_post_per_page
        portal_posts = portal_posts[pager_begin:pager_end]

        tags = portal.all_tags()[portal.id]

        values = {
            'portal': portal,
            'portals': portals,
            'tags': tags,
            'tag': tag,
            'portal_posts': portal_posts,
            'pager': pager,
            'nav_list': self.nav_list(),
            'portal_url': portal_url,
            'post_url': post_url,
            'date': date_begin,
        }
        response = request.website.render("website_portal.portal_post_short", values)
        return response

    @http.route([
            '''/portal/<model("portal.portal"):portal>/post/<model("portal.post", "[('portal_id','=',portal[0])]"):portal_post>''',
    ], type='http', auth="public", website=True)
    def portal_post(self, portal, portal_post, tag_id=None, page=1, enable_editor=None, **post):
        """ Prepare all values to display the portal.

        :return dict values: values for the templates, containing

         - 'portal_post': browse of the current post
         - 'portal': browse of the current portal
         - 'portals': list of browse records of portals
         - 'tag': current tag, if tag_id in parameters
         - 'tags': all tags, for tag-based navigation
         - 'pager': a pager on the comments
         - 'nav_list': a dict [year][month] for archives navigation
         - 'next_post': next portal post, to direct the user towards the next interesting post
        """
        cr, uid, context = request.cr, request.uid, request.context
        tag_obj = request.registry['portal.tag']
        portal_post_obj = request.registry['portal.post']
        date_begin, date_end = post.get('date_begin'), post.get('date_end')

        pager_url = "/portalpost/%s" % portal_post.id

        pager = request.website.pager(
            url=pager_url,
            total=len(portal_post.website_message_ids),
            page=page,
            step=self._post_comment_per_page,
            scope=7
        )
        pager_begin = (page - 1) * self._post_comment_per_page
        pager_end = page * self._post_comment_per_page
        comments = portal_post.website_message_ids[pager_begin:pager_end]

        tag = None
        if tag_id:
            tag = request.registry['portal.tag'].browse(request.cr, request.uid, int(tag_id), context=request.context)
        post_url = QueryURL('', ['portalpost'], portalpost=portal_post, tag_id=tag_id, date_begin=date_begin, date_end=date_end)
        portal_url = QueryURL('', ['portal', 'tag'], portal=portal_post.portal_id, tag=tag, date_begin=date_begin, date_end=date_end)

        if not portal_post.portal_id.id == portal.id:
            return request.redirect("/portal/%s/post/%s" % (slug(portal_post.portal_id), slug(portal_post)))

        tags = tag_obj.browse(cr, uid, tag_obj.search(cr, uid, [], context=context), context=context)

        # Find next Post
        visited_portals = request.httprequest.cookies.get('visited_portals') or ''
        visited_ids = filter(None, visited_portals.split(','))
        visited_ids = map(lambda x: int(x), visited_ids)
        if portal_post.id not in visited_ids:
            visited_ids.append(portal_post.id)
        next_post_id = portal_post_obj.search(cr, uid, [
            ('id', 'not in', visited_ids),
        ], order='ranking desc', limit=1, context=context)
        if not next_post_id:
            next_post_id = portal_post_obj.search(cr, uid, [('id', '!=', portal.id)], order='ranking desc', limit=1, context=context)
        next_post = next_post_id and portal_post_obj.browse(cr, uid, next_post_id[0], context=context) or False

        values = {
            'tags': tags,
            'tag': tag,
            'portal': portal,
            'portal_post': portal_post,
            'main_object': portal_post,
            'nav_list': self.nav_list(),
            'enable_editor': enable_editor,
            'next_post': next_post,
            'date': date_begin,
            'post_url': post_url,
            'portal_url': portal_url,
            'pager': pager,
            'comments': comments,
        }
        response = request.website.render("website_portal.portal_post_complete", values)
        response.set_cookie('visited_portals', ','.join(map(str, visited_ids)))

        request.session[request.session_id] = request.session.get(request.session_id, [])
        if not (portal_post.id in request.session[request.session_id]):
            request.session[request.session_id].append(portal_post.id)
            # Increase counter
            portal_post_obj.write(cr, SUPERUSER_ID, [portal_post.id], {
                'visits': portal_post.visits+1,
            },context=context)
        return response

    def _portal_post_message(self, user, portal_post_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        portal_post = request.registry['portal.post']
        partner_obj = request.registry['res.partner']

        if uid != request.website.user_id.id:
            partner_ids = [user.partner_id.id]
        else:
            partner_ids = portal_post._find_partner_from_emails(
                cr, SUPERUSER_ID, 0, [post.get('email')], context=context)
            if not partner_ids or not partner_ids[0]:
                partner_ids = [partner_obj.create(cr, SUPERUSER_ID, {'name': post.get('name'), 'email': post.get('email')}, context=context)]

        message_id = portal_post.message_post(
            cr, SUPERUSER_ID, int(portal_post_id),
            body=post.get('comment'),
            type='comment',
            subtype='mt_comment',
            author_id=partner_ids[0],
            path=post.get('path', False),
            context=context)
        return message_id

    @http.route(['/portalpost/comment'], type='http', auth="public", methods=['POST'], website=True)
    def portal_post_comment(self, portal_post_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        if post.get('comment'):
            user = request.registry['res.users'].browse(cr, uid, uid, context=context)
            portal_post = request.registry['portal.post']
            portal_post.check_access_rights(cr, uid, 'read')
            self._portal_post_message(user, portal_post_id, **post)
        return werkzeug.utils.redirect(request.httprequest.referrer + "#comments")

    def _get_discussion_detail(self, ids, publish=False, **post):
        cr, uid, context = request.cr, request.uid, request.context
        values = []
        mail_obj = request.registry.get('mail.message')
        for message in mail_obj.browse(cr, SUPERUSER_ID, ids, context=context):
            values.append({
                "id": message.id,
                "author_name": message.author_id.name,
                "author_image": message.author_id.image and \
                    ("data:image/png;base64,%s" % message.author_id.image) or \
                    '/website_portal/static/src/img/anonymous.png',
                "date": message.date,
                'body': html2plaintext(message.body),
                'website_published' : message.website_published,
                'publish' : publish,
            })
        return values

    @http.route(['/portalpost/post_discussion'], type='json', auth="public", website=True)
    def post_discussion(self, portal_post_id, **post):
        cr, uid, context = request.cr, request.uid, request.context
        publish = request.registry['res.users'].has_group(cr, uid, 'base.group_website_publisher')
        user = request.registry['res.users'].browse(cr, uid, uid, context=context)
        id = self._portal_post_message(user, portal_post_id, **post)
        return self._get_discussion_detail([id], publish, **post)

    @http.route('/portalpost/new', type='http', auth="public", website=True)
    def portal_post_create(self, portal_id, **post):
        cr, uid, context = request.cr, request.uid, request.context
        new_portal_post_id = request.registry['portal.post'].create(cr, uid, {
            'portal_id': portal_id,
            'name': _("Portal Post Title"),
            'subtitle': _("Subtitle"),
            'content': '',
            'website_published': False,
        }, context=context)
        new_portal_post = request.registry['portal.post'].browse(cr, uid, new_portal_post_id, context=context)
        return werkzeug.utils.redirect("/portal/%s/post/%s?enable_editor=1" % (slug(new_portal_post.portal_id), slug(new_portal_post)))

    @http.route('/portalpost/duplicate', type='http', auth="public", website=True)
    def portal_post_copy(self, portal_post_id, **post):
        """ Duplicate a portal.

        :param portal_post_id: id of the portal post currently browsed.

        :return redirect to the new portal created
        """
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context, mail_create_nosubscribe=True)
        nid = request.registry['portal.post'].copy(cr, uid, portal_post_id, {}, context=create_context)
        new_portal_post = request.registry['portal.post'].browse(cr, uid, nid, context=context)
        post = request.registry['portal.post'].browse(cr, uid, nid, context)
        return werkzeug.utils.redirect("/portal/%s/post/%s?enable_editor=1" % (slug(post.portal_id), slug(new_portal_post)))

    @http.route('/portalpost/get_discussion/', type='json', auth="public", website=True)
    def discussion(self, post_id=0, path=None, count=False, **post):
        cr, uid, context = request.cr, request.uid, request.context
        mail_obj = request.registry.get('mail.message')
        domain = [('res_id', '=', int(post_id)), ('model', '=', 'portal.post'), ('path', '=', path)]
        #check current user belongs to website publisher group
        publish = request.registry['res.users'].has_group(cr, uid, 'base.group_website_publisher')
        if not publish:
            domain.append(('website_published', '=', True))
        ids = mail_obj.search(cr, SUPERUSER_ID, domain, count=count)
        if count:
            return ids
        return self._get_discussion_detail(ids, publish, **post)

    @http.route('/portalpost/get_discussions/', type='json', auth="public", website=True)
    def discussions(self, post_id=0, paths=None, count=False, **post):
        ret = []
        for path in paths:
            result = self.discussion(post_id=post_id, path=path, count=count, **post)
            ret.append({"path": path, "val": result})
        return ret

    @http.route('/portalpost/change_background', type='json', auth="public", website=True)
    def change_bg(self, post_id=0, image=None, **post):
        if not post_id:
            return False
        return request.registry['portal.post'].write(request.cr, request.uid, [int(post_id)], {'background_image': image}, request.context)

    @http.route('/portal/get_user/', type='json', auth="public", website=True)
    def get_user(self, **post):
        return [False if request.session.uid else True]
