# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ..exceptions import except_orm
from ..models import Model, TransientModel, AbstractModel

# Deprecated, kept for backward compatibility.
# openerp.exceptions.Warning should be used instead.
except_osv = except_orm

# Deprecated, kept for backward compatibility.
osv = Model
osv_memory = TransientModel
osv_abstract = AbstractModel # ;-)
