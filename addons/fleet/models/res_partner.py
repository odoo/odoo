# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import mail


class ResPartner(mail.ResPartner):

    plan_to_change_car = fields.Boolean('Plan To Change Car', default=False, tracking=True)
    plan_to_change_bike = fields.Boolean('Plan To Change Bike', default=False)
