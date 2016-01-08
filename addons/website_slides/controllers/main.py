# -*- coding: utf-8 -*-
import base64
import logging
import werkzeug

from openerp.addons.web import http
from openerp.exceptions import AccessError, UserError
from openerp.http import request
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class website_slides(http.Controller):
    _slides_per_page = 12
    _slides_per_list = 20
    _order_by_criterion = {
        'date': 'date_published desc',
        'view': 'total_views desc',
        'vote': 'likes desc',
    }

    def _set_viewed_slide(self, slide, view_mode):
        slide_key = '%s_%s' % (view_mode, request.session_id)
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
            'is_public_user': request.env.user == request.website.user_id,
            'comments': slide.channel_id.can_see_full and slide.website_message_ids or [],
            'private': not slide.channel_id.can_see_full,
        }

    # --------------------------------------------------
    # MAIN / SEARCH
    # --------------------------------------------------

    @http.route('/slides', type='http', auth="public", website=True)
    def slides_index(self, *args, **post):
        """ Returns a list of available channels: if only one is available,
            redirects directly to its slides
        """
        channels = request.env['slide.channel'].search([], order='sequence, id')
        if not channels:
            return request.website.render("website_slides.channel_not_found")
        elif len(channels) == 1:
            return request.redirect("/slides/%s" % channels.id)
        return request.website.render('website_slides.channels', {
            'channels': channels,
            'user': request.env.user,
            'is_public_user': request.env.user == request.website.user_id
        })

    @http.route([
        '/slides/<model("slide.channel"):channel>',
        '/slides/<model("slide.channel"):channel>/page/<int:page>',

        '/slides/<model("slide.channel"):channel>/<string:slide_type>',
        '/slides/<model("slide.channel"):channel>/<string:slide_type>/page/<int:page>',

        '/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>',
        '/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>/page/<int:page>',

        '/slides/<model("slide.channel"):channel>/category/<model("slide.category"):category>',
        '/slides/<model("slide.channel"):channel>/category/<model("slide.category"):category>/page/<int:page>',

        '/slides/<model("slide.channel"):channel>/category/<model("slide.category"):category>/<string:slide_type>',
        '/slides/<model("slide.channel"):channel>/category/<model("slide.category"):category>/<string:slide_type>/page/<int:page>'],
        type='http', auth="public", website=True)
    def channel(self, channel, category=None, tag=None, page=1, slide_type=None, sorting='creation', search=None, **kw):
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
            'is_public_user': user == request.website.user_id,
            'display_channel_settings': not request.httprequest.cookies.get('slides_channel_%s' % (channel.id), False) and channel.can_see_full,
        }
        if search:
            values['search'] = search
            return request.website.render('website_slides.slides_search', values)

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
        return request.website.render('website_slides.home', values)

    # --------------------------------------------------
    # SLIDE.SLIDE CONTOLLERS
    # --------------------------------------------------

    @http.route('/slides/slide/<model("slide.slide"):slide>', type='http', auth="public", website=True)
    def slide_view(self, slide, **kwargs):
        values = self._get_slide_detail(slide)
        if not values.get('private'):
            self._set_viewed_slide(slide, 'slide')
        return request.website.render('website_slides.slide_detail_view', values)

    @http.route('''/slides/slide/<model("slide.slide", "[('datas', '!=', False), ('slide_type', '=', 'presentation')]"):slide>/pdf_content''', type='http', auth="public", website=True)
    def slide_get_pdf_content(self, slide):
        response = werkzeug.wrappers.Response()
        response.data = slide.datas and slide.datas.decode('base64') or ''
        response.mimetype = 'application/pdf'
        return response

    @http.route('/slides/slide/<model("slide.slide"):slide>/comment', type='http', auth="public", methods=['POST'], website=True)
    def slide_comment(self, slide, **post):
        """ Controller for message_post. Public user can post; their name and
        email is used to find or create a partner and post as admin with the
        right partner. Their comments are not published by default. Logged
        users can post as usual. """
        # TDE TODO :
        # - subscribe partner instead of user writing the message ?
        # - public user -> cannot create mail.message ?
        if not post.get('comment'):
            return werkzeug.utils.redirect(request.httprequest.referrer + "#discuss")
        # public user: check or find author based on email, do not subscribe public user
        # and do not publish their comments by default to avoid direct spam
        if request.uid == request.website.user_id.id:
            if not post.get('email'):
                return werkzeug.utils.redirect(request.httprequest.referrer + "#discuss")
            # TDE FIXME: public user has no right to create mail.message, should
            # be investigated - using SUPERUSER_ID meanwhile
            contextual_slide = slide.sudo().with_context(mail_create_nosubcribe=True)
            # TDE FIXME: check in mail_thread, find partner from emails should maybe work as public user
            partner_id = slide.sudo()._find_partner_from_emails([post.get('email')])[0]
            if partner_id:
                partner = request.env['res.partner'].sudo().browse(partner_id)
            else:
                partner = request.env['res.partner'].sudo().create({
                    'name': post.get('name', post['email']),
                    'email': post['email']
                })
            post_kwargs = {
                'author_id': partner.id,
                'website_published': False,
                'email_from': partner.email,
            }
        # logged user: as usual, published by default
        else:
            contextual_slide = slide
            post_kwargs = {}

        contextual_slide.message_post(
            body=post['comment'],
            message_type='comment',
            subtype='mt_comment',
            **post_kwargs
        )
        return werkzeug.utils.redirect(request.httprequest.referrer + "#discuss")

    @http.route('/slides/slide/<model("slide.slide"):slide>/download', type='http', auth="public", website=True)
    def slide_download(self, slide):
        if slide.download_security == 'public' or (slide.download_security == 'user' and request.session.uid):
            filecontent = base64.b64decode(slide.datas)
            disposition = 'attachment; filename=%s.pdf' % werkzeug.urls.url_quote(slide.name)
            return request.make_response(
                filecontent,
                [('Content-Type', 'application/pdf'),
                 ('Content-Length', len(filecontent)),
                 ('Content-Disposition', disposition)])
        elif not request.session.uid and slide.download_security == 'user':
            return werkzeug.utils.redirect('/web?redirect=/slides/slide/%s' % (slide.id))
        return request.website.render("website.403")

    @http.route('/slides/slide/<model("slide.slide"):slide>/promote', type='http', auth='public', website=True)
    def slide_set_promoted(self, slide):
        slide.channel_id.promoted_slide_id = slide.id
        return request.redirect("/slides/%s" % slide.channel_id.id)

    # JSONRPC
    @http.route('/slides/slide/like', type='json', auth="user", website=True)
    def slide_like(self, slide_id):
        slide = request.env['slide.slide'].browse(int(slide_id))
        slide.likes += 1
        return slide.likes

    @http.route('/slides/slide/dislike', type='json', auth="user", website=True)
    def slide_dislike(self, slide_id):
        slide = request.env['slide.slide'].browse(int(slide_id))
        slide.dislikes += 1
        return slide.dislikes

    @http.route(['/slides/slide/send_share_email'], type='json', auth='user', website=True)
    def slide_send_share_email(self, slide_id, email):
        slide = request.env['slide.slide'].browse(int(slide_id))
        result = slide.send_share_email(email)
        return result

    @http.route('/slides/slide/overlay', type='json', auth="public", website=True)
    def slide_get_next_slides(self, slide_id):
        slide = request.env['slide.slide'].browse(int(slide_id))
        slides_to_suggest = 9

        def slide_mapped_dict(slide):
            return {
                'img_src': '/web/image/slide.slide/%s/image_thumb' % (slide.id),
                'caption': slide.name,
                'url': slide.website_url
            }
        vals = map(slide_mapped_dict, slide.get_related_slides(slides_to_suggest))
        add_more_slide = slides_to_suggest - len(vals)
        if max(add_more_slide, 0):
            vals += map(slide_mapped_dict, slide.get_most_viewed_slides(add_more_slide))
        return vals

    # --------------------------------------------------
    # TOOLS
    # --------------------------------------------------

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
            preview['error'] = _('This video already exists in this channel <a target="_blank" href="/slides/slide/%s">click here to view it </a>' % existing_slide.id)
            return preview
        values = Slide._parse_document_url(data['url'], only_preview_fields=True)
        if values.get('error'):
            preview['error'] = _('Could not fetch data from url. Document or access right not available.\nHere is the received response: %s' % values['error'])
            return preview
        return values

    @http.route(['/slides/add_slide'], type='json', auth='user', methods=['POST'], website=True)
    def create_slide(self, *args, **post):
        payload = request.httprequest.content_length
        # payload is total request content size so it's not exact size of file.
        # already add client validation this is for double check if client alter.
        if (payload / 1024 / 1024 > 15):
            return {'error': _('File is too big. File size cannot exceed 15MB')}

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
        # otherwise client slide create dialog box continue processing even server fail to create a slide.
        try:
            slide_id = request.env['slide.slide'].create(values)
        except (UserError, AccessError) as e:
            _logger.error(e)
            return {'error': e.name}
        except Exception as e:
            _logger.error(e)
            return {'error': _('Internal server error, please try again later or contact administrator.\nHere is the error message: %s' % e.message)}
        return {'url': "/slides/slide/%s" % (slide_id.id)}

    # --------------------------------------------------
    # EMBED IN THIRD PARTY WEBSITES
    # --------------------------------------------------
    @http.route('/slides/embed/<int:slide_id>', type='http', auth='public', website=True)
    def slides_embed(self, slide_id, page="1", **kw):
        # Note : don't use the 'model' in the route (use 'slide_id'), otherwise if public cannot access the embedded
        # slide, the error will be the website.403 page instead of the one of the website_slides.embed_slide.
        # Do not forget the rendering here will be displayed in the embedded iframe

        # determine if it is embedded from external web page
        referrer_url = request.httprequest.headers.get('Referer', '')
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        is_embedded = referrer_url and not bool(base_url in referrer_url) or False
        # try accessing slide, and display to corresponding template
        try:
            slide = request.env['slide.slide'].browse(slide_id)
            if is_embedded:
                request.env['slide.embed'].sudo().add_embed_url(slide.id, referrer_url)
            values = self._get_slide_detail(slide)
            values['page'] = page
            values['is_embedded'] = is_embedded
            if not values.get('private'):
                self._set_viewed_slide(slide, 'embed')
            return request.website.render('website_slides.embed_slide', values)
        except AccessError: # TODO : please, make it clean one day, or find another secure way to detect
                            # if the slide can be embedded, and properly display the error message.
            slide = request.env['slide.slide'].sudo().browse(slide_id)
            return request.website.render('website_slides.embed_slide_forbidden', {'slide' : slide})
