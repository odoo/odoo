# -*- coding: utf-8 -*-

from openerp import api, models


class MailThread(models.AbstractModel):
    """ Update of mail_mail class, to add the signin URL to notifications. """
    _inherit = 'mail.thread'

    @api.model
    def _get_inbox_action_xml_id(self):
        """ For a given message, return an action that either
            - opens the form view of the related document if model, res_id, and
              read access to the document
            - opens the Inbox with a default search on the conversation if model,
              res_id
            - opens the Inbox with context propagated
        """
        # if uid is a portal user -> action is different
        if any(group.is_portal for group in self.env.user.groups_id):
            return ('portal', 'action_mail_inbox_feeds_portal')
        else:
            return super(MailThread, self)._get_inbox_action_xml_id()
