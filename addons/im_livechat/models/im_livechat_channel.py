# -*- coding: utf-8 -*-
import json
import openerp
import random
import re
from datetime import datetime, timedelta

from openerp import api, fields, models
from openerp import tools


class ImLivechatChannel(models.Model):
    """ Livechat Channel
        Define a communication channel, which can be accessed with 'script_external' (script tag to put on
        external website), 'script_internal' (code to be integrated with odoo website) or via 'web_page' link.
        It provides rating tools, and access rules for anonymous people.
    """

    _name = 'im_livechat.channel'
    _description = 'Livechat Channel'

    def _default_image(self):
        image_path = openerp.modules.get_module_resource('im_livechat', 'static/src/img', 'default.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    def _default_user_ids(self):
        return [(6, 0, [self._uid])]

    # attribute fields
    name = fields.Char('Name', required=True, help="The name of the channel")
    button_text = fields.Char('Text of the Button', default='Have a Question? Chat with us.',
        help="Default text displayed on the Livechat Support Button")
    default_message = fields.Char('Welcome Message', default='How may I help you?',
        help="This is an automated 'welcome' message that your visitor will see when they initiate a new conversation.")
    input_placeholder = fields.Char('Chat Input Placeholder')

    # computed fields
    web_page = fields.Char('Web Page', compute='_compute_web_page_link', store=False, readonly=True,
        help="URL to a static page where you client can discuss with the operator of the channel.")
    are_you_inside = fields.Boolean(string='Are you inside the matrix?',
        compute='_are_you_inside', store=False, readonly=True)
    script_external = fields.Text('Script (external)', compute='_compute_script_external', store=False, readonly=True)
    nbr_channel = fields.Integer('Number of conversation', compute='_compute_nbr_channel', store=False, readonly=True)
    rating_percentage_satisfaction = fields.Integer(
        '% Happy', compute='_compute_percentage_satisfaction', store=False, default=-1,
        help="Percentage of happy ratings over the past 7 days")

    # images fields
    image = fields.Binary('Image', default=_default_image, attachment=True,
        help="This field holds the image used as photo for the group, limited to 1024x1024px.")
    image_medium = fields.Binary('Medium',
        compute='_compute_image', store=True, attachment=True,
        help="Medium-sized photo of the group. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary('Thumbnail',
        compute='_compute_image', store=True, attachment=True,
        help="Small-sized photo of the group. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

    # relationnal fields
    user_ids = fields.Many2many('res.users', 'im_livechat_channel_im_user', 'channel_id', 'user_id', string='Operators', default=_default_user_ids)
    channel_ids = fields.One2many('mail.channel', 'livechat_channel_id', 'Sessions')
    rule_ids = fields.One2many('im_livechat.channel.rule', 'channel_id', 'Rules')


    @api.one
    def _are_you_inside(self):
        self.are_you_inside = bool(self.env.uid in [u.id for u in self.user_ids])

    @api.one
    @api.depends('image')
    def _compute_image(self):
        self.image_medium = tools.image_resize_image_medium(self.image)
        self.image_small = tools.image_resize_image_small(self.image)

    @api.multi
    def _compute_script_external(self):
        view = self.env['ir.model.data'].get_object('im_livechat', 'external_loader')
        values = {
            "url": self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            "dbname": self._cr.dbname,
        }
        for record in self:
            values["channel_id"] = record.id
            record.script_external = view.render(values)

    @api.multi
    def _compute_web_page_link(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.web_page = "%s/im_livechat/support/%i" % (base_url, record.id)

    @api.multi
    @api.depends('channel_ids')
    def _compute_nbr_channel(self):
        for record in self:
            record.nbr_channel = len(record.channel_ids)

    @api.multi
    @api.depends('channel_ids.rating_ids')
    def _compute_percentage_satisfaction(self):
        for record in self:
            dt = fields.Datetime.to_string(datetime.utcnow() - timedelta(days=7))
            repartition = record.channel_ids.rating_get_grades([('create_date', '>=', dt)])
            total = sum(repartition.values())
            if total > 0:
                happy = repartition['great']
                record.rating_percentage_satisfaction = ((happy*100) / total) if happy > 0 else 0
            else:
                record.rating_percentage_satisfaction = -1

    # --------------------------
    # Action Methods
    # --------------------------
    @api.multi
    def action_join(self):
        self.ensure_one()
        return self.write({'user_ids': [(4, self._uid)]})

    @api.multi
    def action_quit(self):
        self.ensure_one()
        return self.write({'user_ids': [(3, self._uid)]})

    @api.multi
    def action_view_rating(self):
        """ Action to display the rating relative to the channel, so all rating of the
            sessions of the current channel
            :returns : the ir.action 'action_view_rating' with the correct domain
        """
        self.ensure_one()
        action = self.env['ir.actions.act_window'].for_xml_id('rating', 'action_view_rating')
        action['domain'] = [('res_id', 'in', [s.id for s in self.channel_ids]), ('res_model', '=', 'mail.channel')]
        return action

    # --------------------------
    # Channel Methods
    # --------------------------
    @api.multi
    def get_available_users(self):
        """ get available user of a given channel
            :retuns : return the res.users having their im_status online
        """
        self.ensure_one()
        return self.sudo().user_ids.filtered(lambda user: user.im_status == 'online')

    @api.model
    def get_mail_channel(self, livechat_channel_id, anonymous_name):
        """ Return a mail.channel given a livechat channel. It creates one with a connected operator, or return false otherwise
            :param livechat_channel_id : the identifier if the im_livechat.channel
            :param anonymous_name : the name of the anonymous person of the channel
            :type livechat_channel_id : int
            :type anonymous_name : str
            :return : channel header
            :rtype : dict
        """
        # get the avalable user of the channel
        users = self.sudo().browse(livechat_channel_id).get_available_users()
        if len(users) == 0:
            return False
        # choose the res.users operator and get its partner id
        user = random.choice(users)
        operator_partner_id = user.partner_id.id
        # partner to add to the mail.channel
        channel_partner_to_add = [(4, operator_partner_id)]
        if self.env.uid:  # if the user if logged (portal user), he can be identify
            channel_partner_to_add.append((4, self.env.user.partner_id.id))
        # create the session, and add the link with the given channel
        mail_channel = self.env["mail.channel"].with_context(mail_create_nosubscribe=False).sudo().create({
            'channel_partner_ids': channel_partner_to_add,
            'livechat_channel_id': livechat_channel_id,
            'anonymous_name': anonymous_name,
            'channel_type': 'livechat',
            'name': ', '.join([anonymous_name, user.name]),
            'public': 'public',
            'email_send': False,
        })
        # minimize channel on operator's side
        mail_channel._minimize([operator_partner_id])
        return mail_channel.sudo().with_context(im_livechat_operator_partner_id=operator_partner_id).channel_info()[0]

    @api.model
    def get_channel_infos(self, channel_id):
        channel = self.browse(channel_id)
        return {
            'button_text': channel.button_text,
            'input_placeholder': channel.input_placeholder,
            'default_message': channel.default_message,
            "channel_name": channel.name,
            "channel_id": channel.id,
        }

    @api.model
    def get_livechat_info(self, channel_id, username='Visitor'):
        info = {}
        info['available'] = len(self.browse(channel_id).get_available_users())
        if info['available']:
            info['server_url'] = self.env['ir.config_parameter'].get_param('web.base.url')
            info['options'] = self.sudo().get_channel_infos(channel_id)
            info['options']["default_username"] = username
        return info


class ImLivechatChannelRule(models.Model):
    """ Channel Rules
        Rules defining access to the channel (countries, and url matching). It also provide the 'auto pop'
        option to open automatically the conversation.
    """

    _name = 'im_livechat.channel.rule'
    _description = 'Channel Rules'
    _order = 'sequence asc'


    regex_url = fields.Char('URL Regex',
        help="Regular expression identifying the web page on which the rules will be applied.")
    action = fields.Selection([('display_button', 'Display the button'), ('auto_popup', 'Auto popup'), ('hide_button', 'Hide the button')],
        string='Action', required=True, default='display_button',
        help="* Select 'Display the button' to simply display the chat button on the pages.\n"\
             "* Select 'Auto popup' for to display the button, and automatically open the conversation window.\n"\
             "* Select 'Hide the button' to hide the chat button on the pages.")
    auto_popup_timer = fields.Integer('Auto popup timer', default=0,
        help="Delay (in seconds) to automatically open the converssation window. Note : the selected action must be 'Auto popup', otherwise this parameter will not be take into account.")
    channel_id = fields.Many2one('im_livechat.channel', 'Channel',
        help="The channel of the rule")
    country_ids = fields.Many2many('res.country', 'im_livechat_channel_country_rel', 'channel_id', 'country_id', 'Country',
        help="The actual rule will match only for this country. So if you set select 'Belgium' and 'France' and you set the action to 'Hide Buttun', this 2 country will not be see the support button for the specified URL. This feature requires GeoIP installed on your server.")
    sequence = fields.Integer('Matching order', default=10,
        help="Given the order to find a matching rule. If 2 rules are matching for the given url/country, the one with the lowest sequence will be chosen.")

    def match_rule(self, channel_id, url, country_id=False):
        """ determine if a rule of the given channel match with the given url
            :param channel_id : the identifier of the channel_id
            :param url : the url to match with a rule
            :param country_id : the identifier of the country
            :returns the rule that match the given condition. False otherwise.
            :rtype : im_livechat.channel.rule
        """
        def _match(rules):
            for rule in rules:
                if re.search(rule.regex_url, url):
                    return rule
            return False
        # first, search the country specific rules (the first match is returned)
        if country_id: # don't include the country in the research if geoIP is not installed
            domain = [('country_ids', 'in', [country_id]), ('channel_id', '=', channel_id)]
            rule = _match(self.search(domain))
            if rule:
                return rule
        # second, fallback on the rules without country
        domain = [('country_ids', '=', False), ('channel_id', '=', channel_id)]
        return _match(self.search(domain))
