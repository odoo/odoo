# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from ..models.calendar import calendar_id2real_id


class IrValues(models.Model):
    _inherit = 'ir.values'

    @api.model
    def set(self, key, key2, name, models, value, replace=True, isobject=False, meta=False, preserve_user=False, company=False):
        new_models = []
        for data in models:
            if type(data) in (list, tuple):
                new_models.append((data[0], calendar_id2real_id(data[1])))
            else:
                new_models.append(data)
        return super(IrValues, self).set(key, key2, name, new_models, value, replace, isobject, meta, preserve_user, company)

    @api.model
    def get(self, key, key2, models, meta=False, res_id_req=False, without_user=True, key2_req=True):
        new_models = []
        for data in models:
            if type(data) in (list, tuple):
                new_models.append((data[0], calendar_id2real_id(data[1])))
            else:
                new_models.append(data)
        return super(IrValues, self).get(key, key2, new_models, meta, res_id_req, without_user, key2_req)
