import base64

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


SAMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<FacturaElectronica xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica">
    <Clave>50627072600020840085800100001010000000009123456789</Clave>
    <FechaEmision>2026-07-20T08:00:00-06:00</FechaEmision>
    <Emisor>
        <Nombre>Proveedor XML SA</Nombre>
        <Identificacion>
            <Tipo>02</Tipo>
            <Numero>3101999888</Numero>
        </Identificacion>
        <CorreoElectronico>ventas@proveedorxml.cr</CorreoElectronico>
    </Emisor>
    <DetalleServicio>
        <LineaDetalle>
            <NumeroLinea>1</NumeroLinea>
            <CodigoCABYS>0111101000000</CodigoCABYS>
            <Cantidad>10</Cantidad>
            <UnidadMedida>Unid</UnidadMedida>
            <Detalle>Producto con match</Detalle>
            <PrecioUnitario>500</PrecioUnitario>
            <Impuesto>
                <Tarifa>13</Tarifa>
            </Impuesto>
        </LineaDetalle>
        <LineaDetalle>
            <NumeroLinea>2</NumeroLinea>
            <CodigoCABYS>9999999999999</CodigoCABYS>
            <Cantidad>3</Cantidad>
            <UnidadMedida>Unid</UnidadMedida>
            <Detalle>Producto sin match</Detalle>
            <PrecioUnitario>200</PrecioUnitario>
        </LineaDetalle>
    </DetalleServicio>
    <ResumenFactura>
        <TotalImpuesto>650</TotalImpuesto>
        <TotalComprobante>5650</TotalComprobante>
    </ResumenFactura>
</FacturaElectronica>"""


@tagged('post_install', '-at_install')
class TestProveedorUpload(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({
            'name': 'Producto con match', 'l10n_cr_fe_cabys': '0111101000000'})

    def _upload(self, xml_string):
        wizard = self.env['l10n_cr.fe.proveedor.upload'].create({
            'xml_file': base64.b64encode(xml_string.encode('utf-8')),
            'xml_filename': 'factura.xml',
        })
        action = wizard.action_procesar()
        return self.env['account.move'].browse(action['res_id'])

    def test_parses_clave_and_fecha_emision(self):
        invoice = self._upload(SAMPLE_XML)
        self.assertEqual(invoice.l10n_cr_fe_proveedor_clave,
                          '50627072600020840085800100001010000000009123456789')
        self.assertEqual(invoice.l10n_cr_fe_proveedor_fecha_emision, '2026-07-20T08:00:00-06:00')
        self.assertEqual(invoice.move_type, 'in_invoice')

    def test_creates_new_partner_from_emisor(self):
        invoice = self._upload(SAMPLE_XML)
        self.assertEqual(invoice.partner_id.name, 'Proveedor XML SA')
        self.assertEqual(invoice.partner_id.vat, '3101999888')
        self.assertEqual(invoice.partner_id.email, 'ventas@proveedorxml.cr')

    def test_reuses_existing_partner_by_vat(self):
        existing = self.env['res.partner'].create({'name': 'Ya existe', 'vat': '3101999888'})
        invoice = self._upload(SAMPLE_XML)
        self.assertEqual(invoice.partner_id, existing)

    def test_line_with_matching_cabys_links_product(self):
        invoice = self._upload(SAMPLE_XML)
        lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        matched = lines.filtered(lambda l: l.product_id == self.product)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched.quantity, 10)
        self.assertEqual(matched.price_unit, 500)

    def test_line_without_matching_cabys_left_without_product(self):
        invoice = self._upload(SAMPLE_XML)
        lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        unmatched = lines.filtered(lambda l: not l.product_id)
        self.assertEqual(len(unmatched), 1)
        self.assertEqual(unmatched.name, 'Producto sin match')

    def test_parses_totales_autenticos_del_resumen(self):
        invoice = self._upload(SAMPLE_XML)
        self.assertEqual(invoice.l10n_cr_fe_proveedor_monto_impuesto, 650.0)
        self.assertEqual(invoice.l10n_cr_fe_proveedor_total, 5650.0)

    def test_invalid_xml_raises(self):
        with self.assertRaises(UserError):
            self._upload('esto no es xml')
