# -*- coding: utf-8 -*-
import base64
import logging

import werkzeug

from openerp.http import request
from openerp.addons.web import http
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class website_slides(http.Controller):
    _slides_per_page = 12
    _slides_per_list = 20

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
        if slide.channel_id.visibility == 'partial' and not len(slide.channel_id.group_ids & request.env.user.groups_id):
            return {
                'private_slide': slide,
                'private': True,
                'most_viewed_slides': most_viewed_slides,
                'related_slides': related_slides
            }
        return {
            'slide': slide,
            'user': request.env.user,
            'is_public_user': request.env.user == request.website.user_id,
            'comments': slide.website_message_ids,
            'most_viewed_slides': most_viewed_slides,
            'related_slides': related_slides,
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
            domain += ['|', '|', ('name', 'ilike', search), ('description', 'ilike', search), ('index_content', 'ilike', search)]
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

        if sorting == 'date':
            order = 'date_published desc'
        elif sorting == 'view':
            order = 'total_views desc'
        elif sorting == 'vote':
            order = 'likes desc'
        else:
            sorting = 'date'
            order = 'date_published desc'
        pager_args['sorting'] = sorting

        access_group = channel.group_ids
        upload_group = channel.upload_group_ids
        user_group = user.groups_id

        channel_access = True
        if channel.visibility in ('private', 'partial'):
            channel_access = access_group & user_group and True or False

        # if no upload group define then anyone can upload who has channel access right
        upload_access = len(upload_group & user_group) if upload_group else True

        pager_count = Slide.search_count(domain)
        pager = request.website.pager(url=pager_url, total=pager_count, page=page,
                                      step=self._slides_per_page, scope=self._slides_per_page,
                                      url_args=pager_args)

        slides = Slide.search(domain, limit=self._slides_per_page, offset=pager['offset'], order=order)

        values = {
            'channel': channel,
            'slides': slides,
            'tag': tag,
            'user': user,
            'all_count': pager_count,
            'pager': pager,
            'slide_type': slide_type,
            'sorting': sorting,
            'category': category,
            'is_public_user': user == request.website.user_id,
            'can_upload': channel_access and upload_access
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
    def slide_view(self, slide):
        values = self._get_slide_detail(slide)
        if not values.get('private'):
            self._set_viewed_slide(slide, 'slide')
        return request.website.render('website_slides.slide_detail_view', values)

    @http.route('/slides/slide/<model("slide.slide"):slide>/pdf_content', type='http', auth="public", website=True)
    def slide_get_pdf_content(self, slide):
        response = werkzeug.wrappers.Response()
        response.data = slide.datas.decode('base64')
        response.mimetype = 'application/pdf'
        return response

    @http.route('/slides/slide/<model("slide.slide"):slide>/comment', type='http', auth="public", methods=['POST'], website=True)
    def slide_comment(self, slide, **post):
        Partner = request.env['res.partner']
        partner_ids = False

        # TODO: make website_published False by default and write an method to send email with random back link,
        # which will post all comments posted with that email address
        website_published = False

        if post.get('comment'):
            if request.uid != request.website.user_id.id:
                partner_ids = [request.env.user.partner_id]
                website_published = True
            else:
                partner_ids = Partner.sudo().search([('email', '=', post.get('email'))])
                if not partner_ids or not partner_ids[0]:
                    partner_ids = [Partner.sudo().create({
                        'name': post.get('name'),
                        'email': post.get('email')
                    })]

            if partner_ids:
                slide.sudo().with_context(mail_create_nosubcribe=True).message_post(
                    body=post.get('comment'),
                    type='comment',
                    subtype='mt_comment',
                    author_id=partner_ids[0].id,
                    website_published=website_published
                )

        return werkzeug.utils.redirect(request.httprequest.referrer + "#discuss")

    @http.route('/slides/slide/<model("slide.slide"):slide>/like', type='json', auth="public", website=True)
    def slide_like(self, slide, **post):
        slide.likes += 1
        return slide.likes

    @http.route('/slides/slide/<model("slide.slide"):slide>/dislike', type='json', auth="public", website=True)
    def slide_dislike(self, slide, **post):
        slide.dislikes += 1
        return slide.dislikes

    @http.route(['/slides/slide/<model("slide.slide"):slide>/send_share_email'], type='json', auth='user', methods=['POST'], website=True)
    def slide_send_share_email(self, slide, email):
        result = slide.send_share_email(email)
        return result

    @http.route('/slides/slide/<model("slide.slide"):slide>/overlay', type='json', auth="public", website=True)
    def slide_get_next_slides(self, slide):
        slides_to_suggest = 9

        def slide_mapped_dict(slide):
            return {
                'img_src': '/website/image/slide.slide/%s/image_thumb' % (slide.id),
                'caption': slide.name,
                'url': slide.share_url
            }
        vals = map(slide_mapped_dict, slide.get_related_slides(slides_to_suggest))
        add_more_slide = slides_to_suggest - len(vals)
        if max(add_more_slide, 0):
            vals += map(slide_mapped_dict, slide.get_most_viewed_slides(add_more_slide))
        return vals

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
        if not values:
            preview['error'] = _('Could not fetch data from url. Document or access right not available')
            return preview
        return values

    @http.route(['/slides/add_slide'], type='json', auth='user', methods=['POST'], website=True)
    def create_slide(self, *args, **post):
        payload = request.httprequest.content_length
        # payload is total request content size so it's not exact size of file.
        # already add client validation this is for double check if client alter.
        if (payload / 1024 / 1024 > 17):
            return {'error': _('File is too big.')}

        # TDE FIXME: move as a constraint
        # if request.env['slide.slide'].search([('name', '=', post['name']), ('channel_id', '=', post['channel_id'])]):
        #     return {
        #         'error': _('This title already exists in the channel, rename and try again.')
        #     }

        values = dict((fname, post[fname]) for fname in ['name', 'url', 'tag_ids', 'slide_type', 'channel_id',
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
        except Exception as e:
            _logger.error(e)
            return {'error': _('Internal server error, please try again later or contact administrator.')}
        return {'url': "/slides/slide/%s" % (slide_id.id)}

    # --------------------------------------------------
    # EMBED IN THIRD PARTY WEBSITES
    # --------------------------------------------------

    @http.route('/slides/embed/count', type='http', methods=['POST'], auth='public', website=True)
    def slides_embed_count(self, slide, url):
        request.env['slide.embed'].sudo().add_embed_url(slide, url)

    @http.route('/slides/embed/<model("slide.slide"):slide>', type='http', auth='public', website=True)
    def slides_embed(self, slide, page="1"):
        values = self._get_slide_detail(slide)
        values['page'] = page
        if not values.get('private'):
            self._set_viewed_slide(slide, 'embed')
        return request.website.render('website_slides.embed_slide', values)
