import base64
import uuid
from email.message import EmailMessage
from email.utils import formatdate

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
        # El motivo real del UserError debe conservarse, no el mensaje
        # genérico de "no traía ningún adjunto XML válido" -- sí había un
        # adjunto XML, solo que un campo no era numérico.
        self.assertIn('no numérico', record.error_message)
        self.assertNotIn('no traía ningún adjunto', record.error_message)

    def test_message_post_no_reprocesa_registro_ya_resuelto(self):
        """Un mensaje posterior sin XML (respuesta, nota) sobre un registro
        que ya llegó a 'procesado' no debe volver a correr
        _l10n_cr_fe_procesar_adjuntos ni tocar el move_id ya enlazado."""
        record = self.env['l10n_cr.fe.proveedor.email'].create({'email_from': 'proveedor@x.cr'})
        first_message = self._make_message_with_attachment(record, SAMPLE_XML, 'factura.xml')
        record._l10n_cr_fe_procesar_adjuntos(first_message)
        self.assertEqual(record.state, 'procesado')
        move = record.move_id
        self.assertTrue(move)

        # Un mensaje nuevo sin adjunto XML, posteado a través de message_post
        # (para ejercitar _message_post_after_hook de verdad, no solo el
        # método interno).
        record.message_post(body='Gracias, quedamos atentos.')

        self.assertEqual(record.state, 'procesado')
        self.assertEqual(record.move_id, move)

    def _build_raw_email(self, xml_string, sender='proveedor@x.cr', subject='Factura'):
        msg = EmailMessage()
        msg['From'] = sender
        msg['To'] = 'facturas@tuempresa.cr'
        msg['Subject'] = subject
        msg['Message-Id'] = '<test-%s@x.cr>' % uuid.uuid4()
        msg['Date'] = formatdate(localtime=True)
        msg.set_content('Adjunto la factura electrónica.')
        msg.add_attachment(xml_string.encode('utf-8'), maintype='application',
                            subtype='xml', filename='factura.xml')
        return msg.as_bytes()

    def test_message_process_end_to_end_crea_registro_y_factura(self):
        raw_email = self._build_raw_email(SAMPLE_XML)
        thread_id = self.env['mail.thread'].message_process(
            'l10n_cr.fe.proveedor.email', raw_email)
        record = self.env['l10n_cr.fe.proveedor.email'].browse(thread_id)
        self.assertEqual(record.email_from, 'proveedor@x.cr')
        self.assertTrue(record.date)
        self.assertEqual(record.state, 'procesado')
        self.assertTrue(record.move_id)
        self.assertEqual(record.move_id.l10n_cr_fe_proveedor_clave,
                          '50627072600020840085800100001010000000009123456789')
