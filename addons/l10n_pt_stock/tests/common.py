import itertools
from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command
from odoo.tests import freeze_time, new_test_user

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon
from odoo.addons.l10n_pt_stock.models.stock_picking import SAFT_PT_MOVEMENT_TYPE_MAP

STOCK_REPORT = 'stock.action_report_delivery'

# The transport guides (GT) of the AT's demo SAF-T, saft_idemo599999999.xml, one chain: (document number,
# SystemEntryDate, gross total, signature). The AT's sample signs a gross total, which a transfer never has.
AT_SAMPLE_TRANSPORT_DOCUMENTS = [
    ('1G 5A/1', '2017-09-15 15:58:01', 679.61, "fGqopcOBeYlO9s2yVg92WfVZW5S+2UpjLM0w19zt/2ns8YQX1lNGR80XhT89LyP2bc0GZoBWQBXILbKUMtpm6tI8L+DpI+pPbktPAWG3FCy53/b784TNzQEQvklYNV/b6fqeVnoh8eVZ24V/IFuSslIfLKfrys/ymyER9+0tEcY="),
    ('1G 5A/2', '2017-11-30 23:10:23', 679.61, "gtevyKthLaOI53nTrGz91OwpJHv40vYme1/BqL8YXj17K4EziZCkvnZptorl/Jkz571RvLK2tF1QfLLexPqY5WSXaQPGV8WFy7HCPlrg6IOLQuOXIVK6Z1hOAO+LGDC6Efuov6STP39Sd/wYXpclfHGcVA54AvkzDp1UOTyXzsU="),
    ('1G 5A/3', '2017-12-17 08:00:56', 1487.67, "xmVWmhG9fxZOyTGAfX1O+0YaWtLrPh+Z0/EXCiTpmIVuI02MCagrqv30soM8KgDfrpkAGN1WSgJ40LRcfnsHx0ztZx4HfNj8j75UOayI4i1SJVOh6FSb/V3JwwsNh9QIM8/tF0Ba7SKqVavscAezbTNPCoKpbkyJbfICBXR/F0g="),
]

# Each warehouse needs a code of its own.
_warehouse_codes = (f'WH{n}' for n in itertools.count(2))


