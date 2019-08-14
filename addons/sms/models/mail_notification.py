# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _


class Notification(models.Model):
    _inherit = 'mail.notification'

    notification_type = fields.Selection(selection_add=[('sms', 'SMS')])
    sms_id = fields.Many2one('sms.sms', string='SMS', index=True, ondelete='set null')
    sms_number = fields.Char('SMS Number')
    failure_type = fields.Selection(selection_add=[
        ('sms_number_missing', 'Missing Number'),
        ('sms_number_format', 'Wrong Number Format'),
        ('sms_credit', 'Insufficient Credit'),
        ('sms_server', 'Server Error')]
    )
    # Though this is an interesting case:
    # On sms.resend.recipient, partner_id depends on mail.notification.partner_id as it is defined as a related
    # fields.Many2one('res.partner', 'Partner', related='notification_id.res_partner_id', readonly=True)
    # The below is to add an inverse to the many2one sms.resend.recipient.notification_id
    # so it maintains a list of sms.resend.recipient.partner_id to invalidate
    # when modifying the partner_id of mail.notification. Otherwise the ORM has to do a plain search to find the sms.resend.recipient
    # which have as notification id the one that has been modified
    # Though:
    #  - We already discussed the matter it would rather be more interesting to do this automatically for these cases,
    #    with a kind of virtual one2many the developer/user doesn't know about,
    #    so the developer doesnt have to create it himself for this technical/performance reason
    #  - In this case, the modified happens on the creation of the mail.notification, and has it has just been created it
    #    would be quite safe to assume there was no `sms.resend.recipient` and we could have avoided the search,
    #    even without this virtual/technical one2many.
    #  - Besides, its a wizard, and we also discussed the possibility to stop the modified when going from a regular model to a transient model
    #    meaning when we update something on the record on which is based the wizard
    #    e.g. a related to the invoice name, something like that,
    #    we let the modified do its change when we specifically change the invoice on the wizard, but not when changing the name on the invoice
    sms_resend_recipient_ids = fields.One2many('sms.resend.recipient', 'notification_id', strong='SMS recipients to resend')
