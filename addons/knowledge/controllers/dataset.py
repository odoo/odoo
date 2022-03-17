# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.exceptions import UserError

from odoo.addons.web.controllers.main import DataSet


class KnowledgeDataSet(DataSet):

    @http.route('/web/dataset/resequence', type='json', auth="user")
    def resequence(self, model, ids, field='sequence', offset=0):
        """ Re-sequence cannot be used for knowledge article model as there might be a lot of articles and we don't want
        to write on every article when reordering them. Instead, the sequence of knowledge articles works only among
        children of same parent. So when reordering an article, only the children of the target parent are reordered.
        This reordering of article is handled by a custom mechanism and the handle widget should not be used here.
        """
        if model == "knowledge.article":
            raise UserError("You cannot reorder articles using the handle widget.")
        return super().resequence(model, ids, field, offset)
