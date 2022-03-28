# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import werkzeug
import math

from ast import literal_eval
from collections import defaultdict

from odoo import http, tools, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website_profile.controllers.main import WebsiteProfile
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class WebsiteSlides(WebsiteProfile):
    _slides_per_page = 12
    _slides_per_aside = 20
    _slides_per_category = 4
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
        if request.env.user._is_public() or not slide.website_published or not slide.channel_id.is_member:
            viewed_slides = request.session.setdefault('viewed_slides', list())
            if slide.id not in viewed_slides:
                if tools.sql.increment_field_skiplock(slide, 'public_views'):
                    viewed_slides.append(slide.id)
                    request.session['viewed_slides'] = viewed_slides
        else:
            slide.action_set_viewed(quiz_attempts_inc=quiz_attempts_inc)
        return True

    def _set_completed_slide(self, slide):
        # quiz use their specific mechanism to be marked as done
        if slide.slide_type == 'quiz' or slide.question_ids:
            raise UserError(_("Slide with questions must be marked as done when submitting all good answers "))
        if slide.website_published and slide.channel_id.is_member:
            slide.action_set_completed()
        return True

    def _get_slide_detail(self, slide):
        base_domain = self._get_channel_slides_base_domain(slide.channel_id)
        if slide.channel_id.channel_type == 'documentation':
            related_domain = expression.AND([base_domain, [('category_id', '=', slide.category_id.id)]])

            most_viewed_slides = request.env['slide.slide'].search(base_domain, limit=self._slides_per_aside, order='total_views desc')
            related_slides = request.env['slide.slide'].search(related_domain, limit=self._slides_per_aside)
            category_data = []
            uncategorized_slides = request.env['slide.slide']
        else:
            most_viewed_slides, related_slides = request.env['slide.slide'], request.env['slide.slide']
            category_data = slide.channel_id._get_categorized_slides(
                base_domain, order=request.env['slide.slide']._order_by_strategy['sequence'],
                force_void=True)
            # temporarily kept for fullscreen, to remove asap
            uncategorized_domain = expression.AND([base_domain, [('channel_id', '=', slide.channel_id.id), ('category_id', '=', False)]])
            uncategorized_slides = request.env['slide.slide'].search(uncategorized_domain)

        channel_slides_ids = slide.channel_id.slide_content_ids.ids
        slide_index = channel_slides_ids.index(slide.id)
        previous_slide = slide.channel_id.slide_content_ids[slide_index-1] if slide_index > 0 else None
        next_slide = slide.channel_id.slide_content_ids[slide_index+1] if slide_index < len(channel_slides_ids) - 1 else None

        values = {
            # slide
            'slide': slide,
            'main_object': slide,
            'most_viewed_slides': most_viewed_slides,
            'related_slides': related_slides,
            'previous_slide': previous_slide,
            'next_slide': next_slide,
            'uncategorized_slides': uncategorized_slides,
            'category_data': category_data,
            # user
            'user': request.env.user,
            'is_public_user': request.website.is_public_user(),
            # rating and comments
            'comments': slide.website_message_ids or [],
        }

        # allow rating and comments
        if slide.channel_id.allow_comment:
            values.update({
                'message_post_pid': request.env.user.partner_id.id,
            })

        return values

    def _get_slide_quiz_partner_info(self, slide, quiz_done=False):
        return slide._compute_quiz_info(request.env.user.partner_id, quiz_done=quiz_done)[slide.id]

    def _get_slide_quiz_data(self, slide):
        slide_completed = slide.user_membership_id.sudo().completed
        values = {
            'slide_questions': [{
                'id': question.id,
                'question': question.question,
                'answer_ids': [{
                    'id': answer.id,
                    'text_value': answer.text_value,
                    'is_correct': answer.is_correct if slide_completed or request.website.is_publisher() else None,
                    'comment': answer.comment if request.website.is_publisher else None
                } for answer in question.sudo().answer_ids],
            } for question in slide.question_ids]
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

    def _extract_channel_tag_search(self, **post):
        tags = request.env['slide.channel.tag']
        if post.get('tags'):
            try:
                tag_ids = literal_eval(post['tags'])
            except:
                pass
            else:
                # perform a search to filter on existing / valid tags implicitely
                tags = request.env['slide.channel.tag'].search([('id', 'in', tag_ids)])
        return tags

    def _build_channel_domain(self, base_domain, slide_type=None, my=False, **post):
        search_term = post.get('search')
        tags = self._extract_channel_tag_search(**post)

        domain = base_domain
        if search_term:
            domain = expression.AND([
                domain,
                ['|', ('name', 'ilike', search_term), ('description', 'ilike', search_term)]])

        if tags:
            # Group by group_id
            grouped_tags = defaultdict(list)
            for tag in tags:
                grouped_tags[tag.group_id].append(tag)

            # OR inside a group, AND between groups.
            group_domain_list = []
            for group in grouped_tags:
                group_domain_list.append([('tag_ids', 'in', [tag.id for tag in grouped_tags[group]])])

            domain = expression.AND([domain, *group_domain_list])

        if slide_type and 'nbr_%s' % slide_type in request.env['slide.channel']:
            domain = expression.AND([domain, [('nbr_%s' % slide_type, '>', 0)]])

        if my:
            domain = expression.AND([domain, [('partner_ids', '=', request.env.user.partner_id.id)]])
        return domain

    def _channel_remove_session_answers(self, channel, slide=False):
        """ Will remove the answers saved in the session for a specific channel / slide. """

        if 'slide_answer_quiz' not in request.session:
            return

        slides_domain = [('channel_id', '=', channel.id)]
        if slide:
            slides_domain = expression.AND([slides_domain, [('id', '=', slide.id)]])
        slides = request.env['slide.slide'].search_read(slides_domain, ['id'])

        session_slide_answer_quiz = json.loads(request.session['slide_answer_quiz'])
        for slide in slides:
            session_slide_answer_quiz.pop(str(slide['id']), None)
        request.session['slide_answer_quiz'] = json.dumps(session_slide_answer_quiz)

    # TAG UTILITIES
    # --------------------------------------------------

    def _create_or_get_channel_tag(self, tag_id, group_id):
        if not tag_id:
            return request.env['slide.channel.tag']
        # handle creation of new channel tag
        if tag_id[0] == 0:
            group_id = self._create_or_get_channel_tag_group(group_id)
            if not group_id:
                return {'error': _('Missing "Tag Group" for creating a new "Tag".')}

            new_tag = request.env['slide.channel.tag'].create({
                'name': tag_id[1]['name'],
                'group_id': group_id,
            })
            return new_tag
        return request.env['slide.channel.tag'].browse(tag_id[0])

    def _create_or_get_channel_tag_group(self, group_id):
        if not group_id:
            return False
        # handle creation of new channel tag group
        if group_id[0] == 0:
            tag_group = request.env['slide.channel.tag.group'].create({
                'name': group_id[1]['name'],
            })
            group_id = tag_group.id
        # use existing channel tag group
        return group_id[0]

    # --------------------------------------------------
    # SLIDE.CHANNEL MAIN / SEARCH
    # --------------------------------------------------

    @http.route('/slides', type='http', auth="public", website=True, sitemap=True)
    def slides_channel_home(self, **post):
        """ Home page for eLearning platform. Is mainly a container page, does not allow search / filter. """
        domain = request.website.website_domain()
        channels_all = request.env['slide.channel'].search(domain)
        if not request.env.user._is_public():
            #If a course is completed, we don't want to see it in first position but in last
            channels_my = channels_all.filtered(lambda channel: channel.is_member).sorted(lambda channel: 0 if channel.completed else channel.completion, reverse=True)[:3]
        else:
            channels_my = request.env['slide.channel']
        channels_popular = channels_all.sorted('total_votes', reverse=True)[:3]
        channels_newest = channels_all.sorted('create_date', reverse=True)[:3]

        achievements = request.env['gamification.badge.user'].sudo().search([('badge_id.is_published', '=', True)], limit=5)
        if request.env.user._is_public():
            challenges = None
            challenges_done = None
        else:
            challenges = request.env['gamification.challenge'].sudo().search([
                ('challenge_category', '=', 'slides'),
                ('reward_id.is_published', '=', True)
            ], order='id asc', limit=5)
            challenges_done = request.env['gamification.badge.user'].sudo().search([
                ('challenge_id', 'in', challenges.ids),
                ('user_id', '=', request.env.user.id),
                ('badge_id.is_published', '=', True)
            ]).mapped('challenge_id')

        users = request.env['res.users'].sudo().search([
            ('karma', '>', 0),
            ('website_published', '=', True)], limit=5, order='karma desc')

        values = self._prepare_user_values(**post)
        values.update({
            'channels_my': channels_my,
            'channels_popular': channels_popular,
            'channels_newest': channels_newest,
            'achievements': achievements,
            'users': users,
            'top3_users': self._get_top3_users(),
            'challenges': challenges,
            'challenges_done': challenges_done,
            'search_tags': request.env['slide.channel.tag']
        })

        return request.render('website_slides.courses_home', values)

    @http.route('/slides/all', type='http', auth="public", website=True, sitemap=True)
    def slides_channel_all(self, slide_type=None, my=False, **post):
        """ Home page displaying a list of courses displayed according to some
        criterion and search terms.

          :param string slide_type: if provided, filter the course to contain at
           least one slide of type 'slide_type'. Used notably to display courses
           with certifications;
          :param bool my: if provided, filter the slide.channels for which the
           current user is a member of
          :param dict post: post parameters, including

           * ``search``: filter on course description / name;
           * ``channel_tag_id``: filter on courses containing this tag;
           * ``channel_tag_group_id_<id>``: filter on courses containing this tag
             in the tag group given by <id> (used in navigation based on tag group);
        """
        domain = request.website.website_domain()
        domain = self._build_channel_domain(domain, slide_type=slide_type, my=my, **post)

        order = self._channel_order_by_criterion.get(post.get('sorting'))

        channels = request.env['slide.channel'].search(domain, order=order)
        # channels_layouted = list(itertools.zip_longest(*[iter(channels)] * 4, fillvalue=None))

        tag_groups = request.env['slide.channel.tag.group'].search(
            ['&', ('tag_ids', '!=', False), ('website_published', '=', True)])
        search_tags = self._extract_channel_tag_search(**post)

        values = self._prepare_user_values(**post)
        values.update({
            'channels': channels,
            'tag_groups': tag_groups,
            'search_term': post.get('search'),
            'search_slide_type': slide_type,
            'search_my': my,
            'search_tags': search_tags,
            'search_channel_tag_id': post.get('channel_tag_id'),
            'top3_users': self._get_top3_users(),
        })

        return request.render('website_slides.courses_all', values)

    def _prepare_additional_channel_values(self, values, **kwargs):
        return values

    def _get_top3_users(self):
        return request.env['res.users'].sudo().search_read([
            ('karma', '>', 0),
            ('website_published', '=', True),
            ('image_1920', '!=', False)], ['id'], limit=3, order='karma desc')

    @http.route([
        '/slides/<model("slide.channel"):channel>',
        '/slides/<model("slide.channel"):channel>/page/<int:page>',
        '/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>',
        '/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>/page/<int:page>',
        '/slides/<model("slide.channel"):channel>/category/<model("slide.slide"):category>',
        '/slides/<model("slide.channel"):channel>/category/<model("slide.slide"):category>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=sitemap_slide)
    def channel(self, channel, category=None, tag=None, page=1, slide_type=None, uncategorized=False, sorting=None, search=None, **kw):
        """
        Will return all necessary data to display the requested slide_channel along with a possible category.
        """
        if not channel.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        domain = self._get_channel_slides_base_domain(channel)

        pager_url = "/slides/%s" % (channel.id)
        pager_args = {}
        slide_types = dict(request.env['slide.slide']._fields['slide_type']._description_selection(request.env))

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
                domain += [('tag_ids.id', '=', tag.id)]
                pager_url += "/tag/%s" % tag.id
            if uncategorized:
                domain += [('category_id', '=', False)]
                pager_args['uncategorized'] = 1
            elif slide_type:
                domain += [('slide_type', '=', slide_type)]
                pager_url += "?slide_type=%s" % slide_type

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
        elif slide_type:
            query_string = "?search_slide_type=%s" % slide_type
        elif uncategorized:
            query_string = "?search_uncategorized=1"

        values = {
            'channel': channel,
            'main_object': channel,
            'active_tab': kw.get('active_tab', 'home'),
            # search
            'search_category': category,
            'search_tag': tag,
            'search_slide_type': slide_type,
            'search_uncategorized': uncategorized,
            'query_string': query_string,
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
            # display upload modal
            'enable_slide_upload': 'enable_slide_upload' in kw,
        }
        if not request.env.user._is_public():
            last_message = request.env['mail.message'].search([
                ('model', '=', channel._name),
                ('res_id', '=', channel.id),
                ('author_id', '=', request.env.user.partner_id.id),
                ('message_type', '=', 'comment'),
                ('is_internal', '=', False)
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

        # fetch slides and handle uncategorized slides; done as sudo because we want to display all
        # of them but unreachable ones won't be clickable (+ slide controller will crash anyway)
        # documentation mode may display less slides than content by category but overhead of
        # computation is reasonable
        if channel.promote_strategy == 'specific':
            values['slide_promoted'] = channel.sudo().promoted_slide_id
        else:
            values['slide_promoted'] = request.env['slide.slide'].sudo().search(domain, limit=1, order=order)

        limit_category_data = False
        if channel.channel_type == 'documentation':
            if category or uncategorized:
                limit_category_data = self._slides_per_page
            else:
                limit_category_data = self._slides_per_category

        values['category_data'] = channel._get_categorized_slides(
            domain, order,
            force_void=not category,
            limit=limit_category_data,
            offset=pager['offset'])
        values['channel_progress'] = self._get_channel_progress(channel, include_quiz=True)

        # for sys admins: prepare data to install directly modules from eLearning when
        # uploading slides. Currently supporting only survey, because why not.
        if request.env.user.has_group('base.group_system'):
            module = request.env.ref('base.module_survey')
            if module.state != 'installed':
                values['modules_to_install'] = [{
                    'id': module.id,
                    'name': module.shortdesc,
                    'motivational': _('Evaluate and certify your students.'),
                }]

        values = self._prepare_additional_channel_values(values, **kw)
        return request.render('website_slides.course_main', values)

    # SLIDE.CHANNEL UTILS
    # --------------------------------------------------

    @http.route('/slides/channel/add', type='http', auth='user', methods=['POST'], website=True)
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

    @http.route('/slides/channel/enroll', type='http', auth='public', website=True)
    def slide_channel_join_http(self, channel_id):
        # TDE FIXME: why 2 routes ?
        if not request.website.is_public_user():
            channel = request.env['slide.channel'].browse(int(channel_id))
            channel.action_add_member()
        return werkzeug.utils.redirect("/slides/%s" % (slug(channel)))

    @http.route(['/slides/channel/join'], type='json', auth='public', website=True)
    def slide_channel_join(self, channel_id):
        if request.website.is_public_user():
            return {'error': 'public_user', 'error_signup_allowed': request.env['res.users'].sudo()._get_signup_invitation_scope() == 'b2c'}
        success = request.env['slide.channel'].browse(channel_id).action_add_member()
        if not success:
            return {'error': 'join_done'}
        return success

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

    @http.route('''/slides/slide/<model("slide.slide"):slide>''', type='http', auth="public", website=True, sitemap=True)
    def slide_view(self, slide, **kwargs):
        if not slide.channel_id.can_access_from_current_website() or not slide.active:
            raise werkzeug.exceptions.NotFound()
        # redirection to channel's homepage for category slides
        if slide.is_category:
            return werkzeug.utils.redirect(slide.channel_id.website_url)
        self._set_viewed_slide(slide)

        values = self._get_slide_detail(slide)
        # quiz-specific: update with karma and quiz information
        if slide.question_ids:
            values.update(self._get_slide_quiz_data(slide))
        # sidebar: update with user channel progress
        values['channel_progress'] = self._get_channel_progress(slide.channel_id, include_quiz=True)

        # Allows to have breadcrumb for the previously used filter
        values.update({
            'search_category': slide.category_id if kwargs.get('search_category') else None,
            'search_tag': request.env['slide.tag'].browse(int(kwargs.get('search_tag'))) if kwargs.get('search_tag') else None,
            'slide_types': dict(request.env['slide.slide']._fields['slide_type']._description_selection(request.env)) if kwargs.get('search_slide_type') else None,
            'search_slide_type': kwargs.get('search_slide_type'),
            'search_uncategorized': kwargs.get('search_uncategorized')
        })

        values['channel'] = slide.channel_id
        values = self._prepare_additional_channel_values(values, **kwargs)
        values.pop('channel', None)

        values['signup_allowed'] = request.env['res.users'].sudo()._get_signup_invitation_scope() == 'b2c'

        if kwargs.get('fullscreen') == '1':
            return request.render("website_slides.slide_fullscreen", values)
        return request.render("website_slides.slide_main", values)

    @http.route('''/slides/slide/<model("slide.slide"):slide>/pdf_content''',
                type='http', auth="public", website=True, sitemap=False)
    def slide_get_pdf_content(self, slide):
        response = werkzeug.wrappers.Response()
        response.data = slide.datas and base64.b64decode(slide.datas) or b''
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

        status, headers, image_base64 = request.env['ir.http'].sudo().binary_content(
            model='slide.slide', id=slide.id, field=field,
            default_mimetype='image/png')
        if status == 301:
            return request.env['ir.http']._response_by_status(status, headers, image_base64)
        if status == 304:
            return werkzeug.wrappers.Response(status=304)

        if not image_base64:
            image_base64 = self._get_default_avatar()
            if not (width or height):
                width, height = tools.image_guess_size_from_field_name(field)

        image_base64 = tools.image_process(image_base64, size=(int(width), int(height)), crop=crop)

        content = base64.b64decode(image_base64)
        headers = http.set_safe_image_headers(headers, content)
        response = request.make_response(content, headers)
        response.status_code = status
        return response

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

    @http.route('/slides/slide/<model("slide.slide"):slide>/set_completed', website=True, type="http", auth="user")
    def slide_set_completed_and_redirect(self, slide, next_slide_id=None):
        self._set_completed_slide(slide)
        next_slide = None
        if next_slide_id:
            next_slide = self._fetch_slide(next_slide_id).get('slide', None)
        return werkzeug.utils.redirect("/slides/slide/%s" % (slug(next_slide) if next_slide else slug(slide)))

    @http.route('/slides/slide/set_completed', website=True, type="json", auth="public")
    def slide_set_completed(self, slide_id):
        if request.website.is_public_user():
            return {'error': 'public_user'}
        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            return fetch_res
        self._set_completed_slide(fetch_res['slide'])
        return {
            'channel_completion': fetch_res['slide'].channel_id.completion
        }

    @http.route('/slides/slide/like', type='json', auth="public", website=True)
    def slide_like(self, slide_id, upvote):
        if request.website.is_public_user():
            return {'error': 'public_user', 'error_signup_allowed': request.env['res.users'].sudo()._get_signup_invitation_scope() == 'b2c'}
        slide_partners = request.env['slide.slide.partner'].sudo().search([
            ('slide_id', '=', slide_id),
            ('partner_id', '=', request.env.user.partner_id.id)
        ])
        if (upvote and slide_partners.vote == 1) or (not upvote and slide_partners.vote == -1):
            return {'error': 'vote_done'}
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
        slide.invalidate_cache()
        return slide.read(['likes', 'dislikes', 'user_vote'])[0]

    @http.route('/slides/slide/archive', type='json', auth='user', website=True)
    def slide_archive(self, slide_id):
        """ This route allows channel publishers to archive slides.
        It has to be done in sudo mode since only website_publishers can write on slides in ACLs """
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
    def slide_send_share_email(self, slide_id, email, fullscreen=False):
        slide = request.env['slide.slide'].browse(int(slide_id))
        result = slide._send_share_email(email, fullscreen)
        return result

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

        slide_question = request.env['slide.question'].create({
            'sequence': sequence,
            'question': question,
            'slide_id': slide_id,
            'answer_ids': [(0, 0, {
                'sequence': answer['sequence'],
                'text_value': answer['text_value'],
                'is_correct': answer['is_correct'],
                'comment': answer['comment']
            }) for answer in answer_ids]
        })
        return request.env.ref('website_slides.lesson_content_quiz_question')._render({
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

        if slide.user_membership_id.sudo().completed:
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
            slide._action_set_quiz_done()
            slide.action_set_completed()
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
            'completed': slide.user_membership_id.sudo().completed,
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

        return werkzeug.utils.redirect("/slides/%s" % (slug(channel)))

    # --------------------------------------------------
    # SLIDE.UPLOAD
    # --------------------------------------------------

    @http.route(['/slides/prepare_preview'], type='json', auth='user', methods=['POST'], website=True)
    def prepare_preview(self, **data):
        Slide = request.env['slide.slide']
        unused, document_id = Slide._find_document_data_from_url(data['url'])
        preview = {}
        if not document_id:
            preview['error'] = _('Please enter valid youtube or google doc url')
            return preview
        existing_slide = Slide.search([('channel_id', '=', int(data['channel_id'])), ('document_id', '=', document_id)], limit=1)
        if existing_slide:
            preview['error'] = _('This video already exists in this channel on the following slide: %s', existing_slide.name)
            return preview
        values = Slide._parse_document_url(data['url'], only_preview_fields=True)
        if values.get('error'):
            preview['error'] = values['error']
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
            values['is_published'] = values.get('is_published', False) and can_publish
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
        if channel.channel_type == "training" and not slide.slide_type == "webpage":
            redirect_url = "/slides/%s" % (slug(channel))
        if slide.slide_type == 'webpage':
            redirect_url += "?enable_editor=1"
        return {
            'url': redirect_url,
            'channel_type': channel.channel_type,
            'slide_id': slide.id,
            'category_id': slide.category_id
        }

    def _get_valid_slide_post_values(self):
        return ['name', 'url', 'tag_ids', 'slide_type', 'channel_id', 'is_preview',
                'mime_type', 'datas', 'description', 'image_1920', 'is_published']

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
                request.env['slide.embed'].sudo()._add_embed_url(slide.id, referrer_url)
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
        courses = request.env['slide.channel.partner'].sudo().search([('partner_id', '=', user.partner_id.id)])
        courses_completed = courses.filtered(lambda c: c.completed)
        courses_ongoing = courses - courses_completed
        values = {
            'uid': request.env.user.id,
            'user': user,
            'main_object': user,
            'courses_completed': courses_completed,
            'courses_ongoing': courses_ongoing,
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
