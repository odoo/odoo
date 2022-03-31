# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging


from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResUsersDeletion(models.Model):
    """User deletion requests.

    Those requests are logged in a different model to keep a trace of this action and the
    deletion is done in a CRON. Indeed, removing a user can be a heavy operation on
    large database (because of create_uid, write_uid on each model, which are not always
    indexed). This model just remove the users added in the deletion queue, remaining code
    must deal with other consideration (archiving, blacklist email...).
    """

    _name = 'res.users.deletion'
    _description = 'Users Deletion Request'
    _rec_name = 'user_id'

    # Integer field because the related user might be deleted from the database
    user_id = fields.Many2one('res.users', string='User', ondelete='set null')
    user_id_int = fields.Integer('User Id', compute='_compute_user_id_int', store=True)
    state = fields.Selection([('todo', 'To Do'), ('done', 'Done'), ('fail', 'Failed')],
                             string='State', required=True, default='todo')

    @api.depends('user_id')
    def _compute_user_id_int(self):
        for user_deletion in self:
            if user_deletion.user_id:
                user_deletion.user_id_int = user_deletion.user_id.id

    @api.autovacuum
    def _gc_portal_users(self):
        """Remove the portal users that asked to deactivate their account.

        (see <res.users>::_deactivate_portal_user)

        Removing a user can be an heavy operation on large database (because of
        create_uid, write_uid on each models, which are not always indexed). Because of
        that, this operation is done in a CRON.
        """
        delete_requests = self.search([('state', '=', 'todo')])

        # filter the requests related to a deleted user
        done_requests = delete_requests.filtered(lambda request: not request.user_id)
        done_requests.state = 'done'

        for delete_request in (delete_requests - done_requests):
            user = delete_request.user_id
            user_name = user.name
            try:
                with self.env.cr.savepoint():
                    partner = user.partner_id
                    user.unlink()
                    partner.unlink()
                    _logger.info('User #%i %r, deleted. Original request from %r.',
                                 user.id, user_name, delete_request.create_uid.name)
                    delete_request.state = 'done'
            except Exception:
                delete_request.state = 'fail'
