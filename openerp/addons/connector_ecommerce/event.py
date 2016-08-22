# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Joel Grand-Guillaume
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

from openerp.addons.connector.event import Event


on_picking_out_done = Event()
"""
``on_picking_out_done`` is fired when an outgoing picking has been
marked as done.

Listeners should take the following arguments:

 * session: `connector.session.ConnectorSession` object
 * model_name: name of the model
 * record_id: id of the record
 * type: 'partial' or 'complete' depending on the picking done
"""


on_tracking_number_added = Event()
"""
``on_tracking_number_added`` is fired when a picking has been marked as
 done and a tracking number has been added to it (write).

Listeners should take the following arguments:

 * session: `connector.session.ConnectorSession` object
 * model_name: name of the model
 * record_id: id of the record
"""


on_invoice_paid = Event()
"""
``on_invoice_paid`` is fired when an invoice has been paid.

Listeners should take the following arguments:

 * session: `connector.session.ConnectorSession` object
 * model_name: name of the model
 * record_id: id of the record
"""

on_invoice_validated = Event()
"""
``on_invoice_validated`` is fired when an invoice has been validated.

Listeners should take the following arguments:

 * session: `connector.session.ConnectorSession` object
 * model_name: name of the model
 * record_id: id of the record
"""

on_product_price_changed = Event()
"""
``on_product_price_changed`` is fired when the price of a product is
changed. Specifically, it is fired when one of the products' fields used
in the sale pricelists are modified.

There is no guarantee that's the price actually changed,
because it depends on the pricelists.

 * session: `connector.session.ConnectorSession` object
 * model_name: name of the model
 * record_id: id of the record

"""
