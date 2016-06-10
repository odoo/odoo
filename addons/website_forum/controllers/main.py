# -*- coding: utf-8 -*-

import werkzeug.exceptions
import werkzeug.urls
import werkzeug.wrappers
import simplejson

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.controllers.main import login_redirect
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import Website as controllers
from openerp.addons.website.models.website import slug

controllers = controllers()


class WebsiteForum(http.Controller):
    _post_per_page = 10
    _user_per_page = 30

    def _get_notifications(self):
        cr, uid, context = request.cr, request.uid, request.context
        Message = request.registry['mail.message']
        badge_st_id = request.registry['ir.model.data'].xmlid_to_res_id(cr, uid, 'gamification.mt_badge_granted')
        if badge_st_id:
            msg_ids = Message.search(cr, uid, [('subtype_id', '=', badge_st_id), ('to_read', '=', True)], context=context)
            msg = Message.browse(cr, uid, msg_ids, context=context)
        else:
            msg = list()
        return msg

    def _prepare_forum_values(self, forum=None, **kwargs):
        user = request.registry['res.users'].browse(request.cr, request.uid, request.uid, context=request.context)
        values = {
            'user': user,
            'is_public_user': user.id == request.website.user_id.id,
            'notifications': self._get_notifications(),
            'header': kwargs.get('header', dict()),
            'searches': kwargs.get('searches', dict()),
            'validation_email_sent': request.session.get('validation_email_sent', False),
            'validation_email_done': request.session.get('validation_email_done', False),
        }
        if forum:
            values['forum'] = forum
        elif kwargs.get('forum_id'):
            values['forum'] = request.registry['forum.forum'].browse(request.cr, request.uid, kwargs.pop('forum_id'), context=request.context)
        values.update(kwargs)
        return values

    # User and validation
    # --------------------------------------------------

    @http.route('/forum/send_validation_email', type='json', auth='user', website=True)
    def send_validation_email(self, forum_id=None, **kwargs):
        request.registry['res.users'].send_forum_validation_email(request.cr, request.uid, request.uid, forum_id=forum_id, context=request.context)
        request.session['validation_email_sent'] = True
        return True

    @http.route('/forum/validate_email', type='http', auth='public', website=True)
    def validate_email(self, token, id, email, forum_id=None, **kwargs):
        if forum_id:
            try:
                forum_id = int(forum_id)
            except ValueError:
                forum_id = None
        done = request.registry['res.users'].process_forum_validation_token(request.cr, request.uid, token, int(id), email, forum_id=forum_id, context=request.context)
        if done:
            request.session['validation_email_done'] = True
        if forum_id:
            return request.redirect("/forum/%s" % int(forum_id))
        return request.redirect('/forum')

    @http.route('/forum/validate_email/close', type='json', auth='public', website=True)
    def validate_email_done(self):
        request.session['validation_email_done'] = False
        return True

    # Forum
    # --------------------------------------------------

    @http.route(['/forum'], type='http', auth="public", website=True)
    def forum(self, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        Forum = request.registry['forum.forum']
        obj_ids = Forum.search(cr, uid, [], context=context)
        forums = Forum.browse(cr, uid, obj_ids, context=context)
        return request.website.render("website_forum.forum_all", {'forums': forums})

    @http.route('/forum/new', type='http', auth="user", methods=['POST'], website=True)
    def forum_create(self, forum_name="New Forum", **kwargs):
        forum_id = request.registry['forum.forum'].create(request.cr, request.uid, {
            'name': forum_name,
        }, context=request.context)
        return request.redirect("/forum/%s" % forum_id)

    @http.route('/forum/notification_read', type='json', auth="user", methods=['POST'], website=True)
    def notification_read(self, **kwargs):
        request.registry['mail.message'].set_message_read(request.cr, request.uid, [int(kwargs.get('notification_id'))], read=True, context=request.context)
        return True

    @http.route(['/forum/<model("forum.forum"):forum>',
                 '/forum/<model("forum.forum"):forum>/page/<int:page>',
                 '''/forum/<model("forum.forum"):forum>/tag/<model("forum.tag", "[('forum_id','=',forum[0])]"):tag>/questions''',
                 '''/forum/<model("forum.forum"):forum>/tag/<model("forum.tag", "[('forum_id','=',forum[0])]"):tag>/questions/page/<int:page>''',
                 ], type='http', auth="public", website=True)
    def questions(self, forum, tag=None, page=1, filters='all', sorting='date', search='', **post):
        cr, uid, context = request.cr, request.uid, request.context
        Post = request.registry['forum.post']
        user = request.registry['res.users'].browse(cr, uid, uid, context=context)

        domain = [('forum_id', '=', forum.id), ('parent_id', '=', False), ('state', '=', 'active')]
        if search:
            domain += ['|', ('name', 'ilike', search), ('content', 'ilike', search)]
        if tag:
            domain += [('tag_ids', 'in', tag.id)]
        if filters == 'unanswered':
            domain += [('child_ids', '=', False)]
        elif filters == 'followed':
            domain += [('message_follower_ids', '=', user.partner_id.id)]
        else:
            filters = 'all'

        if sorting == 'answered':
            order = 'child_count desc'
        elif sorting == 'vote':
            order = 'vote_count desc'
        elif sorting == 'date':
            order = 'write_date desc'
        else:
            sorting = 'creation'
            order = 'create_date desc'

        question_count = Post.search(cr, uid, domain, count=True, context=context)
        if tag:
            url = "/forum/%s/tag/%s/questions" % (slug(forum), slug(tag))
        else:
            url = "/forum/%s" % slug(forum)

        url_args = {}
        if search:
            url_args['search'] = search
        if filters:
            url_args['filters'] = filters
        if sorting:
            url_args['sorting'] = sorting
        pager = request.website.pager(url=url, total=question_count, page=page,
                                      step=self._post_per_page, scope=self._post_per_page,
                                      url_args=url_args)

        obj_ids = Post.search(cr, uid, domain, limit=self._post_per_page, offset=pager['offset'], order=order, context=context)
        question_ids = Post.browse(cr, uid, obj_ids, context=context)

        values = self._prepare_forum_values(forum=forum, searches=post)
        values.update({
            'main_object': tag or forum,
            'question_ids': question_ids,
            'question_count': question_count,
            'pager': pager,
            'tag': tag,
            'filters': filters,
            'sorting': sorting,
            'search': search,
        })
        return request.website.render("website_forum.forum_index", values)

    @http.route(['/forum/<model("forum.forum"):forum>/faq'], type='http', auth="public", website=True)
    def forum_faq(self, forum, **post):
        values = self._prepare_forum_values(forum=forum, searches=dict(), header={'is_guidelines': True}, **post)
        return request.website.render("website_forum.faq", values)

    @http.route('/forum/get_tags', type='http', auth="public", methods=['GET'], website=True)
    def tag_read(self, q='', l=25, t='texttext', **post):
        data = request.registry['forum.tag'].search_read(
            request.cr,
            request.uid,
            domain=[('name', '=ilike', (q or '') + "%")],
            fields=['id', 'name'],
            limit=int(l),
            context=request.context
        )
        if t == 'texttext':
            # old tag with texttext - Retro for V8 - #TODO Remove in master
            data = [tag['name'] for tag in data]
        return simplejson.dumps(data)

    @http.route(['/forum/<model("forum.forum"):forum>/tag'], type='http', auth="public", website=True)
    def tags(self, forum, page=1, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Tag = request.registry['forum.tag']
        obj_ids = Tag.search(cr, uid, [('forum_id', '=', forum.id), ('posts_count', '>', 0)], limit=None, order='posts_count DESC', context=context)
        tags = Tag.browse(cr, uid, obj_ids, context=context)
        values = self._prepare_forum_values(forum=forum, searches={'tags': True}, **post)
        values.update({
            'tags': tags,
            'main_object': forum,
        })
        return request.website.render("website_forum.tag", values)

    # Questions
    # --------------------------------------------------

    @http.route(['/forum/<model("forum.forum"):forum>/ask'], type='http', auth="public", website=True)
    def question_ask(self, forum, **post):
        if not request.session.uid:
            return login_redirect()
        values = self._prepare_forum_values(forum=forum, searches={}, header={'ask_hide': True})
        return request.website.render("website_forum.ask_question", values)

    @http.route('/forum/<model("forum.forum"):forum>/question/new', type='http', auth="user", methods=['POST'], website=True)
    def question_create(self, forum, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Tag = request.registry['forum.tag']
        Forum = request.registry['forum.forum']
        question_tag_ids = []
        tag_version = post.get('tag_type', 'texttext')
        if tag_version == "texttext":  # TODO Remove in master
            if post.get('question_tags').strip('[]'):
                tags = post.get('question_tags').strip('[]').replace('"', '').split(",")
                for tag in tags:
                    tag_ids = Tag.search(cr, uid, [('name', '=', tag)], context=context)
                    if tag_ids:
                        question_tag_ids.append((4, tag_ids[0]))
                    else:
                        question_tag_ids.append((0, 0, {'name': tag, 'forum_id': forum.id}))
                question_tag_ids = {forum.id: question_tag_ids}
        elif tag_version == "select2":
            question_tag_ids = Forum._tag_to_write_vals(cr, uid, [forum.id], post.get('question_tags', ''), context)

        new_question_id = request.registry['forum.post'].create(
            request.cr, request.uid, {
                'forum_id': forum.id,
                'name': post.get('question_name'),
                'content': post.get('content'),
                'tag_ids': question_tag_ids[forum.id],
            }, context=context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), new_question_id))

    @http.route(['''/forum/<model("forum.forum"):forum>/question/<model("forum.post", "[('forum_id','=',forum[0]),('parent_id','=',False)]"):question>'''], type='http', auth="public", website=True)
    def question(self, forum, question, **post):
        cr, uid, context = request.cr, request.uid, request.context

        # Hide posts from abusers (negative karma), except for moderators
        if not question.can_view:
            raise werkzeug.exceptions.NotFound()

        # increment view counter
        request.registry['forum.post'].set_viewed(cr, SUPERUSER_ID, [question.id], context=context)

        if question.parent_id:
            redirect_url = "/forum/%s/question/%s" % (slug(forum), slug(question.parent_id))
            return werkzeug.utils.redirect(redirect_url, 301)

        filters = 'question'
        values = self._prepare_forum_values(forum=forum, searches=post)
        values.update({
            'main_object': question,
            'question': question,
            'header': {'question_data': True},
            'filters': filters,
            'reversed': reversed,
        })
        return request.website.render("website_forum.post_description_full", values)

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/toggle_favourite', type='json', auth="user", methods=['POST'], website=True)
    def question_toggle_favorite(self, forum, question, **post):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        # TDE: add check for not public
        favourite = False if question.user_favourite else True
        if favourite:
            favourite_ids = [(4, request.uid)]
        else:
            favourite_ids = [(3, request.uid)]
        request.registry['forum.post'].write(request.cr, request.uid, [question.id], {'favourite_ids': favourite_ids}, context=request.context)
        return favourite

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/ask_for_close', type='http', auth="user", methods=['POST'], website=True)
    def question_ask_for_close(self, forum, question, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Reason = request.registry['forum.post.reason']
        reason_ids = Reason.search(cr, uid, [], context=context)
        reasons = Reason.browse(cr, uid, reason_ids, context)

        values = self._prepare_forum_values(**post)
        values.update({
            'question': question,
            'question': question,
            'forum': forum,
            'reasons': reasons,
        })
        return request.website.render("website_forum.close_question", values)

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/edit_answer', type='http', auth="user", website=True)
    def question_edit_answer(self, forum, question, **kwargs):
        for record in question.child_ids:
            if record.create_uid.id == request.uid:
                answer = record
                break
        return werkzeug.utils.redirect("/forum/%s/post/%s/edit" % (slug(forum), slug(answer)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/close', type='http', auth="user", methods=['POST'], website=True)
    def question_close(self, forum, question, **post):
        request.registry['forum.post'].close(request.cr, request.uid, [question.id], reason_id=int(post.get('reason_id', False)), context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/reopen', type='http', auth="user", methods=['POST'], website=True)
    def question_reopen(self, forum, question, **kwarg):
        request.registry['forum.post'].reopen(request.cr, request.uid, [question.id], context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/delete', type='http', auth="user", methods=['POST'], website=True)
    def question_delete(self, forum, question, **kwarg):
        request.registry['forum.post'].write(request.cr, request.uid, [question.id], {'active': False}, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/undelete', type='http', auth="user", methods=['POST'], website=True)
    def question_undelete(self, forum, question, **kwarg):
        request.registry['forum.post'].write(request.cr, request.uid, [question.id], {'active': True}, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    # Post
    # --------------------------------------------------

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/new', type='http', auth="public", website=True)
    def post_new(self, forum, post, **kwargs):
        if not request.session.uid:
            return login_redirect()
        cr, uid, context = request.cr, request.uid, request.context
        user = request.registry['res.users'].browse(cr, SUPERUSER_ID, uid, context=context)
        if not user.email or not tools.single_email_re.match(user.email):
            return werkzeug.utils.redirect("/forum/%s/user/%s/edit?email_required=1" % (slug(forum), uid))
        request.registry['forum.post'].create(
            request.cr, request.uid, {
                'forum_id': forum.id,
                'parent_id': post.id,
                'content': kwargs.get('content'),
            }, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(post)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment', type='http', auth="public", website=True)
    def post_comment(self, forum, post, **kwargs):
        if not request.session.uid:
            return login_redirect()
        question = post.parent_id if post.parent_id else post
        cr, uid, context = request.cr, request.uid, request.context
        if kwargs.get('comment') and post.forum_id.id == forum.id:
            # TDE FIXME: check that post_id is the question or one of its answers
            body = tools.mail.plaintext2html(kwargs['comment'])
            request.registry['forum.post'].message_post(
                cr, uid, post.id,
                body=body,
                type='comment',
                subtype='mt_comment',
                context=dict(context, mail_create_nosubscribe=True))
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/toggle_correct', type='json', auth="public", website=True)
    def post_toggle_correct(self, forum, post, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        if post.parent_id is False:
            return request.redirect('/')
        if not request.session.uid:
            return {'error': 'anonymous_user'}

        # set all answers to False, only one can be accepted
        request.registry['forum.post'].write(cr, uid, [c.id for c in post.parent_id.child_ids if not c.id == post.id], {'is_correct': False}, context=context)
        request.registry['forum.post'].write(cr, uid, [post.id], {'is_correct': not post.is_correct}, context=context)
        return post.is_correct

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/delete', type='http', auth="user", methods=['POST'], website=True)
    def post_delete(self, forum, post, **kwargs):
        question = post.parent_id
        request.registry['forum.post'].unlink(request.cr, request.uid, [post.id], context=request.context)
        if question:
            werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))
        return werkzeug.utils.redirect("/forum/%s" % slug(forum))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/edit', type='http', auth="user", website=True)
    def post_edit(self, forum, post, **kwargs):
        tag_version = kwargs.get('tag_type', 'texttext')
        if tag_version == "texttext":  # old version - retro v8 - #TODO Remove in master
            tags = ""
            for tag_name in post.tag_ids:
                tags += tag_name.name + ","
        elif tag_version == "select2":  # new version
            tags = [dict(id=tag.id, name=tag.name) for tag in post.tag_ids]
            tags = simplejson.dumps(tags)
        values = self._prepare_forum_values(forum=forum)

        values.update({
            'tags': tags,
            'post': post,
            'is_answer': bool(post.parent_id),
            'searches': kwargs
        })
        return request.website.render("website_forum.edit_post", values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/edition', type='http', auth="user", website=True)
    def post_edit_retro(self, forum, post, **kwargs):
        # This function is only there for retrocompatibility between old template using texttext and template using select2
        # It should be removed into master  #TODO JKE: remove in master all condition with tag_type
        kwargs.update(tag_type="select2")
        return self.post_edit(forum, post, **kwargs)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/save', type='http', auth="user", methods=['POST'], website=True)
    def post_save(self, forum, post, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        question_tags = []
        Tag = request.registry['forum.tag']
        Forum = request.registry['forum.forum']
        tag_version = kwargs.get('tag_type', 'texttext')
        
        vals = {
            'name': kwargs.get('question_name'),
            'content': kwargs.get('content'),
        }
        if tag_version == "texttext":  # old version - retro v8 - #TODO Remove in master
            if kwargs.get('question_tag') and kwargs.get('question_tag').strip('[]'):
                tags = kwargs.get('question_tag').strip('[]').replace('"', '').split(",")
                for tag in tags:
                    tag_ids = Tag.search(cr, uid, [('name', '=', tag)], context=context)
                    if tag_ids:
                        question_tags += tag_ids
                    else:
                        new_tag = Tag.create(cr, uid, {'name': tag, 'forum_id': forum.id}, context=context)
                        question_tags.append(new_tag)
                vals['tag_ids'] = [(6, 0, question_tags)]
        elif tag_version == "select2":  # new version
            vals['tag_ids'] = Forum._tag_to_write_vals(cr, uid, [forum.id], kwargs.get('question_tag', ''), context)[forum.id]

        request.registry['forum.post'].write(cr, uid, [post.id], vals, context=context)
        question = post.parent_id if post.parent_id else post
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/upvote', type='json', auth="public", website=True)
    def post_upvote(self, forum, post, **kwargs):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        if request.uid == post.create_uid.id:
            return {'error': 'own_post'}
        upvote = True if not post.user_vote > 0 else False
        return request.registry['forum.post'].vote(request.cr, request.uid, [post.id], upvote=upvote, context=request.context)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/downvote', type='json', auth="public", website=True)
    def post_downvote(self, forum, post, **kwargs):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        if request.uid == post.create_uid.id:
            return {'error': 'own_post'}
        upvote = True if post.user_vote < 0 else False
        return request.registry['forum.post'].vote(request.cr, request.uid, [post.id], upvote=upvote, context=request.context)

    # User
    # --------------------------------------------------

    @http.route(['/forum/<model("forum.forum"):forum>/users',
                 '/forum/<model("forum.forum"):forum>/users/page/<int:page>'],
                type='http', auth="public", website=True)
    def users(self, forum, page=1, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        User = request.registry['res.users']

        step = 30
        tag_count = User.search(cr, SUPERUSER_ID, [('karma', '>', 1), ('website_published', '=', True)], count=True, context=context)
        pager = request.website.pager(url="/forum/%s/users" % slug(forum), total=tag_count, page=page, step=step, scope=30)

        obj_ids = User.search(cr, SUPERUSER_ID, [('karma', '>', 1), ('website_published', '=', True)], limit=step, offset=pager['offset'], order='karma DESC', context=context)
        # put the users in block of 3 to display them as a table
        users = [[] for i in range(len(obj_ids)/3+1)]
        for index, user in enumerate(User.browse(cr, SUPERUSER_ID, obj_ids, context=context)):
            users[index/3].append(user)
        searches['users'] = 'True'

        values = self._prepare_forum_values(forum=forum, searches=searches)
        values .update({
            'users': users,
            'main_object': forum,
            'notifications': self._get_notifications(),
            'pager': pager,
        })

        return request.website.render("website_forum.users", values)

    @http.route(['/forum/<model("forum.forum"):forum>/partner/<int:partner_id>'], type='http', auth="public", website=True)
    def open_partner(self, forum, partner_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        if partner_id:
            partner = request.registry['res.partner'].browse(cr, SUPERUSER_ID, partner_id, context=context)
            if partner.exists() and partner.user_ids:
                return werkzeug.utils.redirect("/forum/%s/user/%d" % (slug(forum), partner.user_ids[0].id))
        return werkzeug.utils.redirect("/forum/%s" % slug(forum))

    @http.route(['/forum/user/<int:user_id>/avatar'], type='http', auth="public", website=True)
    def user_avatar(self, user_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        response = werkzeug.wrappers.Response()
        User = request.registry['res.users']
        Website = request.registry['website']
        user = User.browse(cr, SUPERUSER_ID, user_id, context=context)
        if not user.exists() or (user_id != request.session.uid and user.karma < 1):
            return Website._image_placeholder(response)
        return Website._image(cr, SUPERUSER_ID, 'res.users', user.id, 'image', response)

    @http.route(['/forum/<model("forum.forum"):forum>/user/<int:user_id>'], type='http', auth="public", website=True)
    def open_user(self, forum, user_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        User = request.registry['res.users']
        Post = request.registry['forum.post']
        Vote = request.registry['forum.post.vote']
        Activity = request.registry['mail.message']
        Followers = request.registry['mail.followers']
        Data = request.registry["ir.model.data"]

        user = User.browse(cr, SUPERUSER_ID, user_id, context=context)
        current_user = User.browse(cr, SUPERUSER_ID, uid, context=context)

        # Users with high karma can see users with karma <= 0 for
        # moderation purposes, IFF they have posted something (see below)
        if (not user.exists() or
               (user.karma < 1 and current_user.karma < forum.karma_unlink_all)):
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))
        values = self._prepare_forum_values(forum=forum, **post)

        # questions and answers by user
        user_question_ids = Post.search(cr, uid, [
                ('parent_id', '=', False),
                ('forum_id', '=', forum.id), ('create_uid', '=', user.id),
            ], order='create_date desc', context=context)
        count_user_questions = len(user_question_ids)

        if (user_id != request.session.uid and not
                (user.website_published or
                    (count_user_questions and current_user.karma > forum.karma_unlink_all))):
            return request.website.render("website_forum.private_profile", values)

        # limit length of visible posts by default for performance reasons, except for the high
        # karma users (not many of them, and they need it to properly moderate the forum)
        post_display_limit = None
        if current_user.karma < forum.karma_unlink_all:
            post_display_limit = 20

        user_questions = Post.browse(cr, uid, user_question_ids[:post_display_limit], context=context)
        user_answer_ids = Post.search(cr, uid, [
                ('parent_id', '!=', False),
                ('forum_id', '=', forum.id), ('create_uid', '=', user.id),
            ], order='create_date desc', context=context)
        count_user_answers = len(user_answer_ids)
        user_answers = Post.browse(cr, uid, user_answer_ids[:post_display_limit], context=context)

        # showing questions which user following
        obj_ids = Followers.search(cr, SUPERUSER_ID, [('res_model', '=', 'forum.post'), ('partner_id', '=', user.partner_id.id)], context=context)
        post_ids = [follower.res_id for follower in Followers.browse(cr, SUPERUSER_ID, obj_ids, context=context)]
        que_ids = Post.search(cr, uid, [('id', 'in', post_ids), ('forum_id', '=', forum.id), ('parent_id', '=', False)], context=context)
        followed = Post.browse(cr, uid, que_ids, context=context)

        #showing Favourite questions of user.
        fav_que_ids = Post.search(cr, uid, [('favourite_ids', '=', user.id), ('forum_id', '=', forum.id), ('parent_id', '=', False)], context=context)
        favourite = Post.browse(cr, uid, fav_que_ids, context=context)

        #votes which given on users questions and answers.
        data = Vote.read_group(cr, uid, [('forum_id', '=', forum.id), ('recipient_id', '=', user.id)], ["vote"], groupby=["vote"], context=context)
        up_votes, down_votes = 0, 0
        for rec in data:
            if rec['vote'] == '1':
                up_votes = rec['vote_count']
            elif rec['vote'] == '-1':
                down_votes = rec['vote_count']

        #Votes which given by users on others questions and answers.
        post_votes = Vote.search(cr, uid, [('user_id', '=', user.id)], context=context)
        vote_ids = Vote.browse(cr, uid, post_votes, context=context)

        #activity by user.
        model, comment = Data.get_object_reference(cr, uid, 'mail', 'mt_comment')
        activity_ids = Activity.search(cr, uid, [('res_id', 'in', user_question_ids+user_answer_ids), ('model', '=', 'forum.post'), ('subtype_id', '!=', comment)], order='date DESC', limit=100, context=context)
        activities = Activity.browse(cr, uid, activity_ids, context=context)

        posts = {}
        for act in activities:
            posts[act.res_id] = True
        posts_ids = Post.browse(cr, uid, posts.keys(), context=context)
        posts = dict(map(lambda x: (x.id, (x.parent_id or x, x.parent_id and x or False)), posts_ids))

        # TDE CLEANME MASTER: couldn't it be rewritten using a 'menu' key instead of one key for each menu ?
        if user.id == uid:
            post['my_profile'] = True
        else:
            post['users'] = True

        values.update({
            'uid': uid,
            'user': user,
            'main_object': user,
            'searches': post,
            'questions': user_questions,
            'count_questions': count_user_questions,
            'answers': user_answers,
            'count_answers': count_user_answers,
            'followed': followed,
            'favourite': favourite,
            'up_votes': up_votes,
            'down_votes': down_votes,
            'activities': activities,
            'posts': posts,
            'vote_post': vote_ids,
        })
        return request.website.render("website_forum.user_detail_full", values)

    @http.route('/forum/<model("forum.forum"):forum>/user/<model("res.users"):user>/edit', type='http', auth="user", website=True)
    def edit_profile(self, forum, user, **kwargs):
        country = request.registry['res.country']
        country_ids = country.search(request.cr, SUPERUSER_ID, [], context=request.context)
        countries = country.browse(request.cr, SUPERUSER_ID, country_ids, context=request.context)
        values = self._prepare_forum_values(forum=forum, searches=kwargs)
        values.update({
            'email_required': kwargs.get('email_required'),
            'countries': countries,
            'notifications': self._get_notifications(),
        })
        return request.website.render("website_forum.edit_profile", values)

    @http.route('/forum/<model("forum.forum"):forum>/user/<model("res.users"):user>/save', type='http', auth="user", methods=['POST'], website=True)
    def save_edited_profile(self, forum, user, **kwargs):
        values = {
            'name': kwargs.get('name'),
            'website': kwargs.get('website'),
            'email': kwargs.get('email'),
            'city': kwargs.get('city'),
            'country_id': int(kwargs.get('country')) if kwargs.get('country') else False,
            'website_description': kwargs.get('description'),
        }
        if request.uid == user.id:  # the controller allows to edit only its own privacy settings; use partner management for other cases
            values['website_published'] = kwargs.get('website_published') == 'True'
        request.registry['res.users'].write(request.cr, request.uid, [user.id], values, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/user/%d" % (slug(forum), user.id))

    # Badges
    # --------------------------------------------------

    @http.route('/forum/<model("forum.forum"):forum>/badge', type='http', auth="public", website=True)
    def badges(self, forum, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        Badge = request.registry['gamification.badge']
        badge_ids = Badge.search(cr, SUPERUSER_ID, [('challenge_ids.category', '=', 'forum')], context=context)
        badges = Badge.browse(cr, uid, badge_ids, context=context)
        badges = sorted(badges, key=lambda b: b.stat_count_distinct, reverse=True)
        values = self._prepare_forum_values(forum=forum, searches={'badges': True})
        values.update({
            'badges': badges,
        })
        return request.website.render("website_forum.badge", values)

    @http.route(['''/forum/<model("forum.forum"):forum>/badge/<model("gamification.badge"):badge>'''], type='http', auth="public", website=True)
    def badge_users(self, forum, badge, **kwargs):
        user_ids = [badge_user.user_id.id for badge_user in badge.owner_ids]
        users = request.registry['res.users'].browse(request.cr, SUPERUSER_ID, user_ids, context=request.context)
        values = self._prepare_forum_values(forum=forum, searches={'badges': True})
        values.update({
            'badge': badge,
            'users': users,
        })
        return request.website.render("website_forum.badge_user", values)

    # Messaging
    # --------------------------------------------------

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment/<model("mail.message"):comment>/convert_to_answer', type='http', auth="user", methods=['POST'], website=True)
    def convert_comment_to_answer(self, forum, post, comment, **kwarg):
        new_post_id = request.registry['forum.post'].convert_comment_to_answer(request.cr, request.uid, comment.id, context=request.context)
        if not new_post_id:
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))
        post = request.registry['forum.post'].browse(request.cr, request.uid, new_post_id, context=request.context)
        question = post.parent_id if post.parent_id else post
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/convert_to_comment', type='http', auth="user", methods=['POST'], website=True)
    def convert_answer_to_comment(self, forum, post, **kwarg):
        question = post.parent_id
        new_msg_id = request.registry['forum.post'].convert_answer_to_comment(request.cr, request.uid, post.id, context=request.context)
        if not new_msg_id:
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment/<model("mail.message"):comment>/delete', type='json', auth="user", website=True)
    def delete_comment(self, forum, post, comment, **kwarg):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        return request.registry['forum.post'].unlink_comment(request.cr, request.uid, post.id, comment.id, context=request.context)
