# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import werkzeug

from odoo import http, _
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.osv import expression

from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website_profile.controllers.main import WebsiteProfile
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class WebsiteSlides(WebsiteProfile):
    _slides_per_page = 12
    _slides_per_list = 20
    _order_by_criterion = {
        'date': 'date_published desc',
        'view': 'total_views desc',
        'vote': 'likes desc',
    }

    def sitemap_slide(env, rule, qs):
        Channel = env['slide.channel']
        dom = sitemap_qs2dom(qs=qs, route='/slides/', field=Channel._rec_name)
        dom += env['website'].get_current_website().website_domain()
        for channel in Channel.search(dom):
            loc = '/slides/%s' % slug(channel)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    def _prepare_user_values(self, **kwargs):
        values = super(WebsiteSlides, self)._prepare_user_values(**kwargs)
        if kwargs.get('channel'):
            values['channel'] = kwargs.get('channel')
        elif kwargs.get('channel_id'):
            values['channel'] = request.env['slide.channel'].browse(kwargs.pop('channel_id'))
        return values

    def _set_viewed_slide(self, slide, view_mode):
        slide_key = '%s_%s' % (view_mode, request.session.sid)
        viewed_slides = request.session.setdefault(slide_key, list())
        if slide.id not in viewed_slides:
            if view_mode == 'slide':
                slide.sudo().slide_views += 1
            elif view_mode == 'embed':
                slide.sudo().embed_views += 1
            viewed_slides.append(slide.id)
            request.session[slide_key] = viewed_slides
        return True

    def _get_slide_detail(self, slide):
        most_viewed_slides = slide.get_most_viewed_slides(self._slides_per_list)
        related_slides = slide.get_related_slides(self._slides_per_list)
        return {
            'slide': slide,
            'most_viewed_slides': most_viewed_slides,
            'related_slides': related_slides,
            'user': request.env.user,
            'is_public_user': request.website.is_public_user(),
            'comments': slide.website_message_ids or [],
        }

    # --------------------------------------------------
    # MAIN / SEARCH
    # --------------------------------------------------

    @http.route('/slides', type='http', auth="public", website=True)
    def slides_index(self, *args, **post):
        """ Returns a list of available channels: if only one is available,
            redirects directly to its slides
        """
        domain = request.website.website_domain()
        # search bar
        search_term = post.get('search')
        if search_term:
            domain = expression.AND([domain, ['|', ('name', 'ilike', search_term), ('description', 'ilike', search_term)]])

        channels = request.env['slide.channel'].search(domain, order='sequence, id')
        if not channels:
            return request.render("website_slides.channel_not_found", {'search_term': search_term})
        elif len(channels) == 1 and not search_term:  # don't auto redirect to only result when searching
            return request.redirect("/slides/%s" % channels.id)
        return request.render('website_slides.channels', {
            'channels': channels,
            'user': request.env.user,
            'is_public_user': request.website.is_public_user(),
            'search_term': search_term,
        })

    @http.route([
        '''/slides/<model("slide.channel"):channel>''',
        '''/slides/<model("slide.channel"):channel>/page/<int:page>''',

        '''/slides/<model("slide.channel"):channel>/<string:slide_type>''',
        '''/slides/<model("slide.channel"):channel>/<string:slide_type>/page/<int:page>''',

        '''/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>''',
        '''/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>/page/<int:page>''',

        '''/slides/<model("slide.channel"):channel>/category/<model("slide.category"):category>''',
        '''/slides/<model("slide.channel"):channel>/category/<model("slide.category"):category>/page/<int:page>''',

        '''/slides/<model("slide.channel"):channel>/category/<model("slide.category"):category>/<string:slide_type>''',
        '''/slides/<model("slide.channel"):channel>/category/<model("slide.category"):category>/<string:slide_type>/page/<int:page>'''],
        type='http', auth="public", website=True, sitemap=sitemap_slide)
    def channel(self, channel, category=None, tag=None, page=1, slide_type=None, sorting='creation', search=None, **kw):
        if not channel.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        user = request.env.user
        Slide = request.env['slide.slide']
        domain = [('channel_id', '=', channel.id)]
        pager_url = "/slides/%s" % (channel.id)
        pager_args = {}

        if search:
            domain += [
                '|', '|',
                ('name', 'ilike', search),
                ('description', 'ilike', search),
                ('index_content', 'ilike', search)]
            pager_args['search'] = search
        else:
            if category:
                domain += [('category_id', '=', category.id)]
                pager_url += "/category/%s" % category.id
            elif tag:
                domain += [('tag_ids.id', '=', tag.id)]
                pager_url += "/tag/%s" % tag.id
            if slide_type:
                domain += [('slide_type', '=', slide_type)]
                pager_url += "/%s" % slide_type

        if not sorting or sorting not in self._order_by_criterion:
            sorting = 'date'
        order = self._order_by_criterion[sorting]
        pager_args['sorting'] = sorting

        pager_count = Slide.search_count(domain)
        pager = request.website.pager(url=pager_url, total=pager_count, page=page,
                                      step=self._slides_per_page, scope=self._slides_per_page,
                                      url_args=pager_args)

        slides = Slide.search(domain, limit=self._slides_per_page, offset=pager['offset'], order=order)
        values = {
            'channel': channel,
            'category': category,
            'slides': slides,
            'tag': tag,
            'slide_type': slide_type,
            'sorting': sorting,
            'user': user,
            'pager': pager,
            'is_public_user': request.website.is_public_user(),
            'rating_avg': channel.rating_avg,
            'rating_count': channel.rating_count,
        }
        if not request.env.user._is_public():
            last_message_values = request.env['mail.message'].search([('model', '=', channel._name), ('res_id', '=', channel.id), ('author_id', '=', user.partner_id.id), ('website_published', '=', True)], order='write_date DESC', limit=1).read(['body', 'rating_value'])
            last_message_data = last_message_values[0] if last_message_values else {}
            values.update({
                'message_post_hash': channel._sign_token(request.env.user.partner_id.id),
                'message_post_pid': request.env.user.partner_id.id,
                'last_message_id': last_message_data.get('id'),
                'last_message': html2plaintext(last_message_data.get('body', '')),
                'last_rating_value': last_message_data.get('rating_value'),
            })
        if search:
            values['search'] = search
            return request.render('website_slides.slides_search', values)

        # Display uncategorized slides
        if not slide_type and not category:
            category_datas = []
            for category in Slide.read_group(domain, ['category_id'], ['category_id']):
                category_id, name = category.get('category_id') or (False, _('Uncategorized'))
                category_datas.append({
                    'id': category_id,
                    'name': name,
                    'total': category['category_id_count'],
                    'slides': Slide.search(category['__domain'], limit=4, offset=0, order=order)
                })
            values.update({
                'category_datas': category_datas,
            })

        return request.render('website_slides.home', values)

    @http.route(['/slides/channel/add'], type='http', auth='user', methods=['POST'], website=True)
    def slide_channel_create(self, *args, **kw):
        channel = request.env['slide.channel'].create({
            'name': kw['name'],
            'description': kw.get('description'),
            'channel_type': kw.get('course_type', 'training'),
            'responsible_id': request.env.user.id
        })
        #TODO JEM: voir avec sbu si faut garder les url /courses
        #if channel.channel_type == 'training':
        #    return werkzeug.utils.redirect("/courses/%s" % (slug(channel)))
        return werkzeug.utils.redirect("/slides/%s" % (slug(channel)))

    # --------------------------------------------------
    # SLIDE.SLIDE CONTOLLERS
    # --------------------------------------------------

    @http.route('''/slides/slide/<model("slide.slide", "[('website_id', 'in', (False, current_website_id))]"):slide>''', type='http', auth="public", website=True)
    def slide_view(self, slide, **kwargs):
        if not slide.channel_id.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        values = self._get_slide_detail(slide)
        self._set_viewed_slide(slide, 'slide')
        return request.render('website_slides.slide_detail_view', values)

    @http.route('''/slides/slide/<model("slide.slide"):slide>/pdf_content''',
                type='http', auth="public", website=True, sitemap=False)
    def slide_get_pdf_content(self, slide):
        response = werkzeug.wrappers.Response()
        response.data = slide.datas and base64.b64decode(slide.datas) or b''
        response.mimetype = 'application/pdf'
        return response

    @http.route('''/slides/slide/<model("slide.slide"):slide>/download''', type='http', auth="public", website=True, sitemap=False)
    def slide_download(self, slide, **kw):
        slide = slide.sudo()
        if slide.download_security == 'public' or (slide.download_security == 'user' and request.env.user and request.env.user != request.website.user_id):
            filecontent = base64.b64decode(slide.datas)
            disposition = 'attachment; filename=%s.pdf' % werkzeug.urls.url_quote(slide.name)
            return request.make_response(
                filecontent,
                [('Content-Type', 'application/pdf'),
                 ('Content-Length', len(filecontent)),
                 ('Content-Disposition', disposition)])
        elif not request.session.uid and slide.download_security == 'user':
            return request.redirect('/web/login?redirect=/slides/slide/%s' % (slide.id))
        return request.render("website.403")

    @http.route('''/slides/slide/<model("slide.slide"):slide>/promote''', type='http', auth='user', website=True)
    def slide_set_promoted(self, slide, **kwargs):
        slide.channel_id.promoted_slide_id = slide.id
        return request.redirect("/slides/%s" % slide.channel_id.id)

    # JSONRPC
    @http.route('/slides/slide/like', type='json', auth="user", website=True)
    def slide_like(self, slide_id, upvote):
        if request.website.is_public_user():
            return {'error': 'public_user'}
        slide_partners = request.env['slide.slide.partner'].sudo().search([
            ('slide_id', '=', slide_id),
            ('partner_id', '=', request.env.user.partner_id.id)
        ])
        if (upvote and slide_partners.vote == 1) or (not upvote and slide_partners.vote == -1):
            return {'error': 'vote_done'}
        slide = request.env['slide.slide'].browse(int(slide_id))
        if upvote:
            slide.action_like()
        else:
            slide.action_dislike()
        slide.invalidate_cache()
        return slide.read(['likes', 'dislikes', 'user_vote'])[0]

    @http.route(['/slides/slide/send_share_email'], type='json', auth='user', website=True)
    def slide_send_share_email(self, slide_id, email):
        slide = request.env['slide.slide'].browse(int(slide_id))
        result = slide.send_share_email(email)
        return result

    # --------------------------------------------------
    # TOOLS
    # --------------------------------------------------

    @http.route(['/slides/channel/join'], type='json', auth='public', website=True)
    def slide_channel_join(self, channel_id):
        if request.website.is_public_user():
            return {'error': 'public_user'}
        success = request.env['slide.channel'].browse(channel_id).action_add_member()
        if not success:
            return {'error': 'join_done'}
        return success

    @http.route(['/slides/dialog_preview'], type='json', auth='user', methods=['POST'], website=True)
    def dialog_preview(self, **data):
        Slide = request.env['slide.slide']
        document_type, document_id = Slide._find_document_data_from_url(data['url'])
        preview = {}
        if not document_id:
            preview['error'] = _('Please enter valid youtube or google doc url')
            return preview
        existing_slide = Slide.search([('channel_id', '=', int(data['channel_id'])), ('document_id', '=', document_id)], limit=1)
        if existing_slide:
            preview['error'] = _('This video already exists in this channel <a target="_blank" href="/slides/slide/%s">click here to view it </a>') % existing_slide.id
            return preview
        values = Slide._parse_document_url(data['url'], only_preview_fields=True)
        if values.get('error'):
            preview['error'] = _('Could not fetch data from url. Document or access right not available.\nHere is the received response: %s') % values['error']
            return preview
        return values

    @http.route(['/slides/add_slide'], type='json', auth='user', methods=['POST'], website=True)
    def create_slide(self, *args, **post):
        # check the size only when we upload a file.
        if post.get('datas'):
            file_size = len(post['datas']) * 3 / 4 # base64
            if (file_size / 1024.0 / 1024.0) > 25:
                return {'error': _('File is too big. File size cannot exceed 25MB')}

        values = dict((fname, post[fname]) for fname in [
            'name', 'url', 'tag_ids', 'slide_type', 'channel_id',
            'mime_type', 'datas', 'description', 'image', 'index_content', 'website_published'] if post.get(fname))
        if post.get('category_id'):
            if post['category_id'][0] == 0:
                values['category_id'] = request.env['slide.category'].create({
                    'name': post['category_id'][1]['name'],
                    'channel_id': values.get('channel_id')}).id
            else:
                values['category_id'] = post['category_id'][0]

        # handle exception during creation of slide and sent error notification to the client
        # otherwise client slide create dialog box continue processing even server fail to create a slide
        try:
            channel = request.env['slide.channel'].browse(values['channel_id'])
            can_upload = channel.can_upload
            can_publish = channel.can_publish
        except (UserError, AccessError) as e:
            _logger.error(e)
            return {'error': e.name}
        else:
            if not can_upload:
                return {'error': _('You cannot upload on this channel.')}

        try:
            values['user_id'] = request.env.uid
            values['website_published'] = values.get('website_published', False) and can_publish
            slide = request.env['slide.slide'].sudo().create(values)
        except (UserError, AccessError) as e:
            _logger.error(e)
            return {'error': e.name}
        except Exception as e:
            _logger.error(e)
            return {'error': _('Internal server error, please try again later or contact administrator.\nHere is the error message: %s') % e}
        return {'url': "/slides/slide/%s" % (slide.id)}

    @http.route(['/slides/tag/search_read'], type='json', auth='user', methods=['POST'], website=True)
    def slide_tag_search_read(self, fields, domain):
        can_create = request.env['slide.tag'].check_access_rights('create', raise_exception=False)
        return {
            'read_results': request.env['slide.tag'].search_read(domain, fields),
            'can_create': can_create,
        }

    @http.route(['/slides/category/search_read'], type='json', auth='user', methods=['POST'], website=True)
    def slide_category_search_read(self, fields, domain):
        can_create = request.env['slide.category'].check_access_rights('create', raise_exception=False)
        return {
            'read_results': request.env['slide.category'].search_read(domain, fields),
            'can_create': can_create,
        }

    # --------------------------------------------------
    # EMBED IN THIRD PARTY WEBSITES
    # --------------------------------------------------
    @http.route('/slides/embed/<int:slide_id>', type='http', auth='public', website=True, sitemap=False)
    def slides_embed(self, slide_id, page="1", **kw):
        # Note : don't use the 'model' in the route (use 'slide_id'), otherwise if public cannot access the embedded
        # slide, the error will be the website.403 page instead of the one of the website_slides.embed_slide.
        # Do not forget the rendering here will be displayed in the embedded iframe

        # determine if it is embedded from external web page
        referrer_url = request.httprequest.headers.get('Referer', '')
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        is_embedded = referrer_url and not bool(base_url in referrer_url) or False
        # try accessing slide, and display to corresponding template
        try:
            slide = request.env['slide.slide'].browse(slide_id)
            if is_embedded:
                request.env['slide.embed'].sudo().add_embed_url(slide.id, referrer_url)
            values = self._get_slide_detail(slide)
            values['page'] = page
            values['is_embedded'] = is_embedded
            self._set_viewed_slide(slide, 'embed')
            return request.render('website_slides.embed_slide', values)
        except AccessError: # TODO : please, make it clean one day, or find another secure way to detect
                            # if the slide can be embedded, and properly display the error message.
            return request.render('website_slides.embed_slide_forbidden', {})

    # Profile
    # ---------------------------------------------------
    def _prepare_open_slide_user(self, user):
        courses = request.env['slide.channel.partner'].sudo().search([('partner_id', '=', user.partner_id.id)]).channel_id
        courses_completed = courses.filtered(lambda c: c.completed)
        courses_ongoing = courses - courses_completed

        values = {
            'uid': request.env.user.id,
            'user': user,
            'main_object': user,
            'courses': courses,
            'courses_completed': courses_completed,
            'courses_ongoing': courses_ongoing,
            'count_courses': len(courses),
            'is_profile_page': True,
        }
        return values

    @http.route(['/slides/user/<int:user_id>'], type='http', auth="public", website=True)
    def open_cross_slide_user(self, user_id=0, **post):
        user = request.env['res.users'].sudo().browse([user_id])

        if post.get('channel'):
            channels = post.get('channel')
        elif post.get('channel_id'):
            channels = request.env['slide.channel'].browse(int(post.get('channel_id')))
        else:
            channels = request.env['slide.channel'].search([])

        values = {
            'user': request.env.user,
            'is_public_user': request.env.user.id == request.website.user_id.id,
            'notifications': self._get_notifications(),
            'header': post.get('header', dict()),
            'searches': post.get('searches', dict()),
            'validation_email_sent': request.session.get('validation_email_sent', False),
            'validation_email_done': request.session.get('validation_email_done', False),
            'channel': channels[0] if len(channels) == 1 else True,
        }
        values.update(self._prepare_open_slide_user(user))

        return request.render("website_slides.user_detail_cross_full", values)

    @http.route(['/slides/<model("slide.channel"):channel>/user/<int:user_id>'], type='http', auth="public", website=True)
    def open_slide_user(self, channel, user_id=0, **post):
        user = request.env['res.users'].sudo().browse(user_id)
        current_user = request.env.user.sudo()

        # Users with high karma can see users with karma <= 0 for
        # moderation purposes, IFF they have posted something (see below)
        if (not user or (user.karma < 1 and current_user.karma < channel.karma_unlink_all)):
            return werkzeug.utils.redirect("/slides/%s" % slug(channel))
        values = self._prepare_user_values(channel=channel, **post)

        values.update(self._prepare_open_slide_user(user))
        return request.render("website_slides.user_detail_full", values)

    @http.route('/slides/user/edit', type='http', auth="user", website=True)
    def edit_slide_profile(self, **kwargs):
        countries = request.env['res.country'].search([])
        if kwargs.get('channel_id'):
            values = self._prepare_user_values(channel_id=int(kwargs.get('channel_id')), searches=kwargs)
        else:
            values = self._prepare_user_values(searches=kwargs)
        values.update({
            'email_required': kwargs.get('email_required'),
            'countries': countries,
            'notifications': self._get_notifications(),
        })
        return request.render("website_slides.edit_slides_profile_main", values)

    @http.route('/slides/user/<model("res.users"):user>/save', type='http', auth="user", methods=['POST'], website=True)
    def save_edited_profile_cross_slide(self, user, **kwargs):
        values = self._prepare_save_edited_profile_values(user, **kwargs)
        user.write(values)
        return werkzeug.utils.redirect("/slides/user/%d" % (user.id))

    @http.route('/slides/<model("slide.channel"):channel>/user/<model("res.users"):user>/save', type='http', auth="user", methods=['POST'], website=True)
    def save_edited_profile_slide(self, channel, user, **kwargs):
        values = self._prepare_save_edited_profile_values(user, **kwargs)
        user.write(values)
        return werkzeug.utils.redirect("/slides/user/%d?channel_id=%d" % (user.id, channel.id))

    # Badges
    # --------------------------------------------------

    # Do we have to create badges for slides ? or use the forum badges ?
    @http.route('''/slides/<model("slide.channel", "[('website_id', 'in', (False, current_website_id))]"):channel>/badge''', type='http', auth="public", website=True)
    def slides_badges(self, channel, **searches):
        Badge = request.env['gamification.badge']
        # badges = Badge.sudo().search([('challenge_ids.category', '=', 'slides')])
        badges = Badge.sudo().search([])
        badges = sorted(badges, key=lambda b: b.stat_count_distinct, reverse=True)
        values = self._prepare_user_values(channel=channel, searches={'badges': True})
        values.update({
            'badges': badges,
        })
        return request.render("website_profile.badge_main", values)
