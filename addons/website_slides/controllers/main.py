# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import itertools
import logging
import werkzeug

from odoo import http, modules, tools, _
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.osv import expression

from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website_profile.controllers.main import WebsiteProfile
from odoo.addons.website.models.ir_http import sitemap_qs2dom

_logger = logging.getLogger(__name__)


class WebsiteSlides(WebsiteProfile):
    _slides_per_page = 12
    _slides_per_list = 20
    _channel_order_by_criterion = {
        'vote': 'total_votes desc',
        'view': 'total_views desc',
        'date': 'create_date desc',
    }

    def sitemap_slide(env, rule, qs):
        Channel = env['slide.channel']
        dom = sitemap_qs2dom(qs=qs, route='/slides/', field=Channel._rec_name)
        dom += env['website'].get_current_website().website_domain()
        for channel in Channel.search(dom):
            loc = '/slides/%s' % slug(channel)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    def _set_viewed_slide(self, slide):
        if request.env.user._is_public() or slide.is_preview or not slide.channel_id.is_member:
            viewed_slides = request.session.setdefault('viewed_slides', list())
            if slide.id not in viewed_slides:
                slide.sudo().public_views += 1
                viewed_slides.append(slide.id)
                request.session['viewed_slides'] = viewed_slides
        else:
            slide.action_set_viewed()
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

    def _extract_channel_tag_search(self, **post):
        tags = request.env['slide.channel.tag']
        for key in (_key for _key in post if _key.startswith('channel_tag_group_id_')):
            group_id, tag_id = False, False
            try:
                group_id = int(key.lstrip('channel_tag_group_id_'))
                tag_id = int(post[key])
            except:
                pass
            else:
                search_tag = request.env['slide.channel.tag'].search([('id', '=', tag_id), ('group_id', '=', group_id)]).exists()
                if search_tag:
                    tags |= search_tag
        return tags

    def _build_channel_domain(self, base_domain, slide_type=None, **post):
        search_term = post.get('search')
        category_id = post.get('category_id')
        channel_tag_id = post.get('channel_tag_id')
        tags = self._extract_channel_tag_search(**post)

        domain = base_domain
        if search_term:
            domain = expression.AND([
                domain,
                ['|', ('name', 'ilike', search_term), ('description', 'ilike', search_term)]])
        if category_id:
            domain = expression.AND([domain, [('category_ids', 'in', [category_id])]])
        elif channel_tag_id:
            domain = expression.AND([domain, [('tag_ids', 'in', [channel_tag_id])]])
        elif tags:
            domain = expression.AND([domain, [('tag_ids', 'in', tags.ids)]])

        if slide_type and 'nbr_%ss' % slide_type in request.env['slide.channel']:
            domain = expression.AND([domain, [('nbr_%ss' % slide_type, '>', 0)]])
        return domain

    # --------------------------------------------------
    # MAIN / SEARCH
    # --------------------------------------------------

    @http.route('/slides', type='http', auth="public", website=True)
    def slides_channel_home(self, **post):
        """ Home page for eLearning platform. Is mainly a container page, does not allow search / filter. """
        domain = request.website.website_domain()
        channels_all = request.env['slide.channel'].search(domain)
        if not request.env.user._is_public():
            channels_my = channels_all.filtered(lambda channel: channel.completion > 0).sorted('completion', reverse=True)[:3]
        else:
            channels_my = request.env['slide.channel']
        channels_popular = channels_all.sorted('total_votes', reverse=True)[:3]
        channels_newest = channels_all.sorted('create_date', reverse=True)[:3]

        # fetch 'latests achievements' for non logged people
        if request.env.user._is_public():
            achievements = request.env['gamification.badge.user'].sudo().search([('badge_id.is_published', '=', True)], limit=5)
            challenges = None
            challenges_done = None
        else:
            achievements = None
            challenges = request.env['gamification.challenge'].sudo().search([
                ('category', '=', 'slides'),
                ('reward_id.is_published', '=', True)
            ], order='id asc', limit=5)
            challenges_done = request.env['gamification.badge.user'].sudo().search([
                ('challenge_id', 'in', challenges.ids),
                ('user_id', '=', request.env.user.id),
                ('badge_id.is_published', '=', True)
            ]).mapped('challenge_id')

        # fetch 'heroes of the week' for non logged people
        if request.env.user._is_public():
            users = request.env['res.users'].sudo().search([
                ('karma', '>', 0),
                ('website_published', '=', True)], limit=5, order='create_date desc')
        else:
            users = None

        return request.render('website_slides.courses_home', {
            'user': request.env.user,
            'is_public_user': request.website.is_public_user(),
            'channels_my': channels_my,
            'channels_popular': channels_popular,
            'channels_newest': channels_newest,
            'achievements': achievements,
            'users': users,
            'challenges': challenges,
            'challenges_done': challenges_done,
        })

    @http.route('/slides/all', type='http', auth="public", website=True)
    def slides_channel_all(self, slide_type=None, **post):
        """ Home page displaying a list of courses displayed according to some
        criterion and search terms.

         : param string slide_type: if provided, filter the slide.channels
           to contain at least one slide of type 'slide_type'
         : param dict post: post parameters, including
           * search_term: keywords entered in the search box, used to filter on slide content;
           * category_id: id of a slide.category;
           * channel_tag_id: id of a channel.tag;
        """
        domain = request.website.website_domain()
        domain = self._build_channel_domain(domain, slide_type=slide_type, **post)

        order = self._channel_order_by_criterion.get(post.get('sorting', 'date'), 'create_date desc')

        channels = request.env['slide.channel'].search(domain, order=order)
        channels_layouted = list(itertools.zip_longest(*[iter(channels)] * 4, fillvalue=None))

        tag_groups = request.env['slide.channel.tag.group'].search(['&', ('tag_ids', '!=', False), ('website_published', '=', True)])
        search_tags = self._extract_channel_tag_search(**post)

        return request.render('website_slides.courses_all', {
            'user': request.env.user,
            'is_public_user': request.website.is_public_user(),
            'channels_layouted': channels_layouted,
            'tag_groups': tag_groups,
            'search_term': post.get('search'),
            'search_tags': search_tags,
        })

    def _prepare_additional_channel_values(self, values, **kwargs):
        return values

    @http.route([
        '/slides/<model("slide.channel"):channel>',
        '/slides/<model("slide.channel"):channel>/page/<int:page>',
        '/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>',
        '/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>/page/<int:page>',
        '/slides/<model("slide.channel"):channel>/category/<model("slide.category"):category>',
        '/slides/<model("slide.channel"):channel>/category/<model("slide.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True, sitemap=sitemap_slide)
    def channel(self, channel, category=None, tag=None, page=1, slide_type=None, sorting=None, search=None, **kw):
        if not channel.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        domain = [('channel_id', '=', channel.id)]
        if not request.env.user.has_group('website.group_website_publisher'):
            domain = expression.AND([
                domain,
                ['&', ('website_published', '=', True), ('channel_id.website_published', '=', True)]
            ])

        pager_url = "/slides/%s" % (channel.id)
        pager_args = {}
        slide_types = dict(request.env['slide.slide']._fields['slide_type']._description_selection(request.env))

        if search:
            domain += [
                '|', '|', '|',
                ('name', 'ilike', search),
                ('description', 'ilike', search),
                ('index_content', 'ilike', search),
                ('html_content', 'ilike', search)]
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
                pager_url += "?slide_type=%s" % slide_type

        # sorting criterion
        actual_sorting = sorting if sorting and sorting in request.env['slide.slide']._order_by_strategy else channel.promote_strategy
        order = request.env['slide.slide']._order_by_strategy[actual_sorting]
        pager_args['sorting'] = actual_sorting

        pager_count = request.env['slide.slide'].sudo().search_count(domain)
        pager = request.website.pager(url=pager_url, total=pager_count, page=page,
                                      step=self._slides_per_page, scope=self._slides_per_page,
                                      url_args=pager_args)

        values = {
            'channel': channel,
            # search
            'search_category': category,
            'search_tag': tag,
            'search_slide_type': slide_type,
            'slide_types': slide_types,
            'sorting': actual_sorting,
            'search': search,
            # chatter
            'rating_avg': channel.rating_avg,
            'rating_count': channel.rating_count,
            # display data
            'user': request.env.user,
            'pager': pager,
            'is_public_user': request.website.is_public_user(),
            'is_slides_publisher': request.env.user.has_group('website.group_website_publisher'),
        }
        if not request.env.user._is_public():
            last_message_values = request.env['mail.message'].search([
                ('model', '=', channel._name),
                ('res_id', '=', channel.id),
                ('author_id', '=', request.env.user.partner_id.id),
                ('website_published', '=', True)
            ], order='write_date DESC', limit=1).read(['body', 'rating_value'])
            last_message_data = last_message_values[0] if last_message_values else {}
            values.update({
                'message_post_hash': channel._sign_token(request.env.user.partner_id.id),
                'message_post_pid': request.env.user.partner_id.id,
                'last_message_id': last_message_data.get('id'),
                'last_message': tools.html2plaintext(last_message_data.get('body', '')),
                'last_rating_value': last_message_data.get('rating_value'),
            })

        # Display uncategorized slides
        # fetch slides; done as sudo because we want to display all of them but
        # unreachable ones won't be clickable (+ slide controller will crash anyway)
        if not category:
            category_data = []
            for category in request.env['slide.slide'].sudo().read_group(domain, ['category_id'], ['category_id']):
                category_id, name = category.get('category_id') or (False, _('Uncategorized'))
                category_data.append({
                    'id': category_id,
                    'name': name,
                    'total_slides': category['category_id_count'],
                    'slides': request.env['slide.slide'].sudo().search(category['__domain'], limit=4, offset=0, order=order)
                })
        else:
            slides_sudo = request.env['slide.slide'].sudo().search(domain, limit=self._slides_per_page, offset=pager['offset'], order=order)
            category_data = [{
                'id': category.id,
                'name': category.name,
                'total_slides': len(slides_sudo),
                'slides': slides_sudo,
            }]
        values['slide_promoted'] = request.env['slide.slide'].sudo().search(domain, limit=1, order=order)
        values['category_data'] = category_data

        values = self._prepare_additional_channel_values(values, **kw)

        return request.render('website_slides.course_main', values)

    @http.route(['/slides/channel/add'], type='http', auth='user', methods=['POST'], website=True)
    def slide_channel_create(self, *args, **kw):
        channel = request.env['slide.channel'].create(self._slide_channel_prepare_values(**kw))
        return werkzeug.utils.redirect("/slides/%s" % (slug(channel)))

    def _slide_channel_prepare_values(self, **kw):
        # `tag_ids` is a string representing a list of int with coma. i.e.: '2,5,7'
        # We don't want to allow user to create tags and tag groups on the fly.
        tag_ids = []
        if kw.get('tag_ids'):
            tag_ids = [int(item) for item in kw['tag_ids'].split(',')]

        return {
            'name': kw['name'],
            'description': kw.get('description'),
            'channel_type': kw.get('channel_type', 'documentation'),
            'user_id': request.env.user.id,
            'tag_ids': [(6, 0, tag_ids)],
            'allow_comment': bool(kw.get('allow_comment')),
        }

    # --------------------------------------------------
    # SLIDE.SLIDE CONTOLLERS
    # --------------------------------------------------

    @http.route('''/slides/slide/<model("slide.slide", "[('website_id', 'in', (False, current_website_id))]"):slide>''', type='http', auth="public", website=True)
    def slide_view(self, slide, **kwargs):
        if not slide.channel_id.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        self._set_viewed_slide(slide)
        values = self._get_slide_detail(slide)
        # allow rating and comments
        if slide.channel_id.allow_comment:
            values.update({
                'message_post_hash': slide._generate_signed_token(request.env.user.partner_id.id),
                'message_post_pid': request.env.user.partner_id.id,
            })
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

    @http.route('/slides/slide/<int:slide_id>/get_image', type='http', auth="public", website=True, sitemap=False)
    def slide_get_image(self, slide_id, field='image_medium', width=0, height=0, crop=False, avoid_if_small=False, upper_limit=False):
        # Protect infographics by limiting access to 256px (large) images
        if field not in ('image_small', 'image_medium', 'image_large'):
            return werkzeug.exceptions.Forbidden()

        slide = request.env['slide.slide'].sudo().browse(slide_id).exists()
        if not slide:
            raise werkzeug.exceptions.NotFound()

        status, headers, content = request.env['ir.http'].sudo().binary_content(
            model='slide.slide', id=slide.id, field=field,
            default_mimetype='image/png')
        if status == 301:
            return request.env['ir.http']._response_by_status(status, headers, content)
        if status == 304:
            return werkzeug.wrappers.Response(status=304)

        if not content:
            content = self._get_default_avatar(field, headers, width, height)

        content = tools.limited_image_resize(
            content, width=width, height=height, crop=crop, upper_limit=upper_limit, avoid_if_small=avoid_if_small)

        image_base64 = base64.b64decode(content)
        headers.append(('Content-Length', len(image_base64)))
        response = request.make_response(image_base64, headers)
        response.status_code = status
        return response

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

    @http.route(['/slides/prepare_preview'], type='json', auth='user', methods=['POST'], website=True)
    def prepare_preview(self, **data):
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
            file_size = len(post['datas']) * 3 / 4  # base64
            if (file_size / 1024.0 / 1024.0) > 25:
                return {'error': _('File is too big. File size cannot exceed 25MB')}

        values = dict((fname, post[fname]) for fname in self._get_valid_slide_post_values() if post.get(fname))

        if post.get('category_id'):
            if post['category_id'][0] == 0:
                values['category_id'] = request.env['slide.category'].create({
                    'name': post['category_id'][1]['name'],
                    'channel_id': values.get('channel_id')}).id
            else:
                values['category_id'] = post['category_id'][0]

        values['is_preview'] = post.get('is_preview') == 'true'

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

        redirect_url = "/slides/slide/%s" % (slide.id)
        if slide.slide_type == 'webpage':
            redirect_url += "?enable_editor=1"
        return {'url': redirect_url}

    def _get_valid_slide_post_values(self):
        return ['name', 'url', 'tag_ids', 'slide_type', 'channel_id',
            'mime_type', 'datas', 'description', 'image', 'index_content', 'website_published']

    @http.route(['/slides/channel/tag/search_read'], type='json', auth='user', methods=['POST'], website=True)
    def slide_channel_tag_search_read(self, fields, domain):
        can_create = request.env['slide.channel.tag'].check_access_rights('create', raise_exception=False)
        return {
            'read_results': request.env['slide.channel.tag'].search_read(domain, fields),
            'can_create': can_create,
        }

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
            self._set_viewed_slide(slide)
            return request.render('website_slides.embed_slide', values)
        except AccessError: # TODO : please, make it clean one day, or find another secure way to detect
                            # if the slide can be embedded, and properly display the error message.
            return request.render('website_slides.embed_slide_forbidden', {})

    # --------------------------------------------------
    # PROFILE
    # --------------------------------------------------

    def _prepare_user_values(self, **kwargs):
        values = super(WebsiteSlides, self)._prepare_user_values(**kwargs)
        channel = self._get_channels(**kwargs)
        if channel:
            values['channel'] = channel
        return values

    def _get_channels(self, **kwargs):
        channels = []
        if kwargs.get('channel'):
            channels = kwargs['channel']
        elif kwargs.get('channel_id'):
            channels = request.env['slide.channel'].browse(int(kwargs['channel_id']))
        return channels

    def _prepare_user_slides_profile(self, user):
        courses = request.env['slide.channel.partner'].sudo().search([('partner_id', '=', user.partner_id.id)]).mapped('channel_id')
        values = {
            'uid': request.env.user.id,
            'user': user,
            'main_object': user,
            'courses': courses,
            'count_courses': len(courses),
            'is_profile_page': True,
            'badge_category': 'slides',
        }
        return values

    def _prepare_user_profile_values(self, user, **post):
        values = super(WebsiteSlides, self)._prepare_user_profile_values(user, **post)
        if post.get('channel_id'):
            values.update({'edit_button_url_param': 'channel_id=' + str(post['channel_id'])})
        channels = self._get_channels(**post)
        if not channels:
            channels = request.env['slide.channel'].search([])
        values.update(self._prepare_user_values(channel=channels[0] if len(channels) == 1 else True, **post))
        values.update(self._prepare_user_slides_profile(user))
        return values