class TestL10nPtStockCommon(TestL10nPtCommon):
    """
    Base of the ``l10n_pt_stock`` suite.

    A transfer that puts goods in circulation is a transport document (DL 147/2003, the RBC): it is
    issued -- numbered, dated and signed in one step -- when it is validated, before the goods leave
    (RBC art. 6(1)). Its type follows the nature of the movement: a delivery or a move between two of
    the company's warehouses is a transport guide (GT), in the series of its operation type; a return
    to a supplier is a return note (GD), in the returns series of the delivery type; a receipt, a
    customer return and a step inside one warehouse issue nothing.

    ``make_transfer()`` makes a confirmed transfer, ``validate()`` validates it, ``deliver()`` does
    both; time is frozen, so a transfer is validated, dated and signed at the same instant unless the
    test moves the clock.
    """

    @classmethod
    def get_default_groups(cls):
        # The class's own user manages the inventory, as it manages accounting.
        return super().get_default_groups() | cls.quick_ref('stock.group_stock_manager')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # A configured company, whose prints the report action does not divert to the layout configurator.
        cls.company_pt.external_report_layout_id = cls.env.ref('web.external_layout_standard')

        # ==== Users ====
        cls.stock_user = new_test_user(
            cls.env,
            login='pt_stock_user',
            groups='base.group_user,stock.group_stock_user',
            company_id=cls.company_pt.id,
            company_ids=[Command.set((cls.company_pt + cls.branch_pt).ids)],
        )

        # ==== Warehouses and operation types ====
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_pt.id)], limit=1)
        cls.out_type = cls.warehouse.out_type_id
        cls.in_type = cls.warehouse.in_type_id
        cls.int_type = cls.warehouse.int_type_id
        cls.warehouse_2 = cls._create_warehouse('Armazém Porto', '50 Rua de Santa Catarina', 'Porto', '4000-447')
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.shelf_location = cls.env['stock.location'].create({
            'name': 'Prateleira 1',
            'location_id': cls.stock_location.id,
        })
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')

        # ==== Partners and products ====
        cls.partner_supplier = cls.env['res.partner'].create({
            'name': 'Fornecedor PT',
            'street': '5 Rua do Carmo',
            'city': 'Lisboa',
            'zip': '1200-093',
            'country_id': cls.env.ref('base.pt').id,
            'vat': 'PT502011378',
        })
        cls.product_goods = cls.env['product.product'].create({
            'name': 'Caneca',
            'default_code': 'CANECA',
            'type': 'consu',
        })

        # ==== AT series: transport guides (GT) and return notes (GD), for 2026 ====
        cls.series_gt = cls.series_factory(document_type='outgoing')
        cls.series_gd = cls.series_factory(document_type='incoming')
        cls.out_type.write({
            'l10n_pt_stock_at_series_id': cls.series_gt.id,
            'l10n_pt_stock_return_at_series_id': cls.series_gd.id,
        })
        # A move between two warehouses is a GT too, chained with the deliveries.
        cls.int_type.l10n_pt_stock_at_series_id = cls.series_gt

    @classmethod
    def _create_warehouse(cls, name, street, city, zip_code, company=None):
        """A warehouse of ``company`` (``company_pt``) at its own address, without any AT series."""
        company = company or cls.company_pt
        return cls.env['stock.warehouse'].create({
            'name': name,
            'code': next(_warehouse_codes),
            'company_id': company.id,
            'partner_id': cls.env['res.partner'].create({
                'name': name,
                'street': street,
                'city': city,
                'zip': zip_code,
                'country_id': cls.env.ref('base.pt').id,
                'parent_id': company.partner_id.id,
                'type': 'other',
            }).id,
        })

    # -------------------------------------------------------------------------
    # Factories
    # -------------------------------------------------------------------------

    @classmethod
    def series_factory(cls, **overrides):
        """``TestL10nPtCommon.series_factory``; a movement series has the AT code of its type and no journal."""
        if prefix := SAFT_PT_MOVEMENT_TYPE_MAP.get(overrides.get('document_type')):
            overrides = {'prefix': prefix, 'journal_id': False, **overrides}
        return super().series_factory(**overrides)

    @classmethod
    def make_transfer(cls, picking_type=None, lines=None, partner=None, location=None, location_dest=None, user=None, **vals):
        """
        A confirmed transfer of ``picking_type`` (the delivery type), between its default locations, to
        ``partner_pt`` (``partner=False`` for none), made by ``user`` (the class's). ``lines`` are
        ``(product, quantity)``, by default one ``product_goods``.
        """
        picking_type = picking_type or cls.out_type
        partner = cls.partner_pt if partner is None else partner
        location = location or picking_type.default_location_src_id
        location_dest = location_dest or picking_type.default_location_dest_id
        env = cls.env(user=user) if user else cls.env
        picking = env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'partner_id': partner.id if partner else False,
            'location_id': location.id,
            'location_dest_id': location_dest.id,
            'move_ids': [Command.create({
                'company_id': picking_type.company_id.id,
                'product_id': product.id,
                'product_uom_qty': quantity,
                'location_id': location.id,
                'location_dest_id': location_dest.id,
            }) for product, quantity in (lines or [(cls.product_goods, 1)])],
            **vals,
        })
        picking.action_confirm()
        return picking

    @classmethod
    def validate(cls, pickings, quantities=None, backorder=False, user=None):
        """
        Validate ``pickings`` as ``user`` (the class's), as their Validate button does: each move done
        for its whole demand, or for ``quantities[move]``; the rest is left in a backorder if
        ``backorder``, else dropped.
        """
        for move in pickings.move_ids:
            move.quantity = (quantities or {}).get(move, move.product_uom_qty)
        pickings.move_ids.picked = True
        context = {'skip_backorder': True}
        if not backorder:
            context['picking_ids_not_to_backorder'] = pickings.ids
        pickings.with_user(user or cls.env.user).with_context(**context).button_validate()
        return pickings

    @classmethod
    def deliver(cls, picking_type=None, lines=None, partner=None, user=None, **vals):
        """A transfer made and validated by ``user``: see ``make_transfer``."""
        return cls.validate(cls.make_transfer(picking_type, lines, partner, user=user, **vals), user=user)

    @classmethod
    def make_return(cls, picking, quantity=None):
        """The confirmed return of ``quantity`` (all) of each move of ``picking``, by its return wizard."""
        wizard = cls.env['stock.return.picking'].with_context(
            active_id=picking.id,
            active_ids=picking.ids,
            active_model='stock.picking',
        ).create({})
        for line in wizard.product_return_moves:
            line.quantity = line.move_id.quantity if quantity is None else quantity
        return wizard._create_return()

    @classmethod
    def print_pdf(cls, records, report=None):
        return super().print_pdf(records, report or (STOCK_REPORT if records._name == 'stock.picking' else None))

    @classmethod
    def print_pdf_for_real(cls, pickings):
        """
        Print ``pickings`` through the whole PDF path, wkhtmltopdf stubbed. In tests, core short-cuts
        ``_render_qweb_pdf`` to the HTML render before ``_render_qweb_pdf_prepare_streams``, where a
        transport document is checked printable: ``print_pdf`` alone never refuses one.
        """
        with patch.object(cls.registry['ir.actions.report'], '_run_wkhtmltopdf', return_value=b'%PDF-1.4'):
            pickings.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf(STOCK_REPORT, pickings.ids)

    @classmethod
    def preview(cls, records, report=None):
        return super().preview(records, report or (STOCK_REPORT if records._name == 'stock.picking' else None))

    @contextmanager
    def at_sample_transfers(self):
        """
        The transport guides of the AT's demo SAF-T (``AT_SAMPLE_TRANSPORT_DOCUMENTS``), as deliveries of
        a 2017 GT series, each validated at its SystemEntryDate. Yields ``{transfer: signature}``, the
        signature the AT published for each. The AT numbers them ``1G 5A/1`` and signs a gross total,
        the module ``GT 2017/00001`` over 0.00: within the context, what is signed and verified carries
        the AT's number and total; every other value is the module's.
        """
        StockPicking = self.registry['stock.picking']
        get_document_number = StockPicking._l10n_pt_get_document_number
        get_gross_total = StockPicking._l10n_pt_get_gross_total
        at_values, signatures = {}, {}

        def document_number(picking):
            return at_values[picking.id][0] if picking.id in at_values else get_document_number(picking)

        def gross_total(picking):
            return at_values[picking.id][1] if picking.id in at_values else get_gross_total(picking)

        with (
            patch.object(StockPicking, '_l10n_pt_get_document_number', document_number),
            patch.object(StockPicking, '_l10n_pt_get_gross_total', gross_total),
        ):
            series = self.series_factory(name='2017', document_type='outgoing', date_start='2017-01-01', date_end='2017-12-31')
            self.out_type.l10n_pt_stock_at_series_id = series
            for number, system_entry_date, total, signature in AT_SAMPLE_TRANSPORT_DOCUMENTS:
                self.env.invalidate_all()
                with freeze_time(system_entry_date):
                    picking = self.make_transfer()
                    # Known before the transfer is signed, at its validation.
                    at_values[picking.id] = (number, total)
                    self.validate(picking)
                signatures[picking] = signature
            yield signatures
