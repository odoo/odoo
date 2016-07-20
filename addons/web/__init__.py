# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import sys

# Mock deprecated openerp.addons.web.http module
import openerp.http
sys.modules['openerp.addons.web.http'] = openerp.http
http = openerp.http

import controllers
import models
