import base64

from odoo.tests.common import TransactionCase, tagged


SAMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<FacturaElectronica xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica">
    <Clave>50627072600020840085800100001010000000009123456789</Clave>
    <FechaEmision>2026-07-20T08:00:00-06:00</FechaEmision>
    <Emisor>
        <Nombre>Proveedor XML SA</Nombre>
        <Identificacion><Tipo>02</Tipo><Numero>3101999888</Numero></Identificacion>
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
        </LineaDetalle>
    </DetalleServicio>
    <ResumenFactura>
        <TotalVentaNeta>5000</TotalVentaNeta>
        <TotalImpuesto>0</TotalImpuesto>
        <TotalComprobante>5000</TotalComprobante>
    </ResumenFactura>
</FacturaElectronica>"""


@tagged('post_install', '-at_install')
class TestProveedorEmail(TransactionCase):

    def _make_message_with_attachment(self, record, content_string, filename):
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(content_string.encode('utf-8')),
            'res_model': 'l10n_cr.fe.proveedor.email',
            'res_id': record.id,
        })
        return self.env['mail.message'].create({
            'model': 'l10n_cr.fe.proveedor.email',
            'res_id': record.id,
            'attachment_ids': [(6, 0, attachment.ids)],
        })

    def test_procesar_adjuntos_crea_factura_con_xml_valido(self):
        record = self.env['l10n_cr.fe.proveedor.email'].create({'email_from': 'proveedor@x.cr'})
        message = self._make_message_with_attachment(record, SAMPLE_XML, 'factura.xml')
        record._l10n_cr_fe_procesar_adjuntos(message)
        self.assertEqual(record.state, 'procesado')
        self.assertTrue(record.move_id)
        self.assertEqual(record.move_id.l10n_cr_fe_proveedor_clave,
                          '50627072600020840085800100001010000000009123456789')

    def test_procesar_adjuntos_detecta_clave_duplicada(self):
        existing = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'l10n_cr_fe_proveedor_clave': '50627072600020840085800100001010000000009123456789',
        })
        record = self.env['l10n_cr.fe.proveedor.email'].create({'email_from': 'proveedor@x.cr'})
        message = self._make_message_with_attachment(record, SAMPLE_XML, 'factura.xml')
        record._l10n_cr_fe_procesar_adjuntos(message)
        self.assertEqual(record.state, 'duplicado')
        self.assertEqual(record.move_id, existing)

    def test_procesar_adjuntos_sin_ningun_adjunto_xml(self):
        record = self.env['l10n_cr.fe.proveedor.email'].create({'email_from': 'alguien@x.cr'})
        message = self._make_message_with_attachment(record, 'hola, tengo una duda', 'nota.txt')
        record._l10n_cr_fe_procesar_adjuntos(message)
        self.assertEqual(record.state, 'sin_xml_valido')
        self.assertFalse(record.move_id)
        self.assertTrue(record.error_message)

    def test_procesar_adjuntos_xml_con_extension_pero_invalido(self):
        record = self.env['l10n_cr.fe.proveedor.email'].create({'email_from': 'alguien@x.cr'})
        message = self._make_message_with_attachment(record, 'esto no es un xml valido', 'factura.xml')
        record._l10n_cr_fe_procesar_adjuntos(message)
        self.assertEqual(record.state, 'sin_xml_valido')
        self.assertFalse(record.move_id)

    def test_procesar_adjuntos_xml_con_campo_numerico_invalido(self):
        xml_con_cantidad_invalida = SAMPLE_XML.replace(
            '<Cantidad>10</Cantidad>', '<Cantidad>diez</Cantidad>')
        record = self.env['l10n_cr.fe.proveedor.email'].create({'email_from': 'alguien@x.cr'})
        message = self._make_message_with_attachment(record, xml_con_cantidad_invalida, 'factura.xml')
        record._l10n_cr_fe_procesar_adjuntos(message)
        self.assertEqual(record.state, 'sin_xml_valido')
        self.assertFalse(record.move_id)
