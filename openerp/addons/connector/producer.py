# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
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

"""
Producers of events.

Fire the common events:

-  ``on_record_create`` when a record is created
-  ``on_record_write`` when something is written on a record
-  ``on_record_unlink``  when a record is deleted

"""

import openerp
from openerp import models
from .session import ConnectorSession
from .event import (on_record_create,
                    on_record_write,
                    on_record_unlink)
from .connector import is_module_installed


create_original = models.BaseModel.create


@openerp.api.model
@openerp.api.returns('self', lambda value: value.id)
def create(self, vals):
    record_id = create_original(self, vals)
    if is_module_installed(self.env, 'connector'):
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        on_record_create.fire(session, self._name, record_id.id, vals)
    return record_id
models.BaseModel.create = create


write_original = models.BaseModel.write


@openerp.api.multi
def write(self, vals):
    result = write_original(self, vals)
    if is_module_installed(self.env, 'connector'):
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        if on_record_write.has_consumer_for(session, self._name):
            for record_id in self.ids:
                on_record_write.fire(session, self._name,
                                     record_id, vals)
    return result
models.BaseModel.write = write


unlink_original = models.BaseModel.unlink


@openerp.api.multi
def unlink(self):
    if is_module_installed(self.env, 'connector'):
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        if on_record_unlink.has_consumer_for(session, self._name):
            for record_id in self.ids:
                on_record_unlink.fire(session, self._name, record_id)
    return unlink_original(self)
models.BaseModel.unlink = unlink
