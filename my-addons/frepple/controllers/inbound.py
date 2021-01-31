# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 by frePPLe bvba
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import odoo
import logging
from xml.etree.cElementTree import iterparse
from datetime import datetime

logger = logging.getLogger(__name__)


class importer(object):
    def __init__(self, req, database=None, company=None, mode=1):
        self.env = req.env
        self.database = database
        self.company = company
        self.datafile = req.httprequest.files.get("frePPLe plan")

        # The mode argument defines different types of runs:
        #  - Mode 1:
        #    Export of the complete plan. This first erase all previous frePPLe
        #    proposals in draft state.
        #  - Mode 2:
        #    Incremental export of some proposed transactions from frePPLe.
        #    In this mode mode we are not erasing any previous proposals.
        self.mode = mode

    def run(self):
        msg = []

        proc_order = self.env["purchase.order"]
        proc_orderline = self.env["purchase.order.line"]
        mfg_order = self.env["mrp.production"]
        if self.mode == 1:
            # Cancel previous draft purchase quotations
            m = self.env["purchase.order"]
            recs = m.search([("state", "=", "draft"), ("origin", "=", "frePPLe")])
            recs.write({"state": "cancel"})
            recs.unlink()
            msg.append("Removed %s old draft purchase orders" % len(recs))

            # Cancel previous draft manufacturing orders
            recs = mfg_order.search(
                [
                    "|",
                    ("state", "=", "draft"),
                    ("state", "=", "cancel"),
                    ("origin", "=", "frePPLe"),
                ]
            )
            recs.write({"state": "cancel"})
            recs.unlink()
            msg.append("Removed %s old draft manufacturing orders" % len(recs))

        # Parsing the XML data file
        countproc = 0
        countmfg = 0

        # dictionary that stores as key the supplier id and the associated po id
        # this dict is used to aggregate the exported POs for a same supplier
        # into one PO in odoo with multiple lines
        supplier_reference = {}

        # dictionary that stores as key a tuple (product id, supplier id)
        # and as value a poline odoo object
        # this dict is used to aggregate POs for the same product supplier
        # into one PO with sum of quantities and min date
        product_supplier_dict = {}

        for event, elem in iterparse(self.datafile, events=("start", "end")):
            if event == "end" and elem.tag == "operationplan":
                uom_id, item_id = elem.get("item_id").split(",")
                try:
                    ordertype = elem.get("ordertype")
                    if ordertype == "PO":
                        # Create purchase order
                        supplier_id = int(elem.get("supplier").split(" ", 1)[0])
                        if supplier_id not in supplier_reference:
                            po = proc_order.create(
                                {
                                    "company_id": self.company.id,
                                    "partner_id": int(
                                        elem.get("supplier").split(" ", 1)[0]
                                    ),
                                    # TODO Odoo has no place to store the location and criticality
                                    # int(elem.get('location_id')),
                                    # elem.get('criticality'),
                                    "origin": "frePPLe",
                                }
                            )
                            supplier_reference[supplier_id] = po.id

                        quantity = elem.get("quantity")
                        date_planned = elem.get("end")
                        if (item_id, supplier_id) not in product_supplier_dict:
                            po_line = proc_orderline.create(
                                {
                                    "order_id": supplier_reference[supplier_id],
                                    "product_id": int(item_id),
                                    "product_qty": quantity,
                                    "product_uom": int(uom_id),
                                    "date_planned": date_planned,
                                    "price_unit": 0,
                                    "name": elem.get("item"),
                                }
                            )
                            product_supplier_dict[(item_id, supplier_id)] = po_line

                        else:
                            po_line = product_supplier_dict[(item_id, supplier_id)]
                            po_line.date_planned = min(
                                po_line.date_planned,
                                datetime.strptime(date_planned, "%Y-%m-%d %H:%M:%S"),
                            )
                            po_line.product_qty = po_line.product_qty + float(quantity)
                        countproc += 1
                    # TODO Create a distribution order
                    # elif ????:
                    else:
                        # Create manufacturing order
                        mfg_order.create(
                            {
                                "product_qty": elem.get("quantity"),
                                "date_planned_start": elem.get("start"),
                                "date_planned_finished": elem.get("end"),
                                "product_id": int(item_id),
                                "company_id": self.company.id,
                                "product_uom_id": int(uom_id),
                                "location_src_id": int(elem.get("location_id")),
                                "bom_id": int(elem.get("operation").split(" ", 1)[0]),
                                # TODO no place to store the criticality
                                # elem.get('criticality'),
                                "origin": "frePPLe",
                            }
                        )
                        countmfg += 1
                except Exception as e:
                    logger.error("Exception %s" % e)
                    msg.append(str(e))
                # Remove the element now to keep the DOM tree small
                root.clear()
            elif event == "start" and elem.tag == "operationplans":
                # Remember the root element
                root = elem

        # Be polite, and reply to the post
        msg.append("Processed %s uploaded procurement orders" % countproc)
        msg.append("Processed %s uploaded manufacturing orders" % countmfg)
        return "\n".join(msg)
