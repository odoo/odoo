# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from odoo.addons.calendar.models.calendar import get_real_ids


class Attachment(models.Model):

    _inherit = "ir.attachment"

    @api.model
    def search(self, args, offset=0, limit=0, order=None, count=False):
        """ Convert the search on real ids in the case it was asked on virtual ids, then call super() """
        args = list(args)
        if any([leaf for leaf in args if leaf[0] == "res_model" and leaf[2] == 'calendar.event']):
            for index in range(len(args)):
                if args[index][0] == "res_id" and isinstance(args[index][2], basestring):
                    args[index] = (args[index][0], args[index][1], get_real_ids(args[index][2]))
        return super(Attachment, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.multi
    def write(self, vals):
        """ When posting an attachment (new or not), convert the virtual ids in real ids. """
        if isinstance(vals.get('res_id'), basestring):
            vals['res_id'] = get_real_ids(vals.get('res_id'))
        return super(Attachment, self).write(vals)
