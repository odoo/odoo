# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from ..models.calendar import get_real_ids


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model
    def search(self, args, offset=0, limit=0, order=None, count=False):
        '''
        convert the search on real ids in the case it was asked on virtual ids, then call super()
        '''
        for index in range(len(args)):
            if args[index][0] == "res_id":
                if isinstance(args[index][2], basestring):
                    args[index][2] = get_real_ids(args[index][2])
                elif isinstance(args[index][2], list):
                    args[index] = (args[index][0], args[index][1], map(lambda x: get_real_ids(x), args[index][2]))
        return super(MailMessage, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def _find_allowed_model_wise(self, doc_model, doc_dict):
        if doc_model == 'calendar.event':
            order = self.env.context.get('order', self._order)
            for virtual in self.env[doc_model].browse(doc_dict.keys()).get_recurrent_ids([], order=order):
                doc_dict.setdefault(virtual.id, doc_dict[get_real_ids(virtual.id)])
        return super(MailMessage, self)._find_allowed_model_wise(doc_model, doc_dict)
