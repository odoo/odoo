# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource
from odoo.tools import image_process


class Users(models.Model):
    _inherit = "res.users"

    @api.model
    def _get_default_image(self):
        """ Get a default image when the user is created without image

            Inspired to _get_default_image method in
            https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/res/res_partner.py
        """
        image_path = get_module_resource('base', 'static/img', 'avatar.png')
        image = base64.b64encode(open(image_path, 'rb').read())
        return image_process(image, colorize=True)

    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)
    signature = fields.Html(string="Email Signature", default="")
    action_id = fields.Many2one('ir.actions.actions', string='Home Action',
        help="If specified, this action will be opened at log on for this user, in addition to the standard menu.")
    image_1920 = fields.Image(related='partner_id.image_1920', inherited=True, readonly=False, default=_get_default_image)

    @api.depends('tz')
    def _compute_tz_offset(self):
        for user in self:
            user.tz_offset = datetime.datetime.now(pytz.timezone(user.tz or 'GMT')).strftime('%z')

    @api.constrains('action_id')
    def _check_action_id(self):
        action_open_website = self.env.ref('base.action_open_website', raise_if_not_found=False)
        if action_open_website and any(user.action_id.id == action_open_website.id for user in self):
            raise ValidationError(_('The "App Switcher" action cannot be selected as home action.'))

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        return self.partner_id.onchange_parent_id()

    def read_action_id(self):
        self.ensure_one()
        return self.read(['action_id'])

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights.
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        partner_writable_fields = ['signature', 'action_id', 'image_1920', 'lang']
        partner_readable_fields = ['signature', 'action_id', 'image_1920', 'image_1024', 'image_512', 'image_256', 'image_128', 'tz_offset',]

        init_res = super(Users, self).__init__(pool, cr)
        helpdesk_fields = [
            'helpdesk_target_closed',
            'helpdesk_target_rating',
            'helpdesk_target_success',
        ]
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(partner_writable_fields)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        type(self).SELF_READABLE_FIELDS.extend(partner_readable_fields)
        return init_res
