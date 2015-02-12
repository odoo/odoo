# -*- coding: utf-8 -*-
import openerp
import openerp.addons.im_chat.im_chat
import random
import re

from openerp.osv import osv, fields
from openerp import api, models, tools
from openerp import SUPERUSER_ID


class im_livechat_channel(osv.Model):
    _name = 'im_livechat.channel'

    def _get_default_image(self, cr, uid, context=None):
        image_path = openerp.modules.get_module_resource('im_livechat', 'static/src/img', 'default.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))
    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result
    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    def _are_you_inside(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = False
            for user in record.user_ids:
                if user.id == uid:
                    res[record.id] = True
                    break
        return res

    def _script_external(self, cr, uid, ids, name, arg, context=None):
        values = {
            "url": self.pool.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url'),
            "dbname":cr.dbname
        }
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            values["channel"] = record.id
            res[record.id] = self.pool['ir.ui.view'].render(cr, uid, 'im_livechat.external_loader', values, context=context)
        return res

    def _script_internal(self, cr, uid, ids, name, arg, context=None):
        values = {
            "url": self.pool.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url'),
            "dbname":cr.dbname
        }
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            values["channel"] = record.id
            res[record.id] = self.pool['ir.ui.view'].render(cr, uid, 'im_livechat.internal_loader', values, context=context)
        return res

    def _web_page(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.pool.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url') + \
                "/im_livechat/support/%s/%i" % (cr.dbname, record.id)
        return res

    def _compute_nbr_session(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = len(record.session_ids)
        return res

    # RATING METHOD
    def _compute_percentage_satisfaction(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            repartition = record.session_ids.rating_get_grades()
            total = sum(repartition.values())
            if total > 0:
                happy = repartition['great']
                res[record.id] = ((happy*100) / total) if happy > 0 else 0
            else:
                res[record.id] = -1
        return res

    def action_view_rating(self, cr, uid, ids, context=None):
        channels = self.browse(cr, uid, ids, context=context)
        action = self.pool['ir.actions.act_window'].for_xml_id(cr, uid, 'rating', 'action_view_rating', context=context)
        action['domain'] = [('res_id', 'in', [s.id for s in channels.session_ids]), ('res_model', '=', 'im_chat.session')]
        return action

    _columns = {
        'name': fields.char(string="Channel Name", size=200, required=True),
        'user_ids': fields.many2many('res.users', 'im_livechat_channel_im_user', 'channel_id', 'user_id', string="Users"),
        'are_you_inside': fields.function(_are_you_inside, type='boolean', string='Are you inside the matrix?', store=False),
        'script_internal': fields.function(_script_internal, type='text', string='Script (internal)', store=False),
        'script_external': fields.function(_script_external, type='text', string='Script (external)', store=False),
        'web_page': fields.function(_web_page, type='char', string='Web Page', store=False),
        'button_text': fields.char(string="Text of the Button"),
        'input_placeholder': fields.char(string="Chat Input Placeholder"),
        'default_message': fields.char(string="Welcome Message", help="This is an automated 'welcome' message that your visitor will see when they initiate a new chat session."),
        # image: all image fields are base64 encoded and PIL-supported
        'image': fields.binary("Photo",
            help="This field holds the image used as photo for the group, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized photo", type="binary", multi="_get_image",
            store={
                'im_livechat.channel': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized photo of the group. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized photo", type="binary", multi="_get_image",
            store={
                'im_livechat.channel': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized photo of the group. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
        'session_ids' : fields.one2many('im_chat.session', 'channel_id', 'Sessions'),
        'nbr_session' : fields.function(_compute_nbr_session, type='integer', string='Number of session', store=False),
        'rule_ids': fields.one2many('im_livechat.channel.rule','channel_id','Rules'),
        # rating field
        'rating_percentage_satisfaction' : fields.function(_compute_percentage_satisfaction, type='integer', string='% Happy', store=False, default=-1),
    }

    def _default_user_ids(self, cr, uid, context=None):
        return [(6, 0, [uid])]

    _defaults = {
        'button_text': "Have a Question? Chat with us.",
        'input_placeholder': "How may I help you?",
        'default_message': '',
        'user_ids': _default_user_ids,
        'image': _get_default_image,
    }

    def get_available_users(self, cr, uid, channel_id, context=None):
        """ get available user of a given channel """
        channel = self.browse(cr, SUPERUSER_ID, channel_id, context=context)
        users = []
        for user_id in channel.user_ids:
            if (user_id.im_status == 'online'):
                users.append(user_id)
        return users

    def get_channel_session(self, cr, uid, channel_id, anonymous_name, context=None):
        """ return a session given a channel : create on with a registered user, or return false otherwise """
        # get the avalable user of the channel
        users = self.get_available_users(cr, SUPERUSER_ID, channel_id, context=context)
        if len(users) == 0:
            return False
        user_id = random.choice(users).id
        # user to add to the session
        user_to_add = [(4, user_id)]
        if uid:
            user_to_add.append((4, uid))
        # create the session, and add the link with the given channel
        Session = self.pool["im_chat.session"]
        newid = Session.create(cr, SUPERUSER_ID, {'user_ids': user_to_add, 'channel_id': channel_id, 'anonymous_name' : anonymous_name}, context=context)
        return Session.session_info(cr, SUPERUSER_ID, [newid], context=context)

    def test_channel(self, cr, uid, channel, context=None):
        if not channel:
            return {}
        return {
            'url': self.browse(cr, uid, channel[0], context=context or {}).web_page,
            'type': 'ir.actions.act_url'
        }

    def get_info_for_chat_src(self, cr, uid, channel, context=None):
        url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        chan = self.browse(cr, uid, channel, context=context)
        return {
            "url": url,
            'buttonText': chan.button_text,
            'inputPlaceholder': chan.input_placeholder,
            'defaultMessage': chan.default_message,
            "channelName": chan.name,
        }

    def join(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'user_ids': [(4, uid)]})
        return True

    def quit(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'user_ids': [(3, uid)]})
        return True


class im_livechat_channel_rule(osv.Model):
    _name = 'im_livechat.channel.rule'

    _columns = {
        'regex_url' : fields.char('URL Regex', help="Regular expression identifying the web page on which the rules will be applied."),
        'action' : fields.selection([('display_button', 'Display button'),('auto_popup','Auto-popup'), ('hide_button', 'Hide button')], 'Action', size=32, required=True,
                                 help="Select 'Display button' to simply display the chat button on the pages."\
                                 " Select 'Auto-popup' for to display the button, and automatically open the conversation window."\
                                 " Select 'Hide button' to hide the chat button on the pages."),
        'auto_popup_timer' : fields.integer('Auto-popup Timer', help="Delay (in seconds) to automatically open the conversation window. Note: the selected action must be 'Auto-popup', otherwise this parameter will not be taken into account."),
        'channel_id': fields.many2one('im_livechat.channel', 'Channel', help="Channel on which the rules applies"),
        'country_ids': fields.many2many('res.country', 'im_livechat_channel_country_rel', 'channel_id', 'country_id', 'Countries', help="Countries where this rule apply. If you set select 'Belgium' and 'France' and you set the action to 'Hide Button', people from these two countries won't see the support button for the specified URL. (This feature requires GeoIP installed on your server.)"),
        'sequence' : fields.integer('Matching Order', help="Given the order to find a matching rule. If 2 rules are matching for the given url/country, the one with the lowest sequence will be chosen.")
    }

    _defaults = {
        'auto_popup_timer': 0,
        'action' : 'display_button',
        'sequence' : 10,
    }

    _order = "sequence asc"

    def match_rule(self, cr, uid, channel_id, url, country_id=False, context=None):
        """ determine if a rule of the given channel match with the given url """
        def _match(rule_ids):
            for rule in self.browse(cr, uid, rule_ids, context=context):
                if re.search(rule.regex_url, url):
                    return rule
            return False
        # first, search the country specific rules (the first match is returned)
        if country_id: # don't include the country in the research if geoIP is not installed
            domain = [('country_ids', 'in', [country_id]), ('channel_id', '=', channel_id)]
            rule_ids = self.search(cr, uid, domain, context=context)
            rule = _match(rule_ids)
            if rule:
                return rule
        # second, fallback on the rules without country
        domain = [('country_ids', '=', False), ('channel_id', '=', channel_id)]
        rule_ids = self.search(cr, uid, domain, context=context)
        return _match(rule_ids)


class im_chat_session(osv.Model):

    _name = 'im_chat.session'
    _inherit = ['im_chat.session', 'rating.mixin']

    def _get_fullname(self, cr, uid, ids, fields, arg, context=None):
        """ built the complete name of the session """
        result = {}
        sessions = self.browse(cr, uid, ids, context=context)
        for session in sessions:
            names = []
            for user in session.user_ids:
                names.append(user.name)
            if session.anonymous_name:
                names.append(session.anonymous_name)
            result[session.id] = ', '.join(names)
        return result

    _columns = {
        'anonymous_name' : fields.char('Anonymous Name'),
        'create_date': fields.datetime('Create Date', required=True, select=True),
        'channel_id': fields.many2one("im_livechat.channel", "Channel"),
        'fullname' : fields.function(_get_fullname, type="char", string="Complete name"),
    }

    def is_in_session(self, cr, uid, uuid, user_id, context=None):
        """ return if the given user_id is in the session """
        sids = self.search(cr, uid, [('uuid', '=', uuid)], context=context, limit=1)
        for session in self.browse(cr, uid, sids, context=context):
            if session.anonymous_name and user_id == openerp.SUPERUSER_ID:
                return True
            else:
                return super(im_chat_session, self).is_in_session(cr, uid, uuid, user_id, context=context)
        return False

    def users_infos(self, cr, uid, ids, context=None):
        """ add the anonymous user in the user of the session """
        for session in self.browse(cr, uid, ids, context=context):
            users_infos = super(im_chat_session, self).users_infos(cr, uid, ids, context=context)
            if session.anonymous_name:
                users_infos.append({'id' : False, 'name' : session.anonymous_name, 'im_status' : 'online'})
            return users_infos

    def quit_user(self, cr, uid, uuid, context=None):
        """ action of leaving a given session """
        sids = self.search(cr, uid, [('uuid', '=', uuid)], context=context, limit=1)
        for session in self.browse(cr, openerp.SUPERUSER_ID, sids, context=context):
            if session.anonymous_name:
                # an identified user can leave an anonymous session if there is still another idenfied user in it
                if uid and uid in [u.id for u in session.user_ids] and len(session.user_ids) > 1:
                    self.remove_user(cr, uid, session.id, context=context)
                    return True
                return False
            else:
                return super(im_chat_session, self).quit_user(cr, uid, session.id, context=context)


    def cron_remove_empty_session(self, cr, uid, context=None):
        groups = self.pool['im_chat.message'].read_group(cr, uid, [], ['to_id'], ['to_id'], context=context)
        not_empty_session_ids = [group['to_id'][0] for group in groups]
        empty_session_ids = self.search(cr, uid, [('id', 'not in', not_empty_session_ids), ('channel_id', '!=', False)], context=context)
        self.unlink(cr, uid, empty_session_ids, context=context)



class Rating(models.Model):

    _inherit = "rating.rating"

    @api.one
    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        # cannot change the rec_name of session since it is use to create the bus channel
        # so, need to override this method to set the same alternative rec_name as in reporting
        if self.res_model == 'im_chat.session':
            current_object = self.env[self.res_model].sudo().browse(self.res_id)
            self.res_name = ('%s / %s') % (current_object.channel_id.name, current_object.id)
        else:
            super(Rating, self)._compute_res_name()
