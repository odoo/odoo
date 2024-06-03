# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression


class MessageAbstract(models.AbstractModel):
    _name = 'message.abstract'

    @api.model
    def _message_fetch(self, domain, search_term=None, before=None, after=None, around=None, limit=30):
        res = {}
        if search_term:
            # we replace every space by a % to avoid hard spacing matching
            search_term = search_term.replace(" ", "%")
            domain = expression.AND([domain, expression.OR([
                # sudo: access to attachment is allowed if you have access to the parent model
                [("attachment_ids", "in", self.env["ir.attachment"].sudo()._search([("name", "ilike", search_term)]))],
                [("body", "ilike", search_term)],
                [("subject", "ilike", search_term)],
                [("subtype_id.description", "ilike", search_term)],
            ])])
            domain = expression.AND([domain, [("message_type", "not in", ["user_notification", "notification"])]])
            res["count"] = self.search_count(domain)
        if around:
            messages_before = self.search(domain=[*domain, ('id', '<=', around)], limit=limit // 2, order="id DESC")
            messages_after = self.search(domain=[*domain, ('id', '>', around)], limit=limit // 2, order='id ASC')
            return {**res, "messages": (messages_after + messages_before).sorted('id', reverse=True)}
        if before:
            domain = expression.AND([domain, [('id', '<', before)]])
        if after:
            domain = expression.AND([domain, [('id', '>', after)]])
        res["messages"] = self.search(domain, limit=limit, order='id ASC' if after else 'id DESC')
        if after:
            res["messages"] = res["messages"].sorted('id', reverse=True)
        return res
