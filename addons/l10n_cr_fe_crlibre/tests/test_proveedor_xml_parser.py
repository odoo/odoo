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
        <TotalVentaNeta>5600</TotalVentaNeta>
        <TotalImpuesto>650</TotalImpuesto>
        <TotalComprobante>6250</TotalComprobante>
    </ResumenFactura>
</FacturaElectronica>"""


@tagged('post_install', '-at_install')
class TestProveedorXmlParser(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({
            'name': 'Producto con match', 'l10n_cr_fe_cabys': '0111101000000'})

    def _parse(self, xml_string):
        return self.env['account.move']._l10n_cr_fe_build_vals_from_proveedor_xml(
            xml_string.encode('utf-8'))

    def test_returns_clave_fecha_y_totales(self):
        vals = self._parse(SAMPLE_XML)
        self.assertEqual(vals['move_type'], 'in_invoice')
        self.assertEqual(vals['l10n_cr_fe_proveedor_clave'],
                          '50627072600020840085800100001010000000009123456789')
        self.assertEqual(vals['l10n_cr_fe_proveedor_fecha_emision'], '2026-07-20T08:00:00-06:00')
        self.assertEqual(vals['invoice_date'], '2026-07-20')
        self.assertEqual(vals['l10n_cr_fe_proveedor_monto_impuesto'], 650.0)
        self.assertEqual(vals['l10n_cr_fe_proveedor_total'], 6250.0)
        self.assertEqual(vals['l10n_cr_fe_proveedor_subtotal'], 5600.0)

    def test_resuelve_partner_por_cedula_del_emisor(self):
        vals = self._parse(SAMPLE_XML)
        partner = self.env['res.partner'].browse(vals['partner_id'])
        self.assertEqual(partner.name, 'Proveedor XML SA')
        self.assertEqual(partner.vat, '3101999888')

    def test_arma_dos_lineas_una_con_producto_y_otra_sin(self):
        vals = self._parse(SAMPLE_XML)
        self.assertEqual(len(vals['invoice_line_ids']), 2)
        primera = vals['invoice_line_ids'][0][2]
        segunda = vals['invoice_line_ids'][1][2]
        self.assertEqual(primera['product_id'], self.product.id)
        self.assertEqual(primera['quantity'], 10)
        self.assertFalse(segunda['product_id'])

    def test_xml_invalido_levanta_user_error(self):
        with self.assertRaises(UserError):
            self._parse('esto no es xml')

    def test_xml_sin_clave_ni_emisor_levanta_user_error(self):
        with self.assertRaises(UserError):
            self._parse('<FacturaElectronica></FacturaElectronica>')
