
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import pdb
import openerp
import addons
import openerp.addons.product.product

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

import netsvc
from osv import fields, osv
import tools
from tools.translate import _
from decimal import Decimal
import decimal_precision as dp

_logger = logging.getLogger(__name__)

class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
            'dont_vidange': fields.float('Dont Vidange', help="Le prix de ce produit inclus ce montant de vidange"),
            'extra':        fields.char('Information Supplémentaire', help="Permet de stocker des informations supplémentaires sur le produit",size=256),
    }
    _defaults = {
            'dont_vidange': 0.0,
    }

