from odoo.tools import misc
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon


class TestL10nRoEdiStockCommon(ValuationReconciliationTestCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ro')
    def setUpClass(cls):
        super().setUpClass()

        cls.warehouse = cls.company_data['default_warehouse']
        cls.customer_location = cls.env.ref('stock.stock_location_customers').id
        cls.stock_location = cls.warehouse.lot_stock_id.id
        # Disable auto-batching
        cls.warehouse.out_type_id.auto_batch = False
        cls.warehouse.in_type_id.auto_batch = False

    @classmethod
    def create_stock_picking(cls, partner, name=False, location_id=None, location_dest_id=None, picking_type=None, product_data=None):
        picking = cls.env['stock.picking'].create({
            'name': name or f'{cls.env.company.name} picking',
            'partner_id': partner.id,
            'location_id': location_id if location_id else cls.stock_location,
            'location_dest_id': location_dest_id if location_dest_id else cls.customer_location,
            'picking_type_id': picking_type.id if picking_type else cls.warehouse.out_type_id.id,
        })

        for data in product_data or []:
            product = data['product_id']
            cls.env['stock.move'].create({
                'product_id': product.id,
                'uom_id': product.uom_id.id,
                'product_uom_qty': data['product_uom_qty'],
                'quantity': data['quantity'],
                'procure_method': data.get('procure_method', 'make_to_stock'),
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'company_id': cls.env.company.id
            })

        return picking

    def change_product_qty(self, product, new_quantity, product_tmpl=None):
        self.env['stock.change.product.qty'].create({
            'product_id': product.id,
            'product_tmpl_id': product_tmpl.id if product_tmpl else product.product_tmpl_id.id,
            'new_quantity': new_quantity,
        }).change_product_qty()

    def _assert_picking_state(self, picking, state=False, amt_documents=0, enabled_fields=('enable', 'fields_readonly')):
        self.assertEqual(picking.l10n_ro_edi_stock_state, state)
        if amt_documents > 0:
            self.assertTrue(picking.l10n_ro_edi_stock_document_ids)
            self.assertEqual(len(picking.l10n_ro_edi_stock_document_ids), amt_documents)
        else:
            self.assertFalse(picking.l10n_ro_edi_stock_document_ids)

        for suffix in ('enable', 'enable_send', 'enable_fetch', 'enable_amend', 'fields_readonly'):
            field_value = picking[f"l10n_ro_edi_stock_{suffix}"]
            self.assertEqual(field_value, suffix in enabled_fields)

    def _assert_etransport_document(self, document, filename):
        with misc.file_open(f'{self.test_module}/tests/test_files/{filename}.xml', 'rb') as file:
            expected_document = file.read()

        expected_tree = self.get_xml_tree_from_string(expected_document)

        if 'intrastat_code_id' in self.env['product.product']._fields:
            nsmap = expected_tree.nsmap
            nsmap['etr'] = nsmap[None]
            nsmap.pop(None)
            for tag in expected_tree.xpath('//*/etr:bunuriTransportate', namespaces=nsmap):
                tag.attrib['codTarifar'] = self.default_intrastat_code.code

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(document.attachment.content),
            expected_tree,
        )
