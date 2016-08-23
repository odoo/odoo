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

from functools import wraps

from openerp.addons.connector.event import (on_record_write,
                                            on_record_create,
                                            on_record_unlink
                                            )
from openerp.addons.connector.connector import Binder
from .unit.delete_synchronizer import export_delete_record
from .connector import get_environment


def delay_export(session, model_name, record_id, fields=None):
    """ Delay a job which export a binding record.

    (A binding record being a ``external.res.partner``,
    ``external.product.product``, ...)
    """
    if session.context.get('connector_no_export'):
        return
    export_record.delay(session, model_name, record_id, fields=fields)


def delay_export_all_bindings(session, model_name, record_id, fields=None):
    """ Delay a job which export all the bindings of a record.

    In this case, it is called on records of normal models and will delay
    the export for all the bindings.
    """
    if session.context.get('connector_no_export'):
        return
    model = session.pool.get(model_name)
    record = model.browse(session.cr, session.uid,
                          record_id, context=session.context)
    for binding in record.prestashop_bind_ids:
        export_record.delay(session, binding._model._name, binding.id,
                            fields=fields)


def delay_unlink(session, model_name, record_id):
    """ Delay a job which delete a record on Prestashop.

    Called on binding records."""
    model = session.pool.get(model_name)
    record = model.browse(session.cr, session.uid,
                          record_id, context=session.context)
    env = get_environment(session, model_name, record.backend_id.id)
    binder = env.get_connector_unit(Binder)
    external_id = binder.to_backend(record_id)
    if external_id:
        export_delete_record.delay(session, model_name,
                                   record.backend_id.id, external_id)


def delay_unlink_all_bindings(session, model_name, record_id):
    """ Delay a job which delete a record on Prestashop.

    Called on binding records."""
    model = session.pool.get(model_name)
    record = model.browse(session.cr, session.uid,
                          record_id, context=session.context)
    for bind_record in record.prestashop_bind_ids:
        prestashop_model_name = bind_record._name
        env = get_environment(session, prestashop_model_name, bind_record.backend_id.id)
        binder = env.get_connector_unit(Binder)
        ext_id = binder.to_backend(bind_record.id)
        if ext_id:
            export_delete_record.delay(session, prestashop_model_name,
                                   bind_record.backend_id.id, ext_id)