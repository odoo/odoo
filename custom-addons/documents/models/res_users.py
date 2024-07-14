# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    def _init_messaging(self):
        res = super()._init_messaging()
        res['hasDocumentsUserGroup'] = self.env.user.has_group('documents.group_documents_user')
        return res
