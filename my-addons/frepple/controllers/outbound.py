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
import logging
from xml.sax.saxutils import quoteattr
from datetime import datetime, timedelta
from operator import itemgetter

import odoo

logger = logging.getLogger(__name__)


class exporter(object):
    def __init__(self, req, uid, database=None, company=None, mode=1):
        self.database = database
        self.company = company

        # The mode argument defines different types of runs:
        #  - Mode 1:
        #    This mode returns all data that is loaded with every planning run.
        #    Currently this mode transfers all objects, except closed sales orders.
        #  - Mode 2:
        #    This mode returns data that is loaded that changes infrequently and
        #    can be transferred during automated scheduled runs at a quiet moment.
        #    Currently this mode transfers only closed sales orders.
        #
        # Normally an Odoo object should be exported by only a single mode.
        # Exporting a certain object with BOTH modes 1 and 2 will only create extra
        # processing time for the connector without adding any benefits. On the other
        # hand it won't break things either.
        #
        # Which data elements belong to each mode can vary between implementations.
        self.mode = mode

        # Initialize an environment
        self.env = req.env

    def run(self):
        # Check if we manage by work orders or manufacturing orders.
        self.manage_work_orders = False
        m = self.env["ir.model"]
        recs = m.search([("model", "=", "mrp.workorder")])
        for rec in recs:
            self.manage_work_orders = True

        # Load some auxiliary data in memory
        self.load_company()
        self.load_uom()

        # Header.
        # The source attribute is set to 'odoo_<mode>', such that all objects created or
        # updated from the data are also marked as from originating from odoo.
        yield '<?xml version="1.0" encoding="UTF-8" ?>\n'
        yield '<plan xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" source="odoo_%s">\n' % self.mode

        # Main content.
        # The order of the entities is important. First one needs to create the
        # objects before they are referenced by other objects.
        # If multiple types of an entity exists (eg operation_time_per,
        # operation_alternate, operation_alternate, etc) the reference would
        # automatically create an object, potentially of the wrong type.
        if self.mode == 1:
            for i in self.export_calendar():
                yield i
        for i in self.export_locations():
            yield i
        for i in self.export_customers():
            yield i
        if self.mode == 1:
            for i in self.export_suppliers():
                yield i
            for i in self.export_workcenters():
                yield i
        for i in self.export_items():
            yield i
        if self.mode == 1:
            for i in self.export_boms():
                yield i
        for i in self.export_salesorders():
            yield i
        if self.mode == 1:
            for i in self.export_purchaseorders():
                yield i
            for i in self.export_manufacturingorders():
                yield i
            for i in self.export_orderpoints():
                yield i
            for i in self.export_onhand():
                yield i

        # Footer
        yield "</plan>\n"

    def load_company(self):
        m = self.env["res.company"]
        recs = m.search([("name", "=", self.company)])
        fields = [
            "security_lead",
            "po_lead",
            "manufacturing_lead",
            "calendar",
            "manufacturing_warehouse",
        ]
        self.company_id = 0
        for i in recs.read(fields):
            self.company_id = i["id"]
            self.security_lead = int(
                i["security_lead"]
            )  # TODO NOT USED RIGHT NOW - add parameter in frepple for this
            self.po_lead = i["po_lead"]
            self.manufacturing_lead = i["manufacturing_lead"]
            self.calendar = i["calendar"] and i["calendar"][1] or "Working hours"
            self.mfg_location = (
                i["manufacturing_warehouse"]
                and i["manufacturing_warehouse"][1]
                or self.company
            )
        if not self.company_id:
            logger.warning("Can't find company '%s'" % self.company)
            self.company_id = None
            self.security_lead = 0
            self.po_lead = 0
            self.manufacturing_lead = 0
            self.calendar = "Working hours"
            self.mfg_location = self.company

    def load_uom(self):
        """
        Loading units of measures into a dictinary for fast lookups.

        All quantities are sent to frePPLe as numbers, expressed in the default
        unit of measure of the uom dimension.
        """
        m = self.env["uom.uom"]
        # We also need to load INactive UOMs, because there still might be records
        # using the inactive UOM. Questionable practice, but can happen...
        recs = m.search(["|", ("active", "=", 1), ("active", "=", 0)])
        fields = ["factor", "uom_type", "category_id", "name"]
        self.uom = {}
        self.uom_categories = {}
        for i in recs.read(fields):
            if i["uom_type"] == "reference":
                f = 1.0
                self.uom_categories[i["category_id"][0]] = i["id"]
            elif i["uom_type"] == "bigger":
                f = i["factor"]
            else:
                if i["factor"] > 0:
                    f = 1 / i["factor"]
                else:
                    f = 1.0
            self.uom[i["id"]] = {
                "factor": f,
                "category": i["category_id"][0],
                "name": i["name"],
            }

    def convert_qty_uom(self, qty, uom_id, product_id=None):
        """
        Convert a quantity to the reference uom of the product.
        The default implementation doesn't consider the product at all, and just
        converts to the reference unit of the uom category.
        """
        if not uom_id:
            return qty
        return qty * self.uom[uom_id]["factor"]

    def convert_float_time(self, float_time):
        """
        Convert Odoo float time to ISO 8601 duration.
        """
        return "PT%dH%dM%dS" % (
            int(float_time),  # duration: hours
            int((float_time*60) % 60),  # duration: minutes
            int((float_time*3600) % 60 % 60),  # duration: seconds
        )

    def export_calendar(self):
        """
        Build a calendar with a) holidays and b) working hours.

        The holidays are obtained from the hr.holidays.public.line model.
        If the hr module isn't installed, no public holidays will be defined.

        The working hours are extracted from a resource.calendar model.
        The calendar to use is configured with the company parameter "calendar".
        If left unspecified we assume 24*7 working hours.

        The odoo model is not ideal and nice for frePPLe, and the current mapping
        is an as-good-as-it-gets workaround.

        Mapping:
        res.company.calendar  -> calendar.name
        (if no working hours are defined then 1 else 0) -> calendar.default_value

        resource.calendar.attendance.date_from -> calendar_bucket.start
        '1' -> calendar_bucket.value
        resource.calendar.attendance.dayofweek -> calendar_bucket.days
        resource.calendar.attendance.hour_from -> calendar_bucket.startime
        resource.calendar.attendance.hour_to -> calendar_bucket.endtime
        computed -> calendar_bucket.priority

        hr.holidays.public.line.start -> calendar_bucket.start
        hr.holidays.public.line.start + 1 day -> calendar_bucket.end
        '0' -> calendar_bucket.value
        '1' -> calendar_bucket.priority
        """
        yield "<!-- calendar -->\n"
        yield "<calendars>\n"
        try:
            m = self.env["resource.calendar"]
            recs = m.search([("name", "=", self.calendar)])
            rec = recs.read(["attendance_ids"], limit=1)
            fields = ["dayofweek", "date_from", "hour_from", "hour_to"]
            buckets = []
            for i in rec["attendance_ids"].read(fields):
                strt = datetime.strptime(i["date_from"] or "2000-01-01", "%Y-%m-%d")
                buckets.append(
                    (
                        strt,
                        '<bucket start="%sT00:00:00" value="1" days="%s" priority="%%s" starttime="%s" endtime="%s"/>\n'
                        % (
                            strt.strftime("%Y-%m-%d"),
                            2 ** ((int(i["dayofweek"]) + 1) % 7),
                            # In odoo, monday = 0. In frePPLe, sunday = 0.
                            "PT%dM" % round(i["hour_from"] * 60),
                            "PT%dM" % round(i["hour_to"] * 60),
                        ),
                    )
                )
            if len(buckets) > 0:
                # Sort by start date.
                # Required to assure that records with a later start date get a
                # lower priority in frePPLe.
                buckets.sort(key=itemgetter(0))
                priority = 1000
                yield '<calendar name=%s default="0"><buckets>\n' % quoteattr(
                    self.calendar
                )
                for i in buckets:
                    yield i[1] % priority
                    priority -= 1
            else:
                # No entries. We'll assume 24*7 availability.
                yield '<calendar name=%s default="1"><buckets>\n' % quoteattr(
                    self.calendar
                )
        except Exception:
            # Exception happens if the resource module isn't installed.
            yield "<!-- Working hours are assumed to be 24*7. -->\n"
            yield '<calendar name=%s default="1"><buckets>\n' % quoteattr(self.calendar)
        try:
            m = self.env["hr.holidays.public.line"]
            recs = m.search([])
            fields = ["date"]
            for i in recs.read(fields):
                nd = datetime.strptime(i["date"], "%Y-%m-%d") + timedelta(days=1)
                yield '<bucket start="%sT00:00:00" end="%sT00:00:00" value="0" priority="1"/>\n' % (
                    i["date"],
                    nd.strftime("%Y-%m-%d"),
                )
        except Exception:
            # Exception happens if the hr module is not installed
            yield "<!-- No holidays since the HR module is not installed -->\n"
        yield "</buckets></calendar></calendars>\n"

    def export_locations(self):
        """
        Generate a list of warehouse locations to frePPLe, based on the
        stock.warehouse model.

        We assume the location name to be unique. This is NOT guarantueed by Odoo.

        The field subategory is used to store the id of the warehouse. This makes
        it easier for frePPLe to send back planning results directly with an
        odoo location identifier.

        FrePPLe is not interested in the locations odoo defines with a warehouse.
        This methods also populates a map dictionary between these locations and
        warehouse they belong to.

        Mapping:
        stock.warehouse.name -> location.name
        stock.warehouse.id -> location.subcategory
        """
        self.map_locations = {}
        self.warehouses = set()
        childlocs = {}
        m = self.env["stock.warehouse"]
        recs = m.search([])
        if recs:
            yield "<!-- warehouses -->\n"
            yield "<locations>\n"
            fields = [
                "name",
                "wh_input_stock_loc_id",
                "wh_output_stock_loc_id",
                "wh_pack_stock_loc_id",
                "wh_qc_stock_loc_id",
                "view_location_id",
            ]
            for i in recs.read(fields):
                yield '<location name=%s subcategory="%s"><available name=%s/></location>\n' % (
                    quoteattr(i["name"]),
                    i["id"],
                    quoteattr(self.calendar),
                )
                childlocs[i["wh_input_stock_loc_id"][0]] = i["name"]
                childlocs[i["wh_output_stock_loc_id"][0]] = i["name"]
                childlocs[i["wh_pack_stock_loc_id"][0]] = i["name"]
                childlocs[i["wh_qc_stock_loc_id"][0]] = i["name"]
                childlocs[i["view_location_id"][0]] = i["name"]
                self.warehouses.add(i["name"])
            yield "</locations>\n"

            # Populate a mapping location-to-warehouse name for later lookups
            parent_loc = {}
            m = self.env["stock.location"]
            recs = m.search([])
            for i in recs.read(["location_id"]):
                if i["location_id"]:
                    parent_loc[i["id"]] = i["location_id"][0]

            marked = {}

            def fnd_parent(loc_id):  # go up the parent chain to find the warehouse
                if not marked.get(loc_id):  # ensures O(N) iterations instead of O(N^2)
                    if childlocs.get(loc_id):
                        return childlocs[loc_id]
                    if parent_loc.get(loc_id):
                        parent = fnd_parent(parent_loc[loc_id])
                        if parent > 0:
                            return parent
                marked[loc_id] = True
                return -1

            for loc_id in recs:
                parent = fnd_parent(loc_id)
                if parent > 0:
                    self.map_locations[loc_id] = parent

    def export_customers(self):
        """
        Generate a list of customers to frePPLe, based on the res.partner model.
        We filter on res.partner where customer = True.

        Mapping:
        res.partner.id res.partner.name -> customer.name
        """
        self.map_customers = {}
        m = self.env["res.partner"]
        recs = m.search([("is_company", "=", True), ("customer_rank", ">", 0)])
        if recs:
            yield "<!-- customers -->\n"
            yield "<customers>\n"
            fields = ["name"]
            for i in recs.read(fields):
                name = "%d %s" % (i["id"], i["name"])
                yield "<customer name=%s/>\n" % quoteattr(name)
                self.map_customers[i["id"]] = name
            yield "</customers>\n"

    def export_suppliers(self):
        """
        Generate a list of suppliers for frePPLe, based on the res.partner model.
        We filter on res.supplier where supplier = True.

        Mapping:
        res.partner.id res.partner.name -> supplier.name
        """
        m = self.env["res.partner"]
        recs = m.search([("is_company", "=", True), ("supplier_rank", ">", 0)])
        if recs:
            yield "<!-- suppliers -->\n"
            yield "<suppliers>\n"
            fields = ["name"]
            for i in recs.read(fields):
                yield "<supplier name=%s/>\n" % quoteattr(
                    "%d %s" % (i["id"], i["name"])
                )
            yield "</suppliers>\n"

    def export_workcenters(self):
        """
        Send the workcenter list to frePPLe, based one the mrp.workcenter model.

        We assume the workcenter name is unique. Odoo does NOT guarantuee that.

        Mapping:
        mrp.workcenter.name -> resource.name
        mrp.workcenter.costs_hour -> resource.cost
        mrp.workcenter.capacity_per_cycle / mrp.workcenter.time_cycle -> resource.maximum
        company.mfg_location -> resource.location
        """
        self.map_workcenters = {}
        m = self.env["mrp.workcenter"]
        recs = m.search([])
        fields = ["name"]
        if recs:
            yield "<!-- workcenters -->\n"
            yield "<resources>\n"
            for i in recs.read(fields):
                name = i["name"]
                self.map_workcenters[i["id"]] = name
                yield '<resource name=%s maximum="%s"><location name=%s/></resource>\n' % (
                    quoteattr(name),
                    1,
                    quoteattr(self.mfg_location),
                )
            yield "</resources>\n"

    def export_items(self):
        """
        Send the list of products to frePPLe, based on the product.product model.
        For purchased items we also create a procurement buffer in each warehouse.

        Mapping:
        [product.product.code] product.product.name -> item.name
        product.product.product_tmpl_id.list_price -> item.cost
        product.product.id , product.product.product_tmpl_id.uom_id -> item.subcategory

        If product.product.product_tmpl_id.purchase_ok
        and product.product.product_tmpl_id.routes contains the buy route
        we collect the suppliers as product.product.product_tmpl_id.seller_ids
        [product.product.code] product.product.name -> itemsupplier.item
        res.partner.id res.partner.name -> itemsupplier.supplier.name
        supplierinfo.delay -> itemsupplier.leadtime
        supplierinfo.min_qty -> itemsupplier.size_minimum
        supplierinfo.date_start -> itemsupplier.effective_start
        supplierinfo.date_end -> itemsupplier.effective_end
        product.product.product_tmpl_id.delay -> itemsupplier.leadtime
        '1' -> itemsupplier.priority
        """
        # Read the product templates
        self.product_product = {}
        self.product_template_product = {}
        m = self.env["product.template"]
        fields = [
            "purchase_ok",
            # "route_ids", #does not exist anymore in odoo 12
            # "bom_ids",  #does not exist anymore in odoo 12
            "produce_delay",
            "list_price",
            "uom_id",
            # "seller_ids",  #does not exist anymore in odoo 12
            # "standard_price",  #does not exist anymore in odoo 12
        ]
        recs = m.search([])
        self.product_templates = {}
        for i in recs.read(fields):
            self.product_templates[i["id"]] = i

        # Read the stock location routes
        # rts = self.env["stock.location.route"]
        # fields = ["name"]
        # recs = rts.search([])

        # Read the suppliers
        m = self.env["res.partner"]
        recs = m.search(
            [
                ("is_company", "=", True),
                ("supplier_rank", ">", 0),
                ("active", "=", True),
            ]
        )
        supplier_id = {}
        fields = ["id", "name"]
        for i in recs.read(fields):
            supplier_id[i["id"]] = i["name"]

        # Read the products
        m = self.env["product.product"]
        recs = m.search([])
        s = self.env["product.supplierinfo"]
        s_fields = ["name", "delay", "min_qty", "date_end", "date_start", "price"]
        if recs:
            yield "<!-- products -->\n"
            yield "<items>\n"
            fields = ["id", "name", "code", "product_tmpl_id"]  # , "seller_ids"]
            for i in recs.read(fields):
                tmpl = self.product_templates[i["product_tmpl_id"][0]]
                if i["code"]:
                    name = u"[%s] %s" % (i["code"], i["name"])
                else:
                    name = i["name"]
                prod_obj = {"name": name, "template": i["product_tmpl_id"][0]}
                self.product_product[i["id"]] = prod_obj
                self.product_template_product[i["product_tmpl_id"][0]] = prod_obj
                yield '<item name=%s cost="%f" subcategory="%s,%s">\n' % (
                    quoteattr(name),
                    (tmpl["list_price"] or 0)
                    / self.convert_qty_uom(1.0, tmpl["uom_id"][0], i["id"]),
                    self.uom_categories[self.uom[tmpl["uom_id"][0]]["category"]],
                    i["id"],
                )
                # Export suppliers for the item, if the item is allowed to be purchased
                if (
                    tmpl["purchase_ok"]
                    # and buy_route in tmpl["route_ids"]
                    # and tmpl["seller_ids"] seller_ids doesn't exist anymore in odoo 12
                ):
                    yield "<itemsuppliers>\n"
                    for sup in s.search([("product_tmpl_id", "=", tmpl["id"])]).read(
                        s_fields
                    ):
                        name = "%d %s" % (sup["name"][0], sup["name"][1])
                        yield '<itemsupplier leadtime="P%dD" priority="1" size_minimum="%f" cost="%f"%s%s><supplier name=%s/></itemsupplier>\n' % (
                            sup["delay"],
                            sup["min_qty"],
                            sup["price"],
                            ' effective_end="%s"' % sup["date_end"]
                            if sup["date_end"]
                            else "",
                            ' effective_start="%s"' % sup["date_start"]
                            if sup["date_start"]
                            else "",
                            quoteattr(name),
                        )
                    yield "</itemsuppliers>\n"
                yield "</item>\n"
            yield "</items>\n"

    def export_boms(self):
        """
        Exports mrp.routings, mrp.routing.workcenter and mrp.bom records into
        frePPLe operations, flows and loads.

        Not supported yet: a) parent boms, b) phantom boms.
        """
        yield "<!-- bills of material -->\n"
        yield "<operations>\n"
        self.operations = set()

        # Read all active manufacturing routings
        mrp_routings = {}
        # m = self.env["mrp.routing"]
        # recs = m.search([])
        # fields = ["location_id"]
        # for i in recs.read(fields):
        #    mrp_routings[i["id"]] = i["location_id"]

        # Read all workcenters of all routings
        mrp_routing_workcenters = {}
        m = self.env["mrp.routing.workcenter"]
        recs = m.search([], order="routing_id, sequence asc")
        fields = ["name", "routing_id", "workcenter_id", "sequence", "time_cycle"]
        for i in recs.read(fields):
            if i["routing_id"][0] in mrp_routing_workcenters:
                # If the same workcenter is used multiple times in a routing,
                # we add the times together.
                exists = False
                if not self.manage_work_orders:
                    for r in mrp_routing_workcenters[i["routing_id"][0]]:
                        if r[0] == i["workcenter_id"][1]:
                            r[1] += i["time_cycle"]
                            exists = True
                            break
                if not exists:
                    mrp_routing_workcenters[i["routing_id"][0]].append(
                        [
                            i["workcenter_id"][1],
                            i["time_cycle"],
                            i["sequence"],
                            i["name"],
                        ]
                    )
            else:
                mrp_routing_workcenters[i["routing_id"][0]] = [
                    [i["workcenter_id"][1], i["time_cycle"], i["sequence"], i["name"]]
                ]

        # Models used in the bom-loop below
        bom_lines_model = self.env["mrp.bom.line"]
        bom_lines_fields = ["product_qty", "product_uom_id", "product_id", "routing_id"]
        try:
            subproduct_model = self.env["mrp.subproduct"]
            subproduct_fields = [
                "product_id",
                "product_qty",
                "product_uom",
                "subproduct_type",
            ]
        except Exception:
            subproduct_model = None

        # Loop over all bom records
        bom_recs = self.env["mrp.bom"].search([])
        bom_fields = [
            "product_qty",
            "product_uom_id",
            "product_tmpl_id",
            "routing_id",
            "type",
            "bom_line_ids",
        ]
        for i in bom_recs.read(bom_fields):
            # Determine the location
            if i["routing_id"]:
                location = mrp_routings.get(i["routing_id"][0], None)
                if not location:
                    location = self.mfg_location
                else:
                    location = location[1]
            else:
                location = self.mfg_location

            # Determine operation name and item
            product_buf = self.product_template_product.get(
                i["product_tmpl_id"][0], None
            )  # TODO avoid multiple bom on single template
            if not product_buf:
                logger.warn(
                    "skipping %s %s" % (i["product_tmpl_id"][0], i["routing_id"])
                )
                continue
            uom_factor = self.convert_qty_uom(
                1.0, i["product_uom_id"][0], i["product_tmpl_id"][0]
            )
            operation = u"%d %s @ %s" % (i["id"], product_buf["name"], location)
            self.operations.add(operation)

            # Build operation. The operation can either be a summary operation or a detailed
            # routing.
            if (
                not self.manage_work_orders
                or not i["routing_id"]
                or not mrp_routing_workcenters.get(i["routing_id"][0], [])
            ):
                #
                # CASE 1: A single operation used for the BOM
                # All routing steps are collapsed in a single operation.
                #
                yield '<operation name=%s size_multiple="1" duration="%s" posttime="P%dD" xsi:type="operation_fixed_time">\n' "<item name=%s/><location name=%s/>\n" % (
                    quoteattr(operation),
                    self.convert_float_time(
                        self.product_templates[i["product_tmpl_id"][0]]["produce_delay"]
                    ),
                    self.manufacturing_lead,
                    quoteattr(product_buf["name"]),
                    quoteattr(location),
                )
                yield '<flows>\n<flow xsi:type="flow_end" quantity="%f"><item name=%s/></flow>\n' % (
                    i["product_qty"] * uom_factor,
                    quoteattr(product_buf["name"]),
                )

                # Build consuming flows.
                # If the same component is consumed multiple times in the same BOM
                # we sum up all quantities in a single flow. We assume all of them
                # have the same effectivity.
                fl = {}
                for j in bom_lines_model.browse(i["bom_line_ids"]).read(
                    bom_lines_fields
                ):
                    product = self.product_product.get(j["product_id"][0], None)
                    if not product:
                        continue
                    if j["product_id"][0] in fl:
                        fl[j["product_id"][0]].append(j)
                    else:
                        fl[j["product_id"][0]] = [j]
                for j in fl:
                    product = self.product_product[j]
                    qty = sum(
                        self.convert_qty_uom(
                            k["product_qty"], k["product_uom_id"][0], k["product_id"][0]
                        )
                        for k in fl[j]
                    )
                    yield '<flow xsi:type="flow_start" quantity="-%f"><item name=%s/></flow>\n' % (
                        qty,
                        quoteattr(product["name"]),
                    )

                # Build byproduct flows
                if i.get("sub_products", None) and subproduct_model:
                    for j in subproduct_model.browse(i["sub_products"]).read(
                        subproduct_fields
                    ):
                        product = self.product_product.get(j["product_id"][0], None)
                        if not product:
                            continue
                        yield '<flow xsi:type="%s" quantity="%f"><item name=%s/></flow>\n' % (
                            "flow_fixed_end"
                            if j["subproduct_type"] == "fixed"
                            else "flow_end",
                            self.convert_qty_uom(
                                j["product_qty"],
                                j["product_uom"][0],
                                j["product_id"][0],
                            ),
                            quoteattr(product["name"]),
                        )
                yield "</flows>\n"

                # Create loads
                if i["routing_id"]:
                    yield "<loads>\n"
                    for j in mrp_routing_workcenters.get(i["routing_id"][0], []):
                        yield '<load quantity="%f"><resource name=%s/></load>\n' % (
                            j[1],
                            quoteattr(j[0]),
                        )
                    yield "</loads>\n"
            else:
                #
                # CASE 2: A routing operation is created with a suboperation for each
                # routing step.
                #
                yield '<operation name=%s size_multiple="1" posttime="P%dD" xsi:type="operation_routing">' "<item name=%s/><location name=%s/>\n" % (
                    quoteattr(operation),
                    self.manufacturing_lead,
                    quoteattr(product_buf["name"]),
                    quoteattr(location),
                )

                yield "<suboperations>"
                steplist = mrp_routing_workcenters[i["routing_id"][0]]
                # sequence cannot be trusted in odoo12
                counter = 0
                for step in steplist:
                    counter = counter + 1
                    suboperation = step[3]
                    yield "<suboperation>" '<operation name=%s priority="%s" duration="%s" xsi:type="operation_fixed_time">\n' "<location name=%s/>\n" '<loads><load quantity="%f"><resource name=%s/></load></loads>\n' % (
                        quoteattr(
                            "%s - %s - %s" % (operation, suboperation, (counter * 100))
                        ),
                        counter * 10,
                        self.convert_float_time(step[1]),
                        quoteattr(location),
                        1,
                        quoteattr(step[0]),
                    )
                    if step[2] == steplist[-1][2]:
                        # Add producing flows on the last routing step
                        yield '<flows>\n<flow xsi:type="flow_end" quantity="%f"><item name=%s/></flow>\n' % (
                            i["product_qty"]
                            * getattr(i, "product_efficiency", 1.0)
                            * uom_factor,
                            quoteattr(product_buf["name"]),
                        )
                        yield "</flows>\n"
                    if step[2] == steplist[0][2]:
                        # All consuming flows on the first routing step.
                        # If the same component is consumed multiple times in the same BOM
                        # we sum up all quantities in a single flow. We assume all of them
                        # have the same effectivity.
                        fl = {}
                        for j in bom_lines_model.browse(i["bom_line_ids"]).read(
                            bom_lines_fields
                        ):
                            product = self.product_product.get(j["product_id"][0], None)
                            if not product:
                                continue
                            if j["product_id"][0] in fl:
                                fl[j["product_id"][0]].append(j)
                            else:
                                fl[j["product_id"][0]] = [j]
                        yield "<flows>\n"
                        for j in fl:
                            product = self.product_product[j]
                            qty = sum(
                                self.convert_qty_uom(
                                    k["product_qty"],
                                    k["product_uom_id"][0],
                                    k["product_id"][0],
                                )
                                for k in fl[j]
                            )
                            yield '<flow xsi:type="flow_start" quantity="-%f"><item name=%s/></flow>\n' % (
                                qty,
                                quoteattr(product["name"]),
                            )
                        yield "</flows>\n"
                    yield "</operation></suboperation>\n"
                yield "</suboperations>\n"
            yield "</operation>\n"
        yield "</operations>\n"

    def export_salesorders(self):
        """
        Send confirmed sales order lines as demand to frePPLe, using the
        sale.order and sale.order.line models.

        Each order is linked to a warehouse, which is used as the location in
        frePPLe.

        Only orders in the status 'draft' and 'sale' are extracted.

        The picking policy 'complete' is supported at the sales order line
        level only in frePPLe. FrePPLe doesn't allow yet to coordinate the
        delivery of multiple lines in a sales order (except with hacky
        modeling construct).
        The field requested_date is only available when sale_order_dates is
        installed.

        Mapping:
        sale.order.name ' ' sale.order.line.id -> demand.name
        sales.order.requested_date -> demand.due
        '1' -> demand.priority
        [product.product.code] product.product.name -> demand.item
        sale.order.partner_id.name -> demand.customer
        convert sale.order.line.product_uom_qty and sale.order.line.product_uom  -> demand.quantity
        stock.warehouse.name -> demand->location
        (if sale.order.picking_policy = 'one' then same as demand.quantity else 1) -> demand.minshipment
        """
        # Get all sales order lines
        m = self.env["sale.order.line"]
        recs = m.search([])
        fields = [
            "qty_delivered",
            "state",
            "product_id",
            "product_uom_qty",
            "product_uom",
            "order_id",
        ]
        so_line = [i for i in recs.read(fields)]

        # Get all sales orders
        m = self.env["sale.order"]
        ids = [i["order_id"][0] for i in so_line]
        fields = [
            "state",
            "partner_id",
            "commitment_date",
            "date_order",
            "picking_policy",
            "warehouse_id",
        ]
        so = {}
        for i in m.browse(ids).read(fields):
            so[i["id"]] = i

        # Generate the demand records
        yield "<!-- sales order lines -->\n"
        yield "<demands>\n"

        for i in so_line:
            name = u"%s %d" % (i["order_id"][1], i["id"])
            product = self.product_product.get(i["product_id"][0], None)
            j = so[i["order_id"][0]]
            location = j["warehouse_id"][1]
            customer = self.map_customers.get(j["partner_id"][0], None)
            if not customer or not location or not product:
                # Not interested in this sales order...
                continue
            due = j.get("requested_date", False) or j["date_order"]
            priority = 1  # We give all customer orders the same default priority

            # Possible sales order status are 'draft', 'sent', 'sale', 'done' and 'cancel'
            state = j.get("state", "sale")
            if state == "draft":
                status = "quote"
                qty = self.convert_qty_uom(
                    i["product_uom_qty"], i["product_uom"][0], i["product_id"][0]
                )
            elif state == "sale":
                qty = i["product_uom_qty"] - i["qty_delivered"]
                if qty <= 0:
                    status = "closed"
                    qty = self.convert_qty_uom(
                        i["product_uom_qty"], i["product_uom"][0], i["product_id"][0]
                    )
                else:
                    status = "open"
                    qty = self.convert_qty_uom(
                        qty, i["product_uom"][0], i["product_id"][0]
                    )
            elif state in ("done", "sent"):
                status = "closed"
                qty = self.convert_qty_uom(
                    i["product_uom_qty"], i["product_uom"][0], i["product_id"][0]
                )
            elif state == "cancel":
                status = "canceled"
                qty = self.convert_qty_uom(
                    i["product_uom_qty"], i["product_uom"][0], i["product_id"][0]
                )

            #           pick = self.req.session.model('stock.picking')
            #           p_fields = ['move_lines', 'sale_id', 'state']
            #           move = self.req.session.model('stock.move')
            #           m_fields = ['product_id', 'product_uom_qty']
            #           if j['picking_ids']:
            #                 # The code below only works in specific situations.
            #                 # If activated incorrectly it can lead to duplicate demands.
            #                 # Here to export sale order line based that is closed by stock moves.
            #                 # if DO line is done then demand status is closed
            #                 # if DO line is cancel, it will skip the current DO line
            #                 # else demand status is open
            #                 pick_number = 0
            #                 for p in pick.read(j['picking_ids'], p_fields, self.req.session.context):
            #                     p_ids = p['move_lines']
            #                     product_id = i['product_id'][0]
            #                     mv_ids = move.search([('id', 'in', p_ids), ('product_id','=', product_id)], context=self.req.session.context)
            #
            #                     status = ''
            #                     if p['state'] == 'done':
            #                         if self.mode == 1:
            #                           # Closed orders aren't transferred during a small run of mode 1
            #                           continue
            #                         status = 'closed'
            #                     elif p['state'] == 'cancel':
            #                         continue
            #                     else:
            #                         status = 'open'
            #
            #                     for mv in move.read(mv_ids, m_fields, self.req.session.context):
            #                         logger.error("     C sales order line %s  %s " % (i, mv))
            #                         pick_number = pick_number + 1
            #                         name = u'%s %d %d' % (i['order_id'][1], i['id'], pick_number)
            #                         yield '<demand name=%s quantity="%s" due="%s" priority="%s" minshipment="%s" status="%s"><item name=%s/><customer name=%s/><location name=%s/></demand>\n' % (
            #                             quoteattr(name), mv['product_uom_qty'], due.strftime("%Y-%m-%dT%H:%M:%S")
            #                             priority, minship,status, quoteattr(product['name']),
            #                             quoteattr(customer), quoteattr(location)
            #                         )
            yield '<demand name=%s quantity="%s" due="%s" priority="%s" minshipment="%s" status="%s"><item name=%s/><customer name=%s/><location name=%s/></demand>\n' % (
                quoteattr(name),
                qty,
                due.strftime("%Y-%m-%dT%H:%M:%S"),
                priority,
                j["picking_policy"] == "one" and qty or 1.0,
                status,
                quoteattr(product["name"]),
                quoteattr(customer),
                quoteattr(location),
            )

        yield "</demands>\n"

    def export_purchaseorders(self):
        """
        Send all open purchase orders to frePPLe, using the purchase.order and
        purchase.order.line models.

        Only purchase order lines in state 'confirmed' are extracted. The state of the
        purchase order header must be "approved".

        Mapping:
        purchase.order.line.product_id -> operationplan.item
        purchase.order.company.mfg_location -> operationplan.location
        purchase.order.partner_id -> operationplan.supplier
        convert purchase.order.line.product_uom_qty - purchase.order.line.qty_received and purchase.order.line.product_uom -> operationplan.quantity
        purchase.order.date_planned -> operationplan.end
        purchase.order.date_planned -> operationplan.start
        'PO' -> operationplan.ordertype
        'confirmed' -> operationplan.status
        """
        m = self.env["purchase.order.line"]
        recs = m.search(
            [
                "|",
                ("order_id.state", "not in", ("draft", "sent", "bid", "confirmed")),
                ("order_id.state", "=", False),
            ]
        )
        fields = [
            "name",
            "date_planned",
            "product_id",
            "product_qty",
            "qty_received",
            "product_uom",
            "order_id",
        ]
        po_line = [i for i in recs.read(fields)]

        # Get all purchase orders
        m = self.env["purchase.order"]
        ids = [i["order_id"][0] for i in po_line]
        fields = ["name", "company_id", "partner_id", "state", "date_order"]
        po = {}
        for i in m.browse(ids).read(fields):
            po[i["id"]] = i

        # Create purchasing operations
        yield "<!-- open purchase orders -->\n"
        yield "<operationplans>\n"
        for i in po_line:
            if not i["product_id"]:
                continue
            item = self.product_product.get(i["product_id"][0], None)
            j = po[i["order_id"][0]]
            #
            location = self.mfg_location
            if location and item and i["product_qty"] > i["qty_received"]:
                start = j["date_order"].strftime("%Y-%m-%dT%H:%M:%S")
                end = i["date_planned"].strftime("%Y-%m-%dT%H:%M:%S")
                qty = self.convert_qty_uom(
                    i["product_qty"] - i["qty_received"],
                    i["product_uom"][0],
                    i["product_id"][0],
                )
                yield '<operationplan reference=%s ordertype="PO" start="%s" end="%s" quantity="%f" status="confirmed">' "<item name=%s/><location name=%s/><supplier name=%s/>" % (
                    quoteattr(j["name"]),
                    start,
                    end,
                    qty,
                    quoteattr(item["name"]),
                    quoteattr(location),
                    quoteattr("%d %s" % (j["partner_id"][0], j["partner_id"][1])),
                )
                yield "</operationplan>\n"
        yield "</operationplans>\n"

    def export_manufacturingorders(self):
        """
        Extracting work in progress to frePPLe, using the mrp.production model.

        We extract workorders in the states 'in_production' and 'confirmed', and
        which have a bom specified.

        Mapping:
        mrp.production.bom_id mrp.production.bom_id.name @ mrp.production.location_dest_id -> operationplan.operation
        convert mrp.production.product_qty and mrp.production.product_uom -> operationplan.quantity
        mrp.production.date_planned -> operationplan.end
        mrp.production.date_planned -> operationplan.start
        '1' -> operationplan.locked
        """
        yield "<!-- manufacturing orders in progress -->\n"
        yield "<operationplans>\n"
        m = self.env["mrp.production"]
        recs = m.search([("state", "in", ["in_production", "ready", "confirmed"])])
        fields = [
            "bom_id",
            "date_start",
            "date_planned_start",
            "name",
            "state",
            "product_qty",
            "product_uom_id",
            "location_dest_id",
            "product_id",
        ]
        for i in recs.read(fields):
            if i["state"] in ("in_production", "confirmed", "ready") and i["bom_id"]:
                # Open orders
                location = self.map_locations.get(i["location_dest_id"][0], None)
                operation = u"%d %s @ %s" % (i["bom_id"][0], i["bom_id"][1], location)
                startdate = i["date_start"] or i["date_planned_start"] or None
                if not startdate:
                    continue
                if not location or operation not in self.operations:
                    continue
                qty = self.convert_qty_uom(
                    i["product_qty"], i["product_uom_id"][0], i["product_id"][0]
                )
                yield '<operationplan reference=%s start="%s" end="%s" quantity="%s" locked="true"><operation name=%s/></operationplan>\n' % (
                    quoteattr(i["name"]),
                    startdate,
                    startdate,
                    qty,
                    quoteattr(operation),
                )
        yield "</operationplans>\n"

    def export_orderpoints(self):
        """
        Defining order points for frePPLe, based on the stock.warehouse.orderpoint
        model.

        Mapping:
        stock.warehouse.orderpoint.product.name ' @ ' stock.warehouse.orderpoint.location_id.name -> buffer.name
        stock.warehouse.orderpoint.location_id.name -> buffer.location
        stock.warehouse.orderpoint.product.name -> buffer.item
        convert stock.warehouse.orderpoint.product_min_qty -> buffer.mininventory
        convert stock.warehouse.orderpoint.product_max_qty -> buffer.maxinventory
        convert stock.warehouse.orderpoint.qty_multiple -> buffer->size_multiple
        """
        m = self.env["stock.warehouse.orderpoint"]
        recs = m.search([])
        fields = [
            "warehouse_id",
            "product_id",
            "product_min_qty",
            "product_max_qty",
            "product_uom",
            "qty_multiple",
        ]
        if recs:
            yield "<!-- order points -->\n"
            yield "<buffers>\n"
            for i in recs.read(fields):
                item = self.product_product.get(
                    i["product_id"] and i["product_id"][0] or 0, None
                )
                if not item:
                    continue
                uom_factor = self.convert_qty_uom(
                    1.0, i["product_uom"][0], i["product_id"][0]
                )
                name = u"%s @ %s" % (item["name"], i["warehouse_id"][1])
                yield "<buffer name=%s><item name=%s/><location name=%s/>\n" '%s%s%s<booleanproperty name="ip_flag" value="true"/>\n' '<stringproperty name="roq_type" value="quantity"/>\n<stringproperty name="ss_type" value="quantity"/>\n' "</buffer>\n" % (
                    quoteattr(name),
                    quoteattr(item["name"]),
                    quoteattr(i["warehouse_id"][1]),
                    '<doubleproperty name="ss_min_qty" value="%s"/>\n'
                    % (i["product_min_qty"] * uom_factor)
                    if i["product_min_qty"]
                    else "",
                    '<doubleproperty name="roq_min_qty" value="%s"/>\n'
                    % ((i["product_max_qty"] - i["product_min_qty"]) * uom_factor)
                    if (i["product_max_qty"] - i["product_min_qty"])
                    else "",
                    '<doubleproperty name="roq_multiple_qty" value="%s"/>\n'
                    % (i["qty_multiple"] * uom_factor)
                    if i["qty_multiple"]
                    else "",
                )
            yield "</buffers>\n"

    def export_onhand(self):
        """
        Extracting all on hand inventories to frePPLe.

        We're bypassing the ORM for performance reasons.

        Mapping:
        stock.report.prodlots.product_id.name @ stock.report.prodlots.location_id.name -> buffer.name
        stock.report.prodlots.product_id.name -> buffer.item
        stock.report.prodlots.location_id.name -> buffer.location
        sum(stock.report.prodlots.qty) -> buffer.onhand
        """
        yield "<!-- inventory -->\n"
        yield "<buffers>\n"
        self.env.cr.execute(
            "SELECT product_id, location_id, sum(quantity) "
            "FROM stock_quant "
            "WHERE quantity > 0 "
            "GROUP BY product_id, location_id "
            "ORDER BY location_id ASC"
            
        )
        inventory = {}
        for i in self.env.cr.fetchall():
            item = self.product_product.get(i[0], None)
            location = self.map_locations.get(i[1], None)
            if item and location:
                inventory[(item["name"], location)] = i[2] + inventory.get(
                    (item["name"], location), 0
                )
        for key, val in inventory.items():
            buf = "%s @ %s" % (key[0], key[1])
            yield '<buffer name=%s onhand="%f"><item name=%s/><location name=%s/></buffer>\n' % (
                quoteattr(buf),
                val,
                quoteattr(key[0]),
                quoteattr(key[1]),
            )
        yield "</buffers>\n"
