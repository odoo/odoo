# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import digest, base_setup, contacts, sales_team, phone_validation, resource, web_tour, calendar, mail


class ResUsers(base_setup.ResUsers, sales_team.ResUsers, mail.ResUsers, calendar.ResUsers, resource.ResUsers, web_tour.ResUsers, contacts.ResUsers, digest.ResUsers, phone_validation.ResUsers):

    target_sales_won = fields.Integer('Won in Opportunities Target')
    target_sales_done = fields.Integer('Activities Done Target')
