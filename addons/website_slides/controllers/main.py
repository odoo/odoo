# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from dateutil.relativedelta import relativedelta

import base64
import json
import logging
import math
import werkzeug

from odoo import fields, http, tools, _
from odoo.addons.http_routing.models.ir_http import slug, unslug
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website_profile.controllers.main import WebsiteProfile
from odoo.exceptions import AccessError, ValidationError, UserError, MissingError
from odoo.http import request, Response
from odoo.osv import expression
from odoo.tools import consteq, email_split

_logger = logging.getLogger(__name__)


def handle_wslide_error(exception):
    if isinstance(exception, AccessError):
        return request.redirect("/slides?invite_error=no_rights", 302)


class WebsiteSlides(WebsiteProfile):
    _slides_per_page = 12
    _slides_per_aside = 20
    _slides_per_category = 3
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

    def _slide_render_context_base(self):
        return {
            # current user info
            'user': request.env.user,
            'is_public_user': request.website.is_public_user(),
            # tools
            '_slugify_tags': self._slugify_tags,
        }

    # SLIDE UTILITIES
    # --------------------------------------------------

    def _fetch_slide(self, slide_id):
        slide = request.env['slide.slide'].browse(int(slide_id)).exists()
        if not slide:
            return {'error': 'slide_wrong'}
        try:
            slide.check_access_rights('read')
            slide.check_access_rule('read')
        except AccessError:
            return {'error': 'slide_access'}
        return {'slide': slide}

    def _set_viewed_slide(self, slide, quiz_attempts_inc=False):
        if not slide.channel_id.is_member:
            if not isinstance(request.session.get('viewed_slides'), dict):
                # Compatibility layer with Odoo 15.0,
                # where `viewed_slides` are stored as `list` in sessions.
                # For performance concerns, `viewed_slides` is changed to a dict,
                # but sessions coming from Odoo 15.0 after an upgrade should still be compatible.
                # This compatibility layer regarding `viewed_slides` must remain from Odoo 16.0 and above,
                # as this is possible to do a jump of multiple versions in one go,
                # and carry the sessions with the upgrade.
                # e.g. upgrade from Odoo 15.0 to 18.0.
                request.session.viewed_slides = dict.fromkeys(request.session.get('viewed_slides', []), 1)
            viewed_slides = request.session['viewed_slides']
            if slide.id not in viewed_slides:
                if tools.sql.increment_fields_skiplock(slide, 'public_views', 'total_views'):
                    viewed_slides[slide.id] = 1
                    request.session.touch()
        else:
            slide.action_set_viewed(quiz_attempts_inc=quiz_attempts_inc)
        return True

    def _slide_mark_completed(self, slide):
        # quiz use their specific mechanism to be marked as done
        if slide.slide_category == 'quiz' or slide.question_ids:
            raise UserError(_("Slide with questions must be marked as done when submitting all good answers "))
        if not slide.can_self_mark_completed:
            raise werkzeug.exceptions.Forbidden(_("This slide can not be marked as completed."))
        slide.action_mark_completed()

    def _slide_mark_uncompleted(self, slide):
        if not slide.can_self_mark_uncompleted:
            raise werkzeug.exceptions.Forbidden(_("This slide can not be marked as uncompleted."))
        slide.action_mark_uncompleted()

    def _get_slide_detail(self, slide):
        base_domain = self._get_channel_slides_base_domain(slide.channel_id)
        category_data = slide.channel_id._get_categorized_slides(
            base_domain,
            order=request.env['slide.slide']._order_by_strategy['sequence'],
            force_void=True
        )

        if slide.channel_id.channel_type == 'documentation':
            most_viewed_slides = request.env['slide.slide'].search(base_domain, limit=self._slides_per_aside, order='total_views desc')
            related_domain = expression.AND([base_domain, [('category_id', '=', slide.category_id.id)]])
            related_slides = request.env['slide.slide'].search(related_domain, limit=self._slides_per_aside)
        else:
            most_viewed_slides, related_slides = request.env['slide.slide'], request.env['slide.slide']

        channel_slides_ids = slide.channel_id.slide_content_ids.ids
        slide_index = channel_slides_ids.index(slide.id)
        previous_slide = slide.channel_id.slide_content_ids[slide_index-1] if slide_index > 0 else None
        next_slide = slide.channel_id.slide_content_ids[slide_index+1] if slide_index < len(channel_slides_ids) - 1 else None

        render_values = self._slide_render_context_base()
        render_values.update({
            # slide
            'slide': slide,
            'main_object': slide,
            'most_viewed_slides': most_viewed_slides,
            'related_slides': related_slides,
            'previous_slide': previous_slide,
            'next_slide': next_slide,
            'category_data': category_data,
            # rating and comments
            'comments': slide.website_message_ids or [],
        })

        # allow rating and comments
        if slide.channel_id.allow_comment:
            render_values.update({
                'message_post_pid': request.env.user.partner_id.id,
            })

        return render_values

    def _get_slide_quiz_partner_info(self, slide, quiz_done=False):
        return slide._compute_quiz_info(request.env.user.partner_id, quiz_done=quiz_done)[slide.id]

    def _get_slide_quiz_data(self, slide):
        is_designer = request.env.user.has_group('website.group_website_designer')
        slides_resources = slide.slide_resource_ids if slide.channel_id.is_member else []
        values = {
            'slide_description': slide.description,
            'slide_questions': [{
                'answer_ids': [{
                    'comment': answer.comment if is_designer else None,
                    'id': answer.id,
                    'is_correct': answer.is_correct if slide.user_has_completed or is_designer else None,
                    'text_value': answer.text_value,
                } for answer in question.sudo().answer_ids],
                'id': question.id,
                'question': question.question,
            } for question in slide.question_ids],
            'slide_resource_ids': [{
                'display_name' : resource.display_name,
                'download_url': resource.download_url,
                'id': resource.id,
                'link': resource.link,
                'resource_type': resource.resource_type,
            } for resource in slides_resources]
        }
        if 'slide_answer_quiz' in request.session:
            slide_answer_quiz = json.loads(request.session['slide_answer_quiz'])
            if str(slide.id) in slide_answer_quiz:
                values['session_answers'] = slide_answer_quiz[str(slide.id)]
        values.update(self._get_slide_quiz_partner_info(slide))
        return values

    def _get_new_slide_category_values(self, channel, name):
        return {
            'name': name,
            'channel_id': channel.id,
            'is_category': True,
            'is_published': True,
            'sequence': channel.slide_ids[-1]['sequence'] + 1 if channel.slide_ids else 1,
        }

    # CHANNEL UTILITIES
    # --------------------------------------------------

    def _get_channel_slides_base_domain(self, channel):
        """ base domain when fetching slide list data related to a given channel

         * website related domain, and restricted to the channel and is not a
           category slide (behavior is different from classic slide);
         * if publisher: everything is ok;
         * if not publisher but has user: either slide is published, either
           current user is the one that uploaded it;
         * if not publisher and public: published;
        """
        base_domain = expression.AND([request.website.website_domain(), ['&', ('channel_id', '=', channel.id), ('is_category', '=', False)]])
        if not channel.can_publish:
            if request.website.is_public_user():
                base_domain = expression.AND([base_domain, [('website_published', '=', True)]])
            else:
                base_domain = expression.AND([base_domain, ['|', ('website_published', '=', True), ('user_id', '=', request.env.user.id)]])
        return base_domain

    def _get_channel_progress(self, channel, include_quiz=False):
        """ Replacement to user_progress. Both may exist in some transient state. """
        slides = request.env['slide.slide'].sudo().search([('channel_id', '=', channel.id)])
        channel_progress = dict((sid, dict()) for sid in slides.ids)
        if not request.env.user._is_public() and channel.is_member:
            slide_partners = request.env['slide.slide.partner'].sudo().search([
                ('channel_id', '=', channel.id),
                ('partner_id', '=', request.env.user.partner_id.id),
                ('slide_id', 'in', slides.ids)
            ])
            for slide_partner in slide_partners:
                channel_progress[slide_partner.slide_id.id].update(slide_partner.read()[0])
                if slide_partner.slide_id.question_ids:
                    gains = [slide_partner.slide_id.quiz_first_attempt_reward,
                             slide_partner.slide_id.quiz_second_attempt_reward,
                             slide_partner.slide_id.quiz_third_attempt_reward,
                             slide_partner.slide_id.quiz_fourth_attempt_reward]
                    channel_progress[slide_partner.slide_id.id]['quiz_gain'] = gains[slide_partner.quiz_attempts_count] if slide_partner.quiz_attempts_count < len(gains) else gains[-1]

        if include_quiz:
            quiz_info = slides._compute_quiz_info(request.env.user.partner_id, quiz_done=False)
            for slide_id, slide_info in quiz_info.items():
                channel_progress[slide_id].update(slide_info)

        return channel_progress

    def _channel_remove_session_answers(self, channel, slide=False):
        """ Will remove the answers saved in the session for a specific channel / slide. """

        if 'slide_answer_quiz' not in request.session:
            return

        slides_domain = [('channel_id', '=', channel.id)]
        if slide:
            slides_domain = expression.AND([slides_domain, [('id', '=', slide.id)]])
        slides = request.env['slide.slide'].search(slides_domain)

        session_slide_answer_quiz = json.loads(request.session['slide_answer_quiz'])
        for slide_id in slides.ids:
            session_slide_answer_quiz.pop(str(slide_id), None)
        request.session['slide_answer_quiz'] = json.dumps(session_slide_answer_quiz)

    def _prepare_collapsed_categories(self, categories_values, slide, next_category_to_open):
        """ Collapse the category if:
            - there is no category (the slides are uncategorized)
            - the category contains the current slide
            - the category is ongoing (has at least one slide completed but not all of its slides)
            - the category is the next one to be opened because the current one has just been completed
        """
        if request.env.user._is_public() or not slide.channel_id.is_member:
            return categories_values
        for category_dict in categories_values:
            category = category_dict.get('category')
            if not category or slide in category.slide_ids or category == next_category_to_open:
                category_dict['is_collapsed'] = True
            else:
                # collapse if category is ongoing
                slides_completion = category.slide_ids.mapped('user_has_completed')
                category_dict['is_collapsed'] = any(slides_completion) and not all(slides_completion)
        return categories_values

    # TAG UTILITIES
    # --------------------------------------------------

    def _slugify_tags(self, tag_ids, toggle_tag_id=None):
        """ Prepares a comma separated slugified tags for the sake of readable
        URLs.

        :param toggle_tag_id: add the tag being clicked (current_tag) to the already
          selected tags (tag_ids) as well as in URL; if tag is already selected
          by the user it is removed from the selected tags (and so from the URL);
        """
        tag_ids = list(tag_ids)  # required to avoid using the same list
        if toggle_tag_id and toggle_tag_id in tag_ids:
            tag_ids.remove(toggle_tag_id)
        elif toggle_tag_id:
            tag_ids.append(toggle_tag_id)
        return ','.join(slug(tag) for tag in request.env['slide.channel.tag'].browse(tag_ids))

    def _channel_search_tags_ids(self, search_tags):
        """ Input: %5B4%5D """
        ChannelTag = request.env['slide.channel.tag']
        try:
            tag_ids = literal_eval(search_tags or '')
        except Exception:
            return ChannelTag
        # perform a search to filter on existing / valid tags implicitly
        return ChannelTag.search([('id', 'in', tag_ids)]) if tag_ids else ChannelTag

    def _channel_search_tags_slug(self, search_tags):
        """ Input: hotels-1,adventure-2 """
        ChannelTag = request.env['slide.channel.tag']
        try:
            tag_ids = list(filter(None, [unslug(tag)[1] for tag in (search_tags or '').split(',')]))
        except Exception:
            return ChannelTag
        # perform a search to filter on existing / valid tags implicitly
        return ChannelTag.search([('id', 'in', tag_ids)]) if tag_ids else ChannelTag

    def _create_or_get_channel_tag(self, tag_id, group_id):
        if not tag_id:
            return request.env['slide.channel.tag']
        # handle creation of new channel tag
        if tag_id[0] == 0:
            group_id = self._create_or_get_channel_tag_group_id(group_id)
            if not group_id:
                return {'error': _('Missing "Tag Group" for creating a new "Tag".')}

            return request.env['slide.channel.tag'].create({
                'name': tag_id[1]['name'],
                'group_id': group_id,
            })
        return request.env['slide.channel.tag'].browse(tag_id[0])

    def _create_or_get_channel_tag_group_id(self, group_id):
        if not group_id:
            return False
        # handle creation of new channel tag group
        if group_id[0] == 0:
            return request.env['slide.channel.tag.group'].create({
                'name': group_id[1]['name'],
            }).id
        # use existing channel tag group
        return group_id[0]

    # --------------------------------------------------
    # SLIDE.CHANNEL MAIN / SEARCH
    # --------------------------------------------------

    @http.route('/slides', type='http', auth="public", website=True, sitemap=True)
    def slides_channel_home(self, **post):
        """ Home page for eLearning platform. Is mainly a container page, does not allow search / filter. """
        channels_all = tools.lazy(lambda: request.env['slide.channel'].search(request.website.website_domain()))
        if not request.env.user._is_public():
            #If a course is completed, we don't want to see it in first position but in last
            channels_my = tools.lazy(lambda: channels_all.filtered(lambda channel: channel.is_member).sorted(lambda channel: 0 if channel.completed else channel.completion, reverse=True)[:3])
        else:
            channels_my = request.env['slide.channel']
        channels_popular = tools.lazy(lambda: channels_all.sorted('total_votes', reverse=True)[:3])
        channels_newest = tools.lazy(lambda: channels_all.sorted('create_date', reverse=True)[:3])

        achievements = tools.lazy(lambda: request.env['gamification.badge.user'].sudo().search([('badge_id.is_published', '=', True)], limit=5))
        if request.env.user._is_public():
            challenges = None
            challenges_done = None
        else:
            challenges = tools.lazy(lambda: request.env['gamification.challenge'].sudo().search([
                ('challenge_category', '=', 'slides'),
                ('reward_id.is_published', '=', True)
            ], order='id asc', limit=5))
            challenges_done = tools.lazy(lambda: request.env['gamification.badge.user'].sudo().search([
                ('challenge_id', 'in', challenges.ids),
                ('user_id', '=', request.env.user.id),
                ('badge_id.is_published', '=', True)
            ]).mapped('challenge_id'))

        users = tools.lazy(lambda: request.env['res.users'].sudo().search([
            ('karma', '>', 0),
            ('website_published', '=', True)], limit=5, order='karma desc'))

        render_values = self._slide_render_context_base()
        render_values.update(self._prepare_user_values(**post))
        render_values.update({
            'channels_my': channels_my,
            'channels_popular': channels_popular,
            'channels_newest': channels_newest,
            'achievements': achievements,
            'users': users,
            'top3_users': tools.lazy(self._get_top3_users),
            'challenges': challenges,
            'challenges_done': challenges_done,
            'search_tags': request.env['slide.channel.tag'],
            'slide_query_url': QueryURL('/slides/all', ['tag']),
            'slugify_tags': self._slugify_tags,
        })

        return request.render('website_slides.courses_home', render_values)

    def _get_slide_channel_search_options(self, my=None, slug_tags=None, slide_category=None, **post):
        return {
            'displayDescription': True,
            'displayDetail': False,
            'displayExtraDetail': False,
            'displayExtraLink': False,
            'displayImage': False,
            'allowFuzzy': not post.get('noFuzzy'),
            'my': my,
            'tag': slug_tags or post.get('tag'),
            'slide_category': slide_category,
        }

    @http.route(['/slides/all', '/slides/all/tag/<string:slug_tags>'], type='http', auth="public", website=True, sitemap=True)
    def slides_channel_all(self, slide_category=None, slug_tags=None, my=False, **post):
        if slug_tags and request.httprequest.method == 'GET':
            # Redirect `tag-1,tag-2` to `tag-1` to disallow multi tags
            # in GET request for proper bot indexation;
            # if the search term is available, do not remove any existing
            # tags because it is user who provided search term with GET
            # request and so clearly it's not SEO bot.
            tag_list = slug_tags.split(',')
            if len(tag_list) > 1 and not post.get('search'):
                url = QueryURL('/slides/all', ['tag'], tag=tag_list[0], my=my, slide_category=slide_category)()
                return request.redirect(url, code=302)
        render_values = self.slides_channel_all_values(slide_category=slide_category, slug_tags=slug_tags, my=my, **post)
        return request.render('website_slides.courses_all', render_values)

    def slides_channel_all_values(self, slide_category=None, slug_tags=None, my=False, **post):
        """ Home page displaying a list of courses displayed according to some
        criterion and search terms.

          :param string slide_category: if provided, filter the course to contain at
           least one slide of type 'slide_category'. Used notably to display courses
           with certifications;
          :param string slug_tags: if provided, filter the slide.channels having
            the tag(s) (in comma separated slugified form);
          :param bool my: if provided, filter the slide.channels for which the
           current user is a member of
          :param dict post: post parameters, including

           * ``search``: filter on course description / name;
        """
        options = self._get_slide_channel_search_options(
            my=my,
            slug_tags=slug_tags,
            slide_category=slide_category,
            **post
        )
        search = post.get('search')
        order = self._channel_order_by_criterion.get(post.get('sorting'))
        _, details, fuzzy_search_term = request.website._search_with_fuzzy("slide_channels_only", search,
            limit=1000, order=order, options=options)
        channels = details[0].get('results', request.env['slide.channel'])

        tag_groups = request.env['slide.channel.tag.group'].search(
            ['&', ('tag_ids', '!=', False), ('website_published', '=', True)])
        if slug_tags:
            search_tags = self._channel_search_tags_slug(slug_tags)
        elif post.get('tags'):
            search_tags = self._channel_search_tags_ids(post['tags'])
        else:
            search_tags = request.env['slide.channel.tag']

        render_values = self._slide_render_context_base()
        render_values.update(self._prepare_user_values(**post))
        render_values.update({
            'channels': channels,
            'tag_groups': tag_groups,
            'search_term': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
            'search_slide_category': slide_category,
            'search_my': my,
            'search_tags': search_tags,
            'top3_users': self._get_top3_users(),
            'slugify_tags': self._slugify_tags,
            'slide_query_url': QueryURL('/slides/all', ['tag']),
        })

        return render_values

    def _prepare_additional_channel_values(self, values, **kwargs):
        return values

    def _get_top3_users(self):
        return request.env['res.users'].sudo().search_read([
            ('karma', '>', 0),
            ('website_published', '=', True)], ['id'], limit=3, order='karma desc')

    def _get_user_slide_authorization(self, slide_id):
        """ Get authorization status for the current user to access the given slide along with some data.
        :return: Dict in the form:
        {
            'status': authorized|not_found|not_authorized,
            'slide': the slide corresponding to the slide_id (only if status != 'not_found')
            'channel_id': id of the channel containing the slide (only if status != 'not_found')
        }
        """
        status = 'authorized'
        try:
            slide_model = request.env['slide.slide']
            slide_model.check_access_rights('read')
            slide = slide_model.browse(slide_id)
            slide.check_access_rule('read')
        except (AccessError, MissingError):
            try:
                slide = request.env['slide.slide'].sudo().browse([slide_id])
            except MissingError:
                return {'status': 'not_found'}
            status = 'not_authorized'
        return {'status': status, 'slide': slide, 'channel_id': slide.sudo().channel_id.id}

    @http.route([
        '/slides/<int:channel_id>',
        '/slides/<int:channel_id>/category/<int:category_id>',
        '/slides/<int:channel_id>/category/<int:category_id>/page/<int:page>',
        '/slides/<model("slide.channel"):channel>',
        '/slides/<model("slide.channel"):channel>/page/<int:page>',
        '/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>',
        '/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>/page/<int:page>',
        '/slides/<model("slide.channel"):channel>/category/<model("slide.slide"):category>',
        '/slides/<model("slide.channel"):channel>/category/<model("slide.slide"):category>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=sitemap_slide, handle_params_access_error=handle_wslide_error)
    def channel(self, channel=False, channel_id=False, category=None, category_id=False, tag=None, page=1, slide_category=None, uncategorized=False, sorting=None, search=None, **kw):
        """ Will return the rendered page of a course, with optional parameters allowing customization:

        :param channel: slide.channel to be rendered.
        :param channel_id: id of the rendered channel. (*)
        :param category: slide.slide (should be a category). Filter contents to those
            below this category (= section).
        :param category_id: id of the desired slide.slide category. (*)
        :param tag: slide.tag used to filter contents.
        :param slide_category: one of the values of linked selection field.
            Filter to this category of slides (video, article...)
        :param uncategorized: To set to True to access all slides outside of any slide.slide category.
        :param sorting: string defining the way to sort contents. ('most_voted', ...)
        :param search: string of the user search in the search bar.
        :param kw.invite_partner_id: id of the invited partner. (**)
        :param kw.invite_hash: string hash based on course and partner. (**)

        (*) Should be used for preview of invited attendees only. A 403 error could occur when using
            channel and category, if their access to models is denied. The generic shared course link
            uses channel_id as well, for the same reason.
        (**) Those are used to check and give invited attendees the access to the course and
            allow them browing its list of contents.
        """
        invite_partner_id = int(kw['invite_partner_id']) if kw.get('invite_partner_id') else False
        invite_hash = kw.get('invite_hash')
        valid_invite_values = {}

        # Invitation data processing
        if request.website.is_public_user() and invite_partner_id and invite_hash and channel_id and not channel:
            valid_invite_values = self._get_channel_values_from_invite(channel_id, invite_hash, invite_partner_id)
            if valid_invite_values.get('invite_preview'):
                channel = valid_invite_values.get('invite_channel')
                valid_invite_values['pager_args'] = {
                    'invite_hash': invite_hash,
                    'invite_partner_id': invite_partner_id
                }

        # Check access rights
        if channel_id and not channel:
            channel = request.env['slide.channel'].browse(channel_id).exists()
            if not channel:
                return self._redirect_to_slides_main('no_channel')
        try:
            channel.check_access_rights('read')
            channel.check_access_rule('read')
        except AccessError:
            return self._redirect_to_slides_main('no_rights')

        if category_id and not category:
            category = channel.slide_category_ids.filtered(lambda category: category.id == category_id)

        # retro-compatibility for older links, 'slide_category' field was previously named 'slide_type'
        # can be safely removed after 15.3 (I swear though, don't be afraid, remove it!)
        slide_category = slide_category or kw.get('slide_type')

        domain = self._get_channel_slides_base_domain(channel)
        pager_url = "/slides/%s" % (channel.id)
        pager_args = valid_invite_values.get('pager_args', {})
        slide_categories = dict(request.env['slide.slide']._fields['slide_category']._description_selection(request.env))

        if search:
            domain += [
                '|', '|',
                ('name', 'ilike', search),
                ('description', 'ilike', search),
                ('html_content', 'ilike', search)]
            pager_args['search'] = search
        else:
            if category:
                domain += [('category_id', '=', category.id)]
                pager_url += "/category/%s" % category.id
            elif tag:
                domain += [('tag_ids', '=', tag.id)]
                pager_url += "/tag/%s" % tag.id
            if uncategorized:
                domain += [('category_id', '=', False)]
                pager_args['uncategorized'] = 1
            elif slide_category:
                domain += [('slide_category', '=', slide_category)]
                pager_url += "?slide_category=%s" % slide_category

        # sorting criterion
        if channel.channel_type == 'documentation':
            default_sorting = 'latest' if channel.promote_strategy in ['specific', 'none', False] else channel.promote_strategy
            actual_sorting = sorting if sorting and sorting in request.env['slide.slide']._order_by_strategy else default_sorting
        else:
            actual_sorting = 'sequence'
        order = request.env['slide.slide']._order_by_strategy[actual_sorting]
        pager_args['sorting'] = actual_sorting

        slide_count = request.env['slide.slide'].sudo().search_count(domain)
        page_count = math.ceil(slide_count / self._slides_per_page)
        pager = request.website.pager(url=pager_url, total=slide_count, page=page,
                                      step=self._slides_per_page, url_args=pager_args,
                                      scope=page_count if page_count < self._pager_max_pages else self._pager_max_pages)

        query_string = None
        if category:
            query_string = "?search_category=%s" % category.id
        elif tag:
            query_string = "?search_tag=%s" % tag.id
        elif slide_category:
            query_string = "?search_slide_category=%s" % slide_category
        elif uncategorized:
            query_string = "?search_uncategorized=1"

        errors = {'access_error': False}
        if request.params.get('access_error') == 'course_content' and request.params.get('access_error_slide_id'):
            # Access are re-verified to support use case where the user refresh the page after an update of their access
            user_slide_authorization = self._get_user_slide_authorization(int(request.params.get('access_error_slide_id')))
            if user_slide_authorization['status'] == 'not_authorized':
                errors.update({
                    'access_error': 'course_content',
                    'access_error_content_name': request.params.get('access_error_slide_name'),
                })

        render_values = self._slide_render_context_base()
        render_values.update({
            'channel': channel,
            'main_object': channel,
            'active_tab': kw.get('active_tab', 'home'),
            # search
            'search_category': category,
            'search_tag': tag,
            'search_slide_category': slide_category,
            'search_uncategorized': uncategorized,
            'query_string': query_string,
            'slide_categories': slide_categories,
            'sorting': actual_sorting,
            'search': search,
            # display data
            'pager': pager,
            'slide_count': slide_count,
            # display upload modal
            'enable_slide_upload': kw.get('enable_slide_upload', False),
            # invitation data
            'invite_hash': invite_hash,
            'invite_partner_id': invite_partner_id,
            'invite_preview': valid_invite_values.get('invite_preview'),
            'is_partner_without_user': valid_invite_values.get('is_partner_without_user'),
            ** errors,
            ** self._slide_channel_prepare_review_values(channel),
        })

        # fetch slides and handle uncategorized slides; done as sudo because we want to display all
        # of them but unreachable ones won't be clickable (+ slide controller will crash anyway)
        # documentation mode may display less slides than content by category but overhead of
        # computation is reasonable
        if channel.promote_strategy == 'specific':
            render_values['slide_promoted'] = channel.sudo().promoted_slide_id
        else:
            render_values['slide_promoted'] = request.env['slide.slide'].sudo().search(domain, limit=1, order=order)

        limit_category_data = False
        if channel.channel_type == 'documentation':
            if category or uncategorized:
                limit_category_data = self._slides_per_page
            else:
                limit_category_data = self._slides_per_category

        render_values['category_data'] = channel._get_categorized_slides(
            domain, order,
            force_void=not category,
            limit=limit_category_data,
            offset=pager['offset'])
        render_values['channel_progress'] = self._get_channel_progress(channel, include_quiz=True)

        # for sys admins: prepare data to install directly modules from eLearning when
        # uploading slides. Currently supporting only survey, because why not.
        if request.env.user.has_group('base.group_system'):
            module = request.env.ref('base.module_survey')
            if module.state != 'installed':
                render_values['modules_to_install'] = [{
                    'id': module.id,
                    'name': module.shortdesc,
                    'motivational': _('Want to test and certify your students?'),
                    'default_slide_category': 'certification',
                }]

        render_values = self._prepare_additional_channel_values(render_values, **kw)
        return request.render('website_slides.course_main', render_values)

    @staticmethod
    def _get_channel_values_from_invite(channel_id, invite_hash, invite_partner_id):
        """ Check identification parameters and returns values used to give access to signed out invited members.
        The course is returned as sudo to allow them seeing a preview of the course even if visibility if not public.
        Returns dict of values or containing 'invite_error' and a value corresponding to the error. See _get_invite_error_msg."""
        channel_sudo = request.env['slide.channel'].browse(channel_id).exists().sudo()
        partner_sudo = request.env['res.partner'].browse(invite_partner_id).exists().sudo()
        if not partner_sudo or not channel_sudo.is_published:
            return {'invite_error': 'no_partner' if not partner_sudo else 'no_channel' if not channel_sudo else 'no_rights'}

        channel_partner_sudo = channel_sudo.channel_partner_all_ids.filtered(lambda cp: cp.partner_id.id == invite_partner_id)
        if not channel_partner_sudo:
            return {'invite_error': 'expired'}
        if not consteq(channel_partner_sudo._get_invitation_hash(), invite_hash):
            return {'invite_error': 'hash_fail'}

        if channel_partner_sudo.member_status == 'invited':
            if not channel_partner_sudo.last_invitation_date or \
               channel_partner_sudo.last_invitation_date + relativedelta(months=3) < fields.Datetime.now():
                return {'invite_error': 'expired'}

        return {
            'invite_channel': channel_sudo,
            'invite_channel_partner': channel_partner_sudo,
            'invite_preview': True,
            'is_partner_without_user': not partner_sudo.user_ids,
            'invite_partner': partner_sudo
        }

    # SLIDE.CHANNEL UTILS
    # --------------------------------------------------

    @staticmethod
    def _redirect_to_slides_main(invite_error=''):
        return request.redirect(f"/slides?invite_error={invite_error}" if invite_error else "/slides")

    @staticmethod
    def _redirect_to_channel(channel):
        return request.redirect(f"/slides/{slug(channel)}")

    def _slide_channel_prepare_review_values(self, channel):
        values = {
            'rating_avg': channel.rating_avg,
            'rating_count': channel.rating_count,
        }

        if not request.env.user._is_public():
            subtype_comment_id = request.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
            last_message = request.env['mail.message'].search([
                ('model', '=', channel._name),
                ('res_id', '=', channel.id),
                ('author_id', '=', request.env.user.partner_id.id),
                ('message_type', '=', 'comment'),
                ('subtype_id', '=', subtype_comment_id)
            ], order='write_date DESC', limit=1)

            if last_message:
                last_message_values = last_message.read(['body', 'rating_value', 'attachment_ids'])[0]
                last_message_attachment_ids = last_message_values.pop('attachment_ids', [])
                if last_message_attachment_ids:
                    # use sudo as portal user cannot read access_token, necessary for updating attachments
                    # through frontend chatter -> access is already granted and limited to current user message
                    last_message_attachment_ids = json.dumps(
                        request.env['ir.attachment'].sudo().browse(last_message_attachment_ids).read(
                            ['id', 'name', 'mimetype', 'file_size', 'access_token']
                        )
                    )
            else:
                last_message_values = {}
                last_message_attachment_ids = []

            values.update({
                'last_message_id': last_message_values.get('id'),
                'last_message': tools.html2plaintext(last_message_values.get('body', '')),
                'last_rating_value': last_message_values.get('rating_value'),
                'last_message_attachment_ids': last_message_attachment_ids,
            })
            if channel.can_review:
                values.update({
                    'message_post_hash': channel._sign_token(request.env.user.partner_id.id),
                    'message_post_pid': request.env.user.partner_id.id,
                })

        return values

    @http.route('/slides/<int:channel_id>/invite', type='http', auth='public', website=True, sitemap=False)
    def slide_channel_invite(self, channel_id, invite_partner_id, invite_hash):
        """ This route is included in the invitation link in email to join / check out the course. It is
        the main entry point on the attendee's side when sharing or inviting them. As rule of thumb, this will
        redirect to the course if the rights are given, and to the main /slides page with appropriate error
        message otherwise. (See _get_invite_error_msg method)

        It acts as a redirector:
            - Returns error if parameters are not valid or if expired invitation.
            - If a user is logged, verify the link is for this user. Redirects according to Acl's.
            - If no user is logged:
                - Redirects to login / signup if the partner is enrolled.
                - Redirects to the course with invite parameters. They will be able to browse a course preview
                before logging in / signing up, as prompted in an information banner.

        :param channel_id: The id of the course the user is invited to. Do not use <model> in the route instead,
            otherwise an error 403 could be returned if the (public) user has no access to the record.
        :param invite_partner_id: The id of the invited partner.
        :param invite_hash: The invitation hash that allows a direct access to channel_id, even if not connected.
        """
        channel = request.env['slide.channel'].browse(int(channel_id)).exists()
        if not channel:
            return self._redirect_to_slides_main('no_channel')

        # --- Compute rights of current user
        try:
            channel.check_access_rights('read')
            channel.check_access_rule('read')
        except AccessError:
            has_rights = False
        else:
            has_rights = True

        invite_values = self._get_channel_values_from_invite(channel_id, invite_hash, int(invite_partner_id))
        if invite_values.get('invite_error'):
            return self._redirect_to_channel(channel) if has_rights else self._redirect_to_slides_main(invite_values.get('invite_error'))

        invite_partner = invite_values.get('invite_partner')
        invite_channel_partner = invite_values.get('invite_channel_partner')

        # --- A user is logged
        if not request.website.is_public_user():
            if request.env.user.partner_id.id != invite_partner.id:
                return self._redirect_to_slides_main('partner_fail')
            return self._redirect_to_channel(channel) if has_rights else self._redirect_to_slides_main('no_rights')

        redirect_url = f'/slides/{channel_id}'

        # --- No user is logged.
        if invite_channel_partner.member_status != 'invited':
            # Enrolled partner. Access to the course but needs to log in / sign up.
            if invite_values.get('is_partner_without_user'):
                invite_partner.signup_prepare()
                signup_url = invite_partner._get_signup_url_for_action(url=redirect_url)[invite_partner.id]
                return request.redirect(signup_url)
            else:
                return request.redirect(f'/web/login?redirect={redirect_url}&auth_login={invite_partner.user_ids[0].login}')
        # Pending invitation. A banner will allow partner to login / signup on the course page.
        return request.redirect(f'{redirect_url}?invite_partner_id={invite_partner_id}&invite_hash={invite_hash}')

    @http.route(['/slides/<int:channel_id>/identify'], type='http', auth='public', website=True, sitemap=False)
    def slide_channel_identify_from_invite(self, channel_id, invite_partner_id, invite_hash):
        """ This route redirects invited partners when they click on the login / signup button, when they are
        asked to login / signup as invited to a course as public user on the course page preview. """
        if not request.website.is_public_user():
            return self._redirect_to_slides_main('identify_fail')

        invite_partner_id = int(invite_partner_id)
        invite_values = self._get_channel_values_from_invite(channel_id, invite_hash, invite_partner_id)
        if invite_values.get('invite_preview'):
            partner_sudo = invite_values.get('invite_partner')
            if invite_values.get('is_partner_without_user'):
                partner_sudo.signup_prepare()
                return request.redirect(partner_sudo._get_signup_url_for_action(url=f'/slides/{channel_id}')[partner_sudo.id])
            else:
                return request.redirect(f'/web/login?redirect=/slides/{channel_id}&auth_login={partner_sudo.user_ids[0].login}')
        return self._redirect_to_slides_main('identify_fail')

    @http.route(['/slides/channel/join'], type='json', auth='public', website=True)
    def slide_channel_join(self, channel_id):
        if request.website.is_public_user():
            return {
                'error': 'public_user',
                'error_signup_allowed': request.env['res.users'].sudo()._get_signup_invitation_scope() == 'b2c',
            }
        channel = request.env['slide.channel'].browse(channel_id)
        if channel.is_member_invited and channel.enroll == 'invite':
            success = channel.sudo()._action_add_members(request.env.user.partner_id)
        else:
            success = channel._action_add_members(request.env.user.partner_id)
        return {'error': 'join_done'} if not success else success

    @http.route(['/slides/channel/leave'], type='json', auth='user', website=True)
    def slide_channel_leave(self, channel_id):
        channel = request.env['slide.channel'].browse(channel_id)
        channel._remove_membership(request.env.user.partner_id.ids)
        self._channel_remove_session_answers(channel)
        return True

    @http.route(['/slides/channel/tag/search_read'], type='json', auth='user', methods=['POST'], website=True)
    def slide_channel_tag_search_read(self, fields, domain):
        can_create = request.env['slide.channel.tag'].check_access_rights('create', raise_exception=False)
        return {
            'read_results': request.env['slide.channel.tag'].search_read(domain, fields),
            'can_create': can_create,
        }

    @http.route(['/slides/channel/tag/group/search_read'], type='json', auth='user', methods=['POST'], website=True)
    def slide_channel_tag_group_search_read(self, fields, domain):
        can_create = request.env['slide.channel.tag.group'].check_access_rights('create', raise_exception=False)
        return {
            'read_results': request.env['slide.channel.tag.group'].search_read(domain, fields),
            'can_create': can_create,
        }

    @http.route('/slides/channel/tag/add', type='json', auth='user', methods=['POST'], website=True)
    def slide_channel_tag_add(self, channel_id, tag_id=None, group_id=None):
        """ Adds a slide channel tag to the specified slide channel.

        :param integer channel_id: Channel ID
        :param list tag_id: Channel Tag ID as first value of list. If id=0, then this is a new tag to
                            generate and expects a second list value of the name of the new tag.
        :param list group_id: Channel Tag Group ID as first value of list. If id=0, then this is a new
                              tag group to generate and expects a second list value of the name of the
                              new tag group. This value is required for when a new tag is being created.

        tag_id and group_id values are provided by a Select2. Default "None" values allow for
        graceful failures in exceptional cases when values are not provided.

        :return: channel's course page
        """

        # handle exception during addition of course tag and send error notification to the client
        # otherwise client slide create dialog box continue processing even server fail to create a slide
        try:
            channel = request.env['slide.channel'].browse(int(channel_id))
            can_upload = channel.can_upload
            can_publish = channel.can_publish
        except UserError as e:
            _logger.error(e)
            return {'error': e.args[0]}
        else:
            if not can_upload or not can_publish:
                return {'error': _('You cannot add tags to this course.')}

        tag = self._create_or_get_channel_tag(tag_id, group_id)
        tag.write({'channel_ids': [(4, channel.id, 0)]})

        return {'url': "/slides/%s" % (slug(channel))}

    @http.route(['/slides/channel/send_share_email'], type='json', auth='user', website=True)
    def slide_channel_send_share_email(self, channel_id, emails):
        if not email_split(emails):
            return False
        channel = request.env['slide.channel'].browse(int(channel_id))
        channel._send_share_email(emails)
        return True

    @http.route(['/slides/channel/subscribe'], type='json', auth='user', website=True)
    def slide_channel_subscribe(self, channel_id):
        return request.env['slide.channel'].browse(channel_id).message_subscribe(partner_ids=[request.env.user.partner_id.id])

    @http.route(['/slides/channel/unsubscribe'], type='json', auth='user', website=True)
    def slide_channel_unsubscribe(self, channel_id):
        request.env['slide.channel'].browse(channel_id).message_unsubscribe(partner_ids=[request.env.user.partner_id.id])
        return True

    # --------------------------------------------------
    # SLIDE.SLIDE MAIN / SEARCH
    # --------------------------------------------------

    @http.route('/slides/slide/<model("slide.slide"):slide>', type='http', auth="public",
                website=True, sitemap=True, handle_params_access_error=handle_wslide_error)
    def slide_view(self, slide, **kwargs):
        if not slide.channel_id.can_access_from_current_website() or not slide.active:
            raise werkzeug.exceptions.NotFound()
        # redirection to channel's homepage for category slides
        if slide.is_category:
            return request.redirect(slide.channel_id.website_url)

        if slide.can_self_mark_completed and not slide.user_has_completed \
           and slide.channel_id.channel_type == 'training' and slide.slide_category != 'video':
            self._slide_mark_completed(slide)
            next_category_to_open = slide._get_next_category()
        else:
            self._set_viewed_slide(slide)
            next_category_to_open = False

        values = self._get_slide_detail(slide)
        # quiz-specific: update with karma and quiz information
        if slide.question_ids:
            values.update(self._get_slide_quiz_data(slide))
        # sidebar: update with user channel progress
        values['channel_progress'] = self._get_channel_progress(slide.channel_id, include_quiz=True)
        # sidebar: auto-collapsed the categories depending on conditions
        values['category_data'] = self._prepare_collapsed_categories(values['category_data'], slide, next_category_to_open)

        # Allows to have breadcrumb for the previously used filter
        values.update({
            'search_category': slide.category_id if kwargs.get('search_category') else None,
            'search_tag': request.env['slide.tag'].browse(int(kwargs.get('search_tag'))) if kwargs.get('search_tag') else None,
            'slide_categories': dict(request.env['slide.slide']._fields['slide_category']._description_selection(request.env)) if kwargs.get('search_slide_category') else None,
            'search_slide_category': kwargs.get('search_slide_category'),
            'search_uncategorized': kwargs.get('search_uncategorized'),
        })

        values['channel'] = slide.channel_id
        values = self._prepare_additional_channel_values(values, **kwargs)
        values['signup_allowed'] = request.env['res.users'].sudo()._get_signup_invitation_scope() == 'b2c'

        if kwargs.get('fullscreen') == '1':
            values.update(self._slide_channel_prepare_review_values(slide.channel_id))
            return request.render("website_slides.slide_fullscreen", values)

        values.pop('channel', None)
        return request.render("website_slides.slide_main", values)

    @http.route('/slides/slide/<int:slide_id>/share', type='http', auth="public", website=True, sitemap=False)
    def slide_shared_view(self, slide_id, **kwargs):
        user_slide_authorization = self._get_user_slide_authorization(slide_id)
        status = user_slide_authorization['status']
        if status == 'not_found':
            raise werkzeug.exceptions.NotFound()

        if status == 'authorized':
            return request.redirect(
                '%s?%s' % (user_slide_authorization['slide'].website_url, werkzeug.urls.url_encode(kwargs)))

        channel_id = user_slide_authorization['channel_id']
        return request.redirect('/slides/%s?%s' % (channel_id, werkzeug.urls.url_encode({
            'access_error': 'course_content',
            'access_error_slide_id': slide_id,
            'access_error_slide_name': user_slide_authorization['slide'].name,
        })))

    @http.route('/slides/slide/<model("slide.slide"):slide>/pdf_content',
                type='http', auth="public", website=True, sitemap=False, handle_params_access_error=handle_wslide_error)
    def slide_get_pdf_content(self, slide):
        response = Response()
        response.data = slide.binary_content and base64.b64decode(slide.binary_content) or b''
        response.mimetype = 'application/pdf'
        return response

    @http.route('/slides/slide/<int:slide_id>/get_image', type='http', auth="public", website=True, sitemap=False)
    def slide_get_image(self, slide_id, field='image_128', width=0, height=0, crop=False):
        # Protect infographics by limiting access to 256px (large) images
        if field not in ('image_128', 'image_256', 'image_512', 'image_1024', 'image_1920'):
            return werkzeug.exceptions.Forbidden()

        slide = request.env['slide.slide'].sudo().browse(slide_id).exists()
        if not slide:
            raise werkzeug.exceptions.NotFound()

        return request.env['ir.binary']._get_image_stream_from(
            slide, field, width=int(width), height=int(height), crop=int(crop)
        ).get_response()

    # SLIDE.SLIDE UTILS
    # --------------------------------------------------

    @http.route('/slides/slide/get_html_content', type="json", auth="public", website=True)
    def get_html_content(self, slide_id):
        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            return fetch_res
        return {
            'html_content': fetch_res['slide'].html_content
        }

    @http.route('/slides/slide/<model("slide.slide"):slide>/set_completed',
                website=True, type="http", auth="user", handle_params_access_error=handle_wslide_error)
    def slide_set_completed_and_redirect(self, slide, next_slide_id=None):
        self._slide_mark_completed(slide)
        next_slide = None
        if next_slide_id:
            next_slide = self._fetch_slide(next_slide_id).get('slide', None)
        return request.redirect("/slides/slide/%s" % (slug(next_slide) if next_slide else slug(slide)))

    @http.route('/slides/slide/set_completed', website=True, type="json", auth="public")
    def slide_set_completed(self, slide_id):
        if request.website.is_public_user():
            return {'error': 'public_user'}
        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            return fetch_res
        self._slide_mark_completed(fetch_res['slide'])
        next_category = fetch_res['slide']._get_next_category()
        return {
            'channel_completion': fetch_res['slide'].channel_id.completion,
            'next_category_id': next_category.id if next_category else False,
        }

    @http.route('/slides/slide/<model("slide.slide"):slide>/set_uncompleted',
                website=True, type='http', auth='user', handle_params_access_error=handle_wslide_error)
    def slide_set_uncompleted_and_redirect(self, slide):
        self._slide_mark_uncompleted(slide)
        return request.redirect(f'/slides/slide/{slug(slide)}')

    @http.route('/slides/slide/set_uncompleted', website=True, type='json', auth='public')
    def slide_set_uncompleted(self, slide_id):
        if request.website.is_public_user():
            return {'error': 'public_user'}
        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            return fetch_res
        self._slide_mark_uncompleted(fetch_res['slide'])
        return {
            'channel_completion': fetch_res['slide'].channel_id.completion,
            'next_category_id': False,
        }

    @http.route('/slides/slide/like', type='json', auth="public", website=True)
    def slide_like(self, slide_id, upvote):
        if request.website.is_public_user():
            return {'error': 'public_user', 'error_signup_allowed': request.env['res.users'].sudo()._get_signup_invitation_scope() == 'b2c'}
        # check slide access
        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            return fetch_res
        # check slide operation
        slide = fetch_res['slide']
        if not slide.channel_id.is_member:
            return {'error': 'channel_membership_required'}
        if not slide.channel_id.allow_comment:
            return {'error': 'channel_comment_disabled'}
        if not slide.channel_id.can_vote:
            return {'error': 'channel_karma_required'}
        if upvote:
            slide.action_like()
        else:
            slide.action_dislike()
        # for large number of likes/dislikes, format them so they don't break the UI
        # first display is done using a widget but this route updated the UI directly
        # hence calling format_decimalized_number
        return {
            'user_vote': slide.user_vote,
            'likes': tools.format_decimalized_number(slide.likes),
            'dislikes': tools.format_decimalized_number(slide.dislikes),
        }

    @http.route('/slides/slide/archive', type='json', auth='user', website=True)
    def slide_archive(self, slide_id):
        """ This route allows channel publishers to archive slides.
        It has to be done in sudo mode since only restricted_editors can write on slides in ACLs """
        slide = request.env['slide.slide'].browse(int(slide_id))
        if slide.channel_id.can_publish:
            slide.sudo().active = False
            return True

        return False

    @http.route('/slides/slide/toggle_is_preview', type='json', auth='user', website=True)
    def slide_preview(self, slide_id):
        slide = request.env['slide.slide'].browse(int(slide_id))
        if slide.channel_id.can_publish:
            slide.is_preview = not slide.is_preview
        return slide.is_preview

    @http.route(['/slides/slide/send_share_email'], type='json', auth='user', website=True)
    def slide_send_share_email(self, slide_id, emails, fullscreen=False):
        if not email_split(emails):
            return False
        slide = request.env['slide.slide'].browse(int(slide_id))
        slide._send_share_email(emails, fullscreen)
        return True

    # --------------------------------------------------
    # TAGS SECTION
    # --------------------------------------------------

    @http.route('/slide_channel_tag/add', type='json', auth='user', methods=['POST'], website=True)
    def slide_channel_tag_create_or_get(self, tag_id, group_id):
        tag = self._create_or_get_channel_tag(tag_id, group_id)
        return {'tag_id': tag.id}

    # --------------------------------------------------
    # QUIZ SECTION
    # --------------------------------------------------

    @http.route('/slides/slide/quiz/question_add_or_update', type='json', methods=['POST'], auth='user', website=True)
    def slide_quiz_question_add_or_update(self, slide_id, question, sequence, answer_ids, existing_question_id=None):
        """ Add a new question to an existing slide. Completed field of slide.partner
        link is set to False to make sure that the creator can take the quiz again.

        An optional question_id to udpate can be given. In this case question is
        deleted first before creating a new one to simplify management.

        :param integer slide_id: Slide ID
        :param string question: Question Title
        :param integer sequence: Question Sequence
        :param array answer_ids: Array containing all the answers :
                [
                    'sequence': Answer Sequence (Integer),
                    'text_value': Answer Title (String),
                    'is_correct': Answer Is Correct (Boolean)
                ]
        :param integer existing_question_id: question ID if this is an update

        :return: rendered question template
        """

        new_question_values = {
            'sequence': sequence,
            'question': question,
            'slide_id': slide_id,
            'answer_ids': [(0, 0, {
                'sequence': answer['sequence'],
                'text_value': answer['text_value'],
                'is_correct': answer['is_correct'],
                'comment': answer['comment']
            }) for answer in answer_ids]
        }

        try:
            # Attempt to create the question and validate the fields.
            # We want to return the error to have a nice display instead of the default mechanism
            # of exception handling that shows sticky toasters.
            # (Use a 'new' and not a create to avoid having to rollback anything if an error is
            # raised)
            slide_question = request.env['slide.question'].new(new_question_values)
            slide_question._validate_fields(new_question_values.keys())
        except ValidationError as e:
            return {'error': e.args[0]}

        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            return fetch_res
        slide = fetch_res['slide']
        if existing_question_id:
            request.env['slide.question'].search([
                ('slide_id', '=', slide.id),
                ('id', '=', int(existing_question_id))
            ]).unlink()

        request.env['slide.slide.partner'].search([
            ('slide_id', '=', slide_id),
            ('partner_id', '=', request.env.user.partner_id.id)
        ]).write({'completed': False})

        slide_question = request.env['slide.question'].create(new_question_values)
        return request.env['ir.qweb']._render('website_slides.lesson_content_quiz_question', {
            'slide': slide,
            'question': slide_question,
        })

    @http.route('/slides/slide/quiz/get', type="json", auth="public", website=True)
    def slide_quiz_get(self, slide_id):
        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            return fetch_res
        slide = fetch_res['slide']
        return self._get_slide_quiz_data(slide)

    @http.route('/slides/slide/quiz/reset', type="json", auth="user", website=True)
    def slide_quiz_reset(self, slide_id):
        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            return fetch_res
        request.env['slide.slide.partner'].search([
            ('slide_id', '=', fetch_res['slide'].id),
            ('partner_id', '=', request.env.user.partner_id.id)
        ]).write({'completed': False, 'quiz_attempts_count': 0})

    @http.route('/slides/slide/quiz/submit', type="json", auth="public", website=True)
    def slide_quiz_submit(self, slide_id, answer_ids):
        if request.website.is_public_user():
            return {'error': 'public_user'}
        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            return fetch_res
        slide = fetch_res['slide']

        if slide.user_has_completed:
            self._channel_remove_session_answers(slide.channel_id, slide)
            return {'error': 'slide_quiz_done'}

        all_questions = request.env['slide.question'].sudo().search([('slide_id', '=', slide.id)])

        user_answers = request.env['slide.answer'].sudo().search([('id', 'in', answer_ids)])
        if user_answers.mapped('question_id') != all_questions:
            return {'error': 'slide_quiz_incomplete'}

        user_bad_answers = user_answers.filtered(lambda answer: not answer.is_correct)

        self._set_viewed_slide(slide, quiz_attempts_inc=True)
        quiz_info = self._get_slide_quiz_partner_info(slide, quiz_done=True)

        rank_progress = {}
        if not user_bad_answers:
            rank_progress['previous_rank'] = self._get_rank_values(request.env.user)
            slide._action_mark_completed()
            rank_progress['new_rank'] = self._get_rank_values(request.env.user)
            rank_progress.update({
                'description': request.env.user.rank_id.description,
                'last_rank': not request.env.user._get_next_rank(),
                'level_up': rank_progress['previous_rank']['lower_bound'] != rank_progress['new_rank']['lower_bound']
            })
        self._channel_remove_session_answers(slide.channel_id, slide)
        return {
            'answers': {
                answer.question_id.id: {
                    'is_correct': answer.is_correct,
                    'comment': answer.comment
                } for answer in user_answers
            },
            'completed': slide.user_has_completed,
            'channel_completion': slide.channel_id.completion,
            'quizKarmaWon': quiz_info['quiz_karma_won'],
            'quizKarmaGain': quiz_info['quiz_karma_gain'],
            'quizAttemptsCount': quiz_info['quiz_attempts_count'],
            'rankProgress': rank_progress,
        }

    @http.route(['/slides/slide/quiz/save_to_session'], type='json', auth='public', website=True)
    def slide_quiz_save_to_session(self, quiz_answers):
        session_slide_answer_quiz = json.loads(request.session.get('slide_answer_quiz', '{}'))
        slide_id = quiz_answers['slide_id']
        session_slide_answer_quiz[str(slide_id)] = quiz_answers['slide_answers']
        request.session['slide_answer_quiz'] = json.dumps(session_slide_answer_quiz)

    def _get_rank_values(self, user):
        lower_bound = user.rank_id.karma_min or 0
        next_rank = user._get_next_rank()
        upper_bound = next_rank.karma_min
        progress = 100
        if next_rank and (upper_bound - lower_bound) != 0:
            progress = 100 * ((user.karma - lower_bound) / (upper_bound - lower_bound))
        return {
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'karma': user.karma,
            'motivational': next_rank.description_motivational,
            'progress': progress
        }
    # --------------------------------------------------
    # CATEGORY MANAGEMENT
    # --------------------------------------------------

    @http.route(['/slides/category/search_read'], type='json', auth='user', methods=['POST'], website=True)
    def slide_category_search_read(self, fields, domain):
        category_slide_domain = domain if domain else []
        category_slide_domain = expression.AND([category_slide_domain, [('is_category', '=', True)]])
        can_create = request.env['slide.slide'].check_access_rights('create', raise_exception=False)
        return {
            'read_results': request.env['slide.slide'].search_read(category_slide_domain, fields),
            'can_create': can_create,
        }

    @http.route('/slides/category/add', type="http", website=True, auth="user", methods=['POST'])
    def slide_category_add(self, channel_id, name):
        """ Adds a category to the specified channel. Slide is added at the end
        of slide list based on sequence. """
        channel = request.env['slide.channel'].browse(int(channel_id))
        if not channel.can_upload or not channel.can_publish:
            raise werkzeug.exceptions.NotFound()

        request.env['slide.slide'].create(self._get_new_slide_category_values(channel, name))

        return request.redirect("/slides/%s" % (slug(channel)))

    # --------------------------------------------------
    # SLIDE.UPLOAD
    # --------------------------------------------------

    @http.route(['/slides/prepare_preview'], type='json', auth='user', methods=['POST'], website=True)
    def prepare_preview(self, channel_id, slide_category, url=None):
        """ Will attempt to fetch external metadata for this slide from the correct
        source (YouTube, Google Drive, ...).

        To take advantage of the slide business method, we create a temporary slide record before
        fetching the metadata.
        This allows a lot of code simplification, since we use "new", it will not created anything
        in database. """

        if not url:
            return {}

        Slide = request.env['slide.slide']

        additional_values = {}
        if slide_category == 'video':
            identical_video = request.env['slide.slide']
            existing_videos = Slide.search([
                ('channel_id', '=', int(channel_id)),
                ('slide_category', '=', 'video')
            ])

            slide = Slide.new({
                'channel_id': int(channel_id),
                'name': 'memory_record_for_computed_fields',
                'slide_category': 'video',
                'url': url
            })

            if not slide.video_source_type:
                slide.unlink()
                return {'error': _("Could not find your video. Please check if your link is correct and if the video can be accessed.")}

            if slide.video_source_type == 'youtube':
                identical_video = existing_videos.filtered(
                    lambda existing_video: slide.youtube_id == existing_video.youtube_id)
            elif slide.video_source_type == 'google_drive':
                identical_video = existing_videos.filtered(
                    lambda existing_video: slide.google_drive_id == existing_video.google_drive_id)
            elif slide.video_source_type == 'vimeo':
                identical_video = existing_videos.filtered(
                    lambda existing_video: slide.vimeo_id == existing_video.vimeo_id)
            if identical_video:
                identical_video_name = identical_video[0].name
                additional_values['info'] = _('This video already exists in this channel on the following content: %s', identical_video_name)
        elif slide_category in ['document', 'infographic']:
            slide = Slide.new({
                'channel_id': int(channel_id),
                'name': 'memory_record_for_computed_fields',
                'slide_category': slide_category,
                'source_type': 'external',
                'url': url
            })

            if not slide.google_drive_id:
                return {'error': _('Please enter valid Google Drive Link')}

        slide_values, error = slide._fetch_external_metadata(image_url_only=True)
        if error:
            return {'error': error}

        if additional_values:
            slide_values.update(additional_values)

        return slide_values

    @http.route(['/slides/add_slide'], type='json', auth='user', methods=['POST'], website=True)
    def create_slide(self, *args, **post):
        # check the size only when we upload a file.
        if post.get('binary_content'):
            file_size = len(post['binary_content']) * 3 / 4  # base64
            if (file_size / 1024.0 / 1024.0) > 25:
                return {'error': _('File is too big. File size cannot exceed 25MB')}

        values = dict((fname, post[fname]) for fname in self._get_valid_slide_post_values() if post.get(fname))

        # handle exception during creation of slide and sent error notification to the client
        # otherwise client slide create dialog box continue processing even server fail to create a slide
        try:
            channel = request.env['slide.channel'].browse(values['channel_id'])
            can_upload = channel.can_upload
            can_publish = channel.can_publish
        except UserError as e:
            _logger.error(e)
            return {'error': e.args[0]}
        else:
            if not can_upload:
                return {'error': _('You cannot upload on this channel.')}

        if post.get('duration'):
            # minutes to hours conversion
            values['completion_time'] = int(post['duration']) / 60

        category = False
        # handle creation of new categories on the fly
        if post.get('category_id'):
            category_id = post['category_id'][0]
            if category_id == 0:
                category = request.env['slide.slide'].create(self._get_new_slide_category_values(channel, post['category_id'][1]['name']))
                values['sequence'] = category.sequence + 1
            else:
                category = request.env['slide.slide'].browse(category_id)
                values.update({
                    'sequence': request.env['slide.slide'].browse(post['category_id'][0]).sequence + 1
                })

        # create slide itself
        try:
            values['user_id'] = request.env.uid
            slide = request.env['slide.slide'].sudo().create(values)
        except UserError as e:
            _logger.error(e)
            return {'error': e.args[0]}
        except Exception as e:
            _logger.error(e)
            return {'error': _('Internal server error, please try again later or contact administrator.\nHere is the error message: %s', e)}

        # ensure correct ordering by re sequencing slides in front-end (backend should be ok thanks to list view)
        channel._resequence_slides(slide, force_category=category)

        redirect_url = "/slides/slide/%s" % (slide.id)
        if slide.slide_category == 'article':
            redirect_url = request.env["website"].get_client_action_url(redirect_url, True)
        elif slide.slide_category == 'quiz':
            redirect_url += "?quiz_quick_create"
        elif channel.channel_type == "training":
            redirect_url = "/slides/%s" % (slug(channel))
        return {
            'url': redirect_url,
            'channel_type': channel.channel_type,
            'slide_id': slide.id,
            'category_id': slide.category_id
        }

    def _get_valid_slide_post_values(self):
        return ['name', 'url', 'video_url', 'document_google_url', 'image_google_url', 'tag_ids', 'slide_category', 'channel_id',
            'is_preview', 'binary_content', 'description', 'image_1920', 'is_published', 'source_type']

    @http.route(['/slides/tag/search_read'], type='json', auth='user', methods=['POST'], website=True)
    def slide_tag_search_read(self, fields, domain):
        can_create = request.env['slide.tag'].check_access_rights('create', raise_exception=False)
        return {
            'read_results': request.env['slide.tag'].search_read(domain, fields),
            'can_create': can_create,
        }

    # --------------------------------------------------
    # EMBED IN THIRD PARTY WEBSITES
    # --------------------------------------------------

    @http.route('/slides/embed/<int:slide_id>', type='http', auth='public', website=True, sitemap=False)
    def slides_embed(self, slide_id, page="1", **kw):
        return self._slide_embed(slide_id, page=page, is_external_embed=False, **kw)

    @http.route('/slides/embed_external/<int:slide_id>', type='http', auth='public', website=True, sitemap=False)
    def slides_embed_external(self, slide_id, page="1", **kw):
        return self._slide_embed(slide_id, page=page, is_external_embed=True, **kw)

    def _slide_embed(self, slide_id, page="1", is_external_embed=False, **kw):
        """ Note : don't use the 'model' in the route (use 'slide_id'), otherwise if public cannot
        access the embedded slide, the error will be the website.403 page instead of the one of the
        website_slides.embed_slide.

        Do not forget the rendering here will be displayed in the embedded iframe

        Try accessing slide, and display to corresponding template.

        When the content is embedded *externally*, meaning on a third party website, we do some
        additional steps like displaying sharing controls and also updating some KPIs. """

        try:
            slide = request.env['slide.slide'].browse(slide_id)
            if not slide.exists() or not slide.sudo().active:
                raise werkzeug.exceptions.NotFound()

            referer_url = request.httprequest.headers.get('Referer', '')
            if is_external_embed:
                slide.sudo()._embed_increment(referer_url)

            values = self._get_slide_detail(slide)
            values['page'] = page
            values['is_external_embed'] = is_external_embed
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
        invite_error_msg = self._get_invite_error_msg(kwargs.get('invite_error'))
        if invite_error_msg:
            values['invite_error_msg'] = invite_error_msg

        channel = self._get_channels(**kwargs)
        if channel:
            values['channel'] = channel
        return values

    def _get_channels(self, **kwargs):
        channels = []
        if kwargs.get('channel'):
            channels = kwargs['channel']
        elif kwargs.get('channel_id'):
            channels = tools.lazy(lambda: request.env['slide.channel'].browse(int(kwargs['channel_id'])))
        return channels

    @staticmethod
    def _get_invite_error_msg(invite_error):
        return {
            'expired': _('This invitation link has expired.'),
            'hash_fail': _('This invitation link has an invalid hash.'),
            'identify_fail': _('This identification link does not seem to be valid.'),
            'no_channel': _('This course does not exist.'),
            'no_partner': _('The contact associated with this invitation does not seem to be valid.'),
            'no_rights': _('You do not have permission to access this course.'),
            'partner_fail': _('This invitation link is not for this contact.'),
        }.get(invite_error, '')

    def _prepare_user_slides_profile(self, user):
        courses = request.env['slide.channel.partner'].sudo().search([('partner_id', '=', user.partner_id.id), ('member_status', '!=', 'invited')])
        courses_completed = courses.filtered(lambda c: c.member_status == 'completed')
        courses_ongoing = courses - courses_completed
        values = {
            'uid': request.env.user.id,
            'user': user,
            'main_object': user,
            'courses_completed': courses_completed,
            'courses_ongoing': courses_ongoing,
            'is_profile_page': True,
            'badge_category': 'slides',
            'my_profile': request.env.user.id == user.id,
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
