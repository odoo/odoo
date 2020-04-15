# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ..exceptions import UserError
from ..models import Model, TransientModel, AbstractModel

# Deprecated, kept for backward compatibility.
except_osv = UserError

# Deprecated, kept for backward compatibility.
osv = Model
osv_memory = TransientModel
osv_abstract = AbstractModel # ;-)
