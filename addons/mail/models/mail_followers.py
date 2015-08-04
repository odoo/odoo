# -*- coding: utf-8 -*-

from openerp import _, api, fields, models
from openerp import tools


class Followers(models.Model):
    """ mail_followers holds the data related to the follow mechanism inside
    Odoo. Partners can choose to follow documents (records) of any kind
    that inherits from mail.thread. Following documents allow to receive
    notifications for new messages. A subscription is characterized by:

    :param: res_model: model of the followed objects
    :param: res_id: ID of resource (may be 0 for every objects)
    """
    _name = 'mail.followers'
    _rec_name = 'partner_id'
    _log_access = False
    _description = 'Document Followers'

    res_model = fields.Char(
        'Related Document Model', required=True, select=1, help='Model of the followed resource')
    res_id = fields.Integer(
        'Related Document ID', select=1, help='Id of the followed resource')
    partner_id = fields.Many2one(
        'res.partner', string='Related Partner', ondelete='cascade', required=True, select=1)
    subtype_ids = fields.Many2many(
        'mail.message.subtype', string='Subtype',
        help="Message subtypes followed, meaning subtypes that will be pushed onto the user's Wall.")

    #
    # Modifying followers change access rights to individual documents. As the
    # cache may contain accessible/inaccessible data, one has to refresh it.
    #
    @api.model
    def create(self, vals):
        res = super(Followers, self).create(vals)
        self.invalidate_cache()
        return res

    @api.multi
    def write(self, vals):
        res = super(Followers, self).write(vals)
        self.invalidate_cache()
        return res

    @api.multi
    def unlink(self):
        res = super(Followers, self).unlink()
        self.invalidate_cache()
        return res

    _sql_constraints = [('mail_followers_res_partner_res_model_id_uniq', 'unique(res_model,res_id,partner_id)', 'Error, a partner cannot follow twice the same object.')]


class Notification(models.Model):
    """ Class holding notifications pushed to partners. Followers and partners
    added in 'contacts to notify' receive notifications. """
    _name = 'mail.notification'
    _rec_name = 'partner_id'
    _log_access = False
    _description = 'Notifications'

    partner_id = fields.Many2one('res.partner', string='Contact', ondelete='cascade', required=True, select=1)
    is_read = fields.Boolean('Read', select=1, oldname='read')
    starred = fields.Boolean('Starred', select=1, help='Starred message that goes into the todo mailbox')
    message_id = fields.Many2one('mail.message', string='Message', ondelete='cascade', required=True, select=1)

    def init(self, cr):
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('mail_notification_partner_id_read_starred_message_id',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX mail_notification_partner_id_read_starred_message_id ON mail_notification (partner_id, is_read, starred, message_id)')

    @api.model
    def _notify(self, message, recipients=None, force_send=False, user_signature=True):
        """ Send by email the notification depending on the user preferences

            :param list partners_to_notify: optional list of partner ids restricting
                the notifications to process
            :param bool force_send: if True, the generated mail.mail is
                immediately sent after being created, as if the scheduler
                was executed for this message only.
            :param bool user_signature: if True, the generated mail.mail body is
                the body of the related mail.message with the author's signature
        """
        # mail_notify_noemail (do not send email) or no partner_ids: do not send, return
        if self.env.context.get('mail_notify_noemail'):
            return True
        if not recipients:
            recipients = message.partner_ids

        notifications = self.env['mail.notification'].sudo().search(
            [('message_id', '=', message.id), ('partner_id', 'in', recipients.ids)])
        notifications.write({'is_read': False})
        new_notifications = self.env['mail.notification'].sudo()
        for new_partner in recipients - notifications.mapped('partner_id'):
            new_notifications |= self.env['mail.notification'].sudo().create({
                'message_id': message.id,
                'partner_id': new_partner.id,
                'is_read': False})
        new_recipients = new_notifications.mapped('partner_id')

        # notify
        new_recipients._notify(message, force_send=force_send, user_signature=user_signature)
