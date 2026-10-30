from datetime import datetime

from odoo import fields
from psycopg2.errors import UniqueViolation

from odoo.exceptions import RedirectWarning, UserError
from odoo.tests import freeze_time, new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_pt_stock.tests.common import TestL10nPtStockCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtStockTransfer(TestL10nPtStockCommon):
    """
    The life of a transfer as a transport document: which movement is one, and of which type (Portaria
    302/2016 4.2.3.8; RBC art. 6(1)); its issue at validation, numbered, dated and signed in one step,
    so that number, date and chain orders agree (Despacho 8632/2014 1.6, 2.1.5); and, once issued,
    nothing it states can change (RBC art. 4(2); Despacho 8632/2014 1.11) nor disappear (DL 28/2019
    art. 7(4)-(5)): corrections go through a return (D-16).
    """

    # -------------------------------------------------------------------------
    # Document types
    # -------------------------------------------------------------------------

    def test_document_type_by_movement(self):
        """
        A delivery and a move between two warehouses are GT, in the delivery and internal types' series;
        a return to a supplier is a GD, in the delivery type's returns series; a receipt, a customer
        return and a step inside one warehouse issue nothing (PT-49, D-5, D-19).
        """
        delivery = self.deliver()
        customer_return = self.validate(self.make_return(delivery))
        receipt = self.deliver(self.in_type, partner=self.partner_supplier)
        supplier_return = self.validate(self.make_return(receipt))
        internal_step = self.deliver(self.int_type, partner=False, location_dest=self.shelf_location)
        between_warehouses = self.deliver(self.int_type, partner=False, location_dest=self.warehouse_2.lot_stock_id)

        self.assertEqual(supplier_return.picking_type_id, self.out_type)
        for picking, document_type, number in (
            (delivery, 'outgoing', 'GT 2026/00001'),
            (customer_return, False, False),
            (receipt, False, False),
            (supplier_return, 'incoming', 'GD 2026/00001'),
            (internal_step, False, False),
            (between_warehouses, 'outgoing', 'GT 2026/00002'),
        ):
            with self.subTest(picking=picking.name):
                self.assertEqual(picking.state, 'done')
                self.assertEqual(picking.l10n_pt_document_type, document_type)
                self.assertEqual(picking.l10n_pt_document_number, number)
                if number:
                    self.assertIssued(picking)
                    self.assertEqual(picking._l10n_pt_get_saft_doc_type(), number[:2])
                else:
                    self.assertNotIssued(picking)
                    self.assertFalse(picking.l10n_pt_at_series_id)
        self.assertEqual(supplier_return.l10n_pt_at_series_id, self.series_gd)
        self.assertEqual((delivery + between_warehouses).l10n_pt_at_series_id, self.series_gt)

    def test_document_type_follows_draft_changes(self):
        """Until it is issued, a transfer's type follows its locations: a step becomes a GT once it leaves the warehouse."""
        picking = self.make_transfer(self.int_type, partner=False, location_dest=self.shelf_location)
        self.assertFalse(picking.l10n_pt_document_type)
        picking.location_dest_id = self.warehouse_2.lot_stock_id
        self.assertEqual(picking.l10n_pt_document_type, 'outgoing')
        self.validate(picking)
        self.assertEqual(picking.l10n_pt_document_number, 'GT 2026/00001')

    def test_non_pt_company(self):
        """A transfer of a non-PT company is no PT document: no type, number, signature or start of transport."""
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_foreign.id)], limit=1)
        picking = self.deliver(warehouse.out_type_id.with_company(self.company_foreign))
        self.assertEqual(picking.state, 'done')
        self.assertFalse(picking.l10n_pt_document_type)
        self.assertNotIssued(picking)
        self.assertFalse(picking.l10n_pt_start_transport_date)
        self.assertFalse(self.signing.calls['sign_records'])

    # -------------------------------------------------------------------------
    # Operation types
    # -------------------------------------------------------------------------

    def test_operation_type_series_rules(self):
        """
        Deliveries and moves between warehouses issue GT, receipts nothing; only a delivery type takes
        a returns series, a GD one; a series serves one operation type of each kind (PT-49).
        """
        # Each refusal is rolled back, as its request would be, so that the next change starts clean.
        for description, change, exception, message in (
            ("GT series on a receipt type",
             lambda: self.in_type.write({'l10n_pt_stock_at_series_id': self.series_factory(document_type='outgoing', name='2026R').id}),
             RedirectWarning, "cannot be used by this Operation Type"),
            ("GD series as a delivery type's main series",
             lambda: self.out_type.write({'l10n_pt_stock_at_series_id': self.series_gd.id}),
             RedirectWarning, "cannot be used by this Operation Type"),
            ("returns series on an internal type",
             lambda: self.int_type.write({'l10n_pt_stock_return_at_series_id': self.series_factory(document_type='incoming', name='2026I').id}),
             UserError, "Only a delivery operation type takes a series for returns"),
            ("GT series as returns series",
             lambda: self.out_type.write({'l10n_pt_stock_return_at_series_id': self.series_gt.id}),
             UserError, "Only a delivery operation type takes a series for returns"),
            ("GT series on a second delivery type",
             lambda: self.warehouse_2.out_type_id.write({'l10n_pt_stock_at_series_id': self.series_gt.id}),
             UniqueViolation, "stock_picking_type_at_series_code_unique"),
            ("GD series on a second delivery type",
             lambda: self.warehouse_2.out_type_id.write({'l10n_pt_stock_return_at_series_id': self.series_gd.id}),
             UniqueViolation, "stock_picking_type_return_at_series_unique"),
        ):
            with (
                self.subTest(change=description),
                self.assertRaisesRegex(exception, message),
                mute_logger('odoo.sql_db'),
                self.env.cr.savepoint(),
            ):
                change()
                self.env.flush_all()
        # The delivery and internal types of the class share their GT series, one chain.
        self.assertEqual(self.int_type.l10n_pt_stock_at_series_id, self.out_type.l10n_pt_stock_at_series_id)

    def test_stock_administrator_sets_series(self):
        """An inventory administrator without accounting rights gives an operation type its series (PT-141)."""
        stock_manager = new_test_user(
            self.env,
            login='pt_stock_manager',
            groups='base.group_user,stock.group_stock_manager',
            company_id=self.company_pt.id,
        )
        delivery_type = self.warehouse_2.out_type_id.with_user(stock_manager)
        series = self.series_factory(document_type='outgoing', name='2026P')
        self.env.invalidate_all()
        delivery_type.l10n_pt_stock_at_series_id = series
        with self.assertRaisesRegex(RedirectWarning, "cannot be used by this Operation Type"), self.env.cr.savepoint():
            delivery_type.l10n_pt_stock_at_series_id = self.series_gd
        # As the operation type's form reads it, from a cold cache.
        self.env.invalidate_all()
        [values] = delivery_type.web_read({'l10n_pt_stock_at_series_id': {'fields': {'display_name': {}}}})
        self.assertEqual(values['l10n_pt_stock_at_series_id'], {'id': series.id, 'display_name': 'GT 2026P'})

    def test_missing_series_warning(self):
        """
        A transfer to be issued in a series its operation type lacks says so on its form; validated, it
        is done without being issued.
        """
        other_delivery_type = self.warehouse_2.out_type_id
        without_series = self.make_transfer(other_delivery_type)
        self.assertTrue(without_series.l10n_pt_show_no_at_series_warning)
        self.assertFalse(self.make_transfer().l10n_pt_show_no_at_series_warning)
        self.assertFalse(self.make_transfer(self.in_type, partner=self.partner_supplier).l10n_pt_show_no_at_series_warning)
        self.out_type.l10n_pt_stock_return_at_series_id = False
        receipt = self.deliver(self.in_type, partner=self.partner_supplier)
        self.assertTrue(self.make_return(receipt).l10n_pt_show_no_at_series_warning)

        self.validate(without_series)
        self.assertEqual(without_series.state, 'done')
        self.assertNotIssued(without_series)
        self.assertFalse(without_series.l10n_pt_start_transport_date)

    # -------------------------------------------------------------------------
    # Issuing
    # -------------------------------------------------------------------------

    def test_validation_issues(self):
        """
        Validating a delivery issues it, as the user who validates it: its number, ATCUD, issuer and
        time, its signature, in one call to the signing service, and its start of transport (PT-66).
        """
        picking = self.make_transfer()
        self.assertNotIssued(picking)
        self.validate(picking)
        self.assertIssued(picking)
        self.assertEqual(picking.l10n_pt_document_number, 'GT 2026/00001')
        self.assertEqual(picking.l10n_pt_atcud, f'{self.series_gt.at_code}-1')
        self.assertEqual(picking.l10n_pt_issue_user_id, self.env.user)
        now = fields.Datetime.now()
        self.assertEqual(picking.date_done, now)
        self.assertEqual(picking.l10n_pt_issued_on, now)
        self.assertEqual(picking.l10n_pt_hashed_on, now)
        self.assertEqual(picking.l10n_pt_start_transport_date, now)
        self.assertEqual(self.signing.calls['sign_records'], 1)
        self.assertSignatureValid(picking)
        self.assertIn("successfully signed", picking.message_ids[0].body)

    def test_stock_user_issues(self):
        """A stock user without accounting rights validates, and so issues, a delivery and a supplier return (PT-141)."""
        receipt = self.deliver(self.in_type, partner=self.partner_supplier, user=self.stock_user)
        delivery = self.deliver(user=self.stock_user)
        supplier_return = self.validate(self.make_return(receipt), user=self.stock_user)
        self.assertIssued(delivery + supplier_return)
        self.assertEqual((delivery + supplier_return).l10n_pt_issue_user_id, self.stock_user)
        self.assertEqual(delivery.l10n_pt_document_number, 'GT 2026/00001')
        self.assertEqual(supplier_return.l10n_pt_document_number, 'GD 2026/00001')
        self.assertChainVerified(delivery + supplier_return)

    def test_numbered_in_validation_order(self):
        """Transfers confirmed A then B and validated B then A are numbered B /1, A /2, in one valid chain (PT-25)."""
        first_confirmed = self.make_transfer()
        second_confirmed = self.make_transfer()
        with freeze_time('2026-06-15 11:00:00'):
            self.validate(second_confirmed)
        with freeze_time('2026-06-15 12:00:00'):
            self.validate(first_confirmed)
        self.assertEqual(second_confirmed.l10n_pt_document_number, 'GT 2026/00001')
        self.assertEqual(first_confirmed.l10n_pt_document_number, 'GT 2026/00002')
        self.assertEqual(self._previous_signed(first_confirmed), second_confirmed)
        self.assertChainVerified(first_confirmed + second_confirmed)

    def test_cancelled_before_validation(self):
        """
        A transfer cancelled before validation was never issued: no number, nothing to sign, and the
        integrity check runs over it (PT-3).
        """
        cancelled = self.make_transfer()
        cancelled.action_cancel()
        self.assertEqual(cancelled.state, 'cancel')
        self.assertNotIssued(cancelled)
        picking = self.deliver()
        self.assertEqual(picking.l10n_pt_document_number, 'GT 2026/00001')
        self.assertChainVerified(picking)

    def test_backorder(self):
        """
        A partial validation issues what leaves, its quantity frozen; the backorder is issued when it
        is validated in turn.
        """
        picking = self.make_transfer(lines=[(self.product_goods, 10)])
        self.validate(picking, quantities={picking.move_ids: 4}, backorder=True)
        backorder = picking.backorder_ids
        self.assertEqual(picking.l10n_pt_document_number, 'GT 2026/00001')
        self.assertEqual(picking.move_ids.quantity, 4)
        self.assertEqual(backorder.move_ids.product_uom_qty, 6)
        self.assertNotIssued(backorder)
        with freeze_time('2026-06-16 10:00:00'):
            self.validate(backorder)
        self.assertEqual(backorder.l10n_pt_document_number, 'GT 2026/00002')
        self.assertChainVerified(picking + backorder)

    def test_series_kept_when_operation_type_changes(self):
        """
        A transfer keeps the series it was issued in when its operation type is given another one; the
        new series starts at /1 over an empty previous signature (PT-31).
        """
        before = self.deliver()
        new_series = self.series_factory(document_type='outgoing', name='2026B')
        self.out_type.l10n_pt_stock_at_series_id = new_series
        after = self.deliver()
        self.assertEqual(before.l10n_pt_at_series_id, self.series_gt)
        self.assertEqual(before.l10n_pt_document_number, 'GT 2026/00001')
        self.assertEqual(after.l10n_pt_at_series_id, new_series)
        self.assertEqual(after.l10n_pt_document_number, 'GT 2026B/00001')
        self.assertEqual(self.signing.payloads[-1]['previous_signature'], '')
        self.assertChainVerified(before + after)

        self.out_type.l10n_pt_stock_at_series_id = False
        unissued = self.deliver()
        self.assertNotIssued(unissued)
        self.assertEqual(before.l10n_pt_at_series_id, self.series_gt)

    def test_series_validity(self):
        """
        A series that has ended, has not started, or has no AT validation code refuses the validation,
        and no number is consumed (Portaria 195/2020; PT-22).
        """
        for name, vals, message in (
            ('2026E', {'date_end': '2026-06-14'}, "An inactive series cannot be used"),
            ('2026F', {'date_start': '2026-06-16'}, "An inactive series cannot be used"),
            ('2026N', {'at_code': False}, "has no AT validation code"),
        ):
            with self.subTest(vals=vals):
                series = self.series_factory(document_type='outgoing', name=name, **vals)
                self.out_type.l10n_pt_stock_at_series_id = series
                picking = self.make_transfer()
                with self.assertRaisesRegex((UserError, RedirectWarning), message), self.env.cr.savepoint():
                    self.validate(picking)
                self.assertNotEqual(picking.state, 'done')
                self.assertNotIssued(picking)
                self.assertEqual(series._l10n_pt_get_document_number_sequence().number_next_actual, 1)

    def test_start_of_transport(self):
        """
        The transport starts when the document is issued, at validation, unless a later start was entered;
        an earlier one is moved to the validation time (RBC art. 4(2); PT-47).
        """
        now = fields.Datetime.now()
        later = datetime(2026, 6, 16, 8, 0)
        for start, expected in ((False, now), (later, later), (datetime(2026, 6, 14, 8, 0), now)):
            with self.subTest(start=start):
                picking = self.make_transfer(l10n_pt_start_transport_date=start)
                self.validate(picking)
                self.assertEqual(picking.l10n_pt_start_transport_date, expected)

    def test_issued_in_its_own_company(self):
        """A transfer validated while another company is active is issued in its own company's series (PT-56)."""
        picking = self.make_transfer()
        picking = picking.with_context(allowed_company_ids=(self.company_foreign + self.company_pt).ids)
        self.validate(picking)
        self.assertEqual(picking.l10n_pt_document_number, 'GT 2026/00001')
        self.assertChainVerified(picking)

    # -------------------------------------------------------------------------
    # Once issued
    # -------------------------------------------------------------------------

    def test_issued_transfer_locked(self):
        """
        Once issued, a transfer cannot be unlocked, nor its partner, places, start of transport,
        operation type or company changed, nor its goods and quantities, nor scrapped from: a return
        corrects it (PT-33).
        """
        picking = self.deliver()
        move = picking.move_ids
        other_partner = self.partner_foreign
        for description, change in (
            ("unlock", lambda: picking.action_toggle_is_locked()),
            ("partner", lambda: picking.write({'partner_id': other_partner.id})),
            ("source", lambda: picking.write({'location_id': self.shelf_location.id})),
            ("destination", lambda: picking.write({'location_dest_id': self.warehouse_2.lot_stock_id.id})),
            ("start of transport", lambda: picking.write({'l10n_pt_start_transport_date': datetime(2026, 6, 20)})),
            ("operation type", lambda: picking.write({'picking_type_id': self.warehouse_2.out_type_id.id})),
            ("demand", lambda: move.write({'product_uom_qty': 2})),
            ("quantity", lambda: move.write({'quantity': 2})),
            ("product", lambda: move.write({'product_id': self.product_a.id})),
            ("move line quantity", lambda: move.move_line_ids.write({'quantity': 2})),
            ("new move", lambda: self.env['stock.move'].create({
                'product_id': self.product_goods.id,
                'product_uom_qty': 1,
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
            })),
            ("scrap", lambda: self.env['stock.scrap'].create({
                'product_id': self.product_goods.id,
                'scrap_qty': 1,
                'picking_id': picking.id,
            }).action_validate()),
        ):
            with (
                self.subTest(change=description),
                self.assertRaisesRegex(UserError, "was issued as a transport document"),
                self.env.cr.savepoint(),
            ):
                change()
        # Rewriting a value it holds, or a field it does not state, changes nothing it was issued with.
        picking.write({'partner_id': self.partner_pt.id, 'note': 'Entregar de manhã'})
        self.assertEqual(picking.note, '<p>Entregar de manhã</p>')
        self.assertEqual(self.make_return(picking).state, 'assigned')

    def test_issued_transfer_not_deleted(self):
        """
        An issued transfer cannot be deleted: a validated one is refused by core already, one numbered
        at confirmation then cancelled, as before PT-25, by the PT guard; an unissued one can be deleted
        (PT-32, PT-61).
        """
        picking = self.deliver()
        with self.assertRaisesRegex(UserError, "Create a return"), self.env.cr.savepoint():
            picking.unlink()
        cancelled = self.make_transfer()
        cancelled.action_cancel()
        self.tamper(cancelled, 'l10n_pt_document_number', 'GT 2026/00002')
        with self.assertRaisesRegex(UserError, r"Documents issued in Portugal cannot be deleted \(GT 2026/00002\)"), self.env.cr.savepoint():
            cancelled.unlink()
        self.assertTrue((picking + cancelled).exists())
        unissued = self.make_transfer()
        unissued.action_cancel()
        unissued.unlink()
        self.assertFalse(unissued.exists())

    def test_series_of_issued_transfer_frozen(self):
        """
        A series in which a transfer was issued cannot be renamed, re-coded, re-dated, moved to another
        company or deleted; it can be ended from its last document's date on. An unused one is free
        (PT-42, PT-62, PT-63).
        """
        self.deliver()
        for vals in (
            {'name': '2026X'},
            {'prefix': 'GR'},
            {'date_start': '2026-02-01'},
            {'company_id': self.company_pt_2.id},
        ):
            with self.subTest(vals=vals), self.assertRaisesRegex(UserError, "cannot change the properties"):
                self.series_gt.write(vals)
        with self.assertRaisesRegex(UserError, "cannot change the AT Validation Code"):
            self.series_gt.at_code = 'ATOTHER01'
        with self.assertRaisesRegex(UserError, "cannot end before its last document"):
            self.series_gt.date_end = '2026-06-14'
        with self.assertRaisesRegex(UserError, "cannot delete a series"):
            self.series_gt.unlink()
        self.series_gt.date_end = '2026-06-15'
        self.assertEqual(self.series_gt.date_end, fields.Date.to_date('2026-06-15'))

        self.series_gd.write({'name': '2026X', 'at_code': 'ATOTHER02'})
        self.series_gd.unlink()
        self.assertFalse(self.out_type.l10n_pt_stock_return_at_series_id)

    # -------------------------------------------------------------------------
    # Master data
    # -------------------------------------------------------------------------

    def test_customer_nif_locked_by_issued_transfer(self):
        """
        A customer's NIF can be given while missing or generic, then no longer changed once a transport
        document was issued to it or to one of its contacts (Despacho 8632/2014 3.3.3; PT-41); a
        transfer not yet validated locks nothing.
        """
        customer = self.env['res.partner'].create({'name': 'Cliente Novo', 'is_company': True, 'country_id': self.env.ref('base.pt').id})
        contact = self.env['res.partner'].create({'name': 'Armazém do Cliente', 'type': 'delivery', 'parent_id': customer.id})
        self.make_transfer(partner=contact)
        customer.vat = 'PT123456789'
        customer.vat = '999999990'
        self.deliver(partner=contact)
        customer.vat = 'PT501964843'
        with self.assertRaisesRegex(UserError, "partner that already has issued documents"):
            customer.vat = 'PT502011378'

    def test_product_name_locked_by_issued_transfer(self):
        """
        A product's name cannot change once it travelled under an issued transport document; a
        transfer not validated, or a receipt, locks nothing, and a user without inventory rights still
        renames other products (Despacho 8632/2014 3.3.5; PT-48, PT-124).
        """
        product = self.product_goods
        self.make_transfer()
        self.deliver(self.in_type, partner=self.partner_supplier)
        product.name = 'Caneca Azul'
        self.deliver()
        with self.assertRaisesRegex(UserError, "used in a transfer in Portugal"):
            product.name = 'Caneca Verde'
        product_manager = new_test_user(self.env, login='pt_product_manager', groups='base.group_user,product.group_product_manager')
        with self.assertRaisesRegex(UserError, "used in a transfer in Portugal"):
            product.with_user(product_manager).name = 'Caneca Verde'
        self.product_b.with_user(product_manager).name = 'Produto B'
        self.assertEqual(self.product_b.name, 'Produto B')
