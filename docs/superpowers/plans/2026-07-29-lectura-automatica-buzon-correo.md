# Lectura automática de un buzón de correo (XML de proveedores) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatizar la entrada del XML de facturas de proveedores a Odoo leyendo un buzón de correo dedicado (Gmail/Google Workspace vía OAuth2), sin cambiar nada del flujo de revisión/aceptación ya construido.

**Architecture:** Se reutiliza el modelo nativo de Odoo `fetchmail.server` (con `server_type='gmail'`, del módulo `google_gmail`) apuntando (`object_id`) a un modelo nuevo `l10n_cr.fe.proveedor.email` que hereda `mail.thread`. Un hook sobre ese modelo revisa los adjuntos del correo entrante, y si hay un XML válido de factura CR v4.4, crea el `account.move` (in_invoice) reutilizando la misma lógica de parseo que ya usa el asistente manual (`l10n_cr.fe.proveedor.upload`) — extraída a un método compartido en `account.move` para no duplicar código.

**Tech Stack:** Odoo 19 ORM, `mail.thread` (mixin nativo), `fetchmail.server`/`google_gmail` (nativos, no se tocan), Python `xml.etree.ElementTree` (ya usado en este módulo).

## Global Constraints

- Spec de referencia: `docs/superpowers/specs/2026-07-29-lectura-automatica-buzon-correo-design.md`.
- Seguir el estilo TDD ya establecido en este módulo: escribir el test, correrlo para confirmar que falla (RED), implementar, correrlo para confirmar que pasa (GREEN), commit.
- Comando estándar para correr tests de este módulo (reemplazar `<TAGS>` por el tag específico o `/l10n_cr_fe_crlibre` para todo el módulo):
  ```bash
  MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags <TAGS> --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
  ```
  El flag `-u l10n_cr_fe_crlibre` es necesario siempre que se agreguen/cambien campos, modelos o vistas — actualiza el esquema/registro antes de correr los tests.
- Imports ordenados: futuro → stdlib → terceros → odoo (primero) → odoo.addons (local) — ya enforced por `ruff.toml`.
- Prefijo de métodos propios de este módulo: `_l10n_cr_fe_*` (convención ya establecida en `account_move.py`).
- **No** se configura el `fetchmail.server` real (cuenta OAuth de Gmail) como parte de este plan — es configuración de datos/infraestructura externa, documentada en la spec, fuera del alcance de estas tareas.
- Después del último task, reiniciar el contenedor vivo (`docker restart erp-odoo-1`) para que el usuario pueda probar manualmente.

---

### Task 1: Extraer el parseo del XML de proveedor a un método compartido en `account.move`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Modify: `addons/l10n_cr_fe_crlibre/wizards/proveedor_upload.py`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_proveedor_xml_parser.py`

**Interfaces:**
- Produces: `account.move._l10n_cr_fe_build_vals_from_proveedor_xml(self, xml_bytes)` — método de instancia (se llama sobre un recordset vacío, ej. `self.env['account.move']._l10n_cr_fe_build_vals_from_proveedor_xml(xml_bytes)`), recibe el XML ya decodificado de base64 (bytes), devuelve un `dict` listo para `account.move.create(...)` con las claves: `move_type`, `partner_id`, `invoice_date`, `l10n_cr_fe_proveedor_clave`, `l10n_cr_fe_proveedor_fecha_emision`, `l10n_cr_fe_proveedor_monto_impuesto`, `l10n_cr_fe_proveedor_total`, `l10n_cr_fe_proveedor_subtotal`, `invoice_line_ids`. Levanta `UserError` si el XML no es válido o le faltan `Clave`/`Emisor`/líneas de detalle.
- Consumes: nada de otras tareas (es la base de las siguientes).

- [ ] **Step 1: Escribir los tests del método compartido (deben fallar)**

Crear `addons/l10n_cr_fe_crlibre/tests/test_proveedor_xml_parser.py`:

```python
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
```

- [ ] **Step 2: Correr los tests para confirmar que fallan (RED)**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons --test-enable --test-tags /l10n_cr_fe_crlibre:TestProveedorXmlParser --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: FAIL con `AttributeError: 'account.move' object has no attribute '_l10n_cr_fe_build_vals_from_proveedor_xml'` (o similar) en los 5 tests.

- [ ] **Step 3: Implementar el método compartido en `account_move.py`**

Abrir `addons/l10n_cr_fe_crlibre/models/account_move.py`. Los imports `base64` y `xml.etree.ElementTree as ET` ya existen al inicio del archivo (líneas 1 y 4) — no hace falta agregarlos.

Agregar estos métodos nuevos en la clase `AccountMove` (junto a los demás métodos `_l10n_cr_fe_*`, por ejemplo justo antes de `_l10n_cr_fe_build_mr_params`):

```python
    def _l10n_cr_fe_xml_find_text(self, node, tag):
        el = node.find('.//{*}%s' % tag)
        return el.text.strip() if el is not None and el.text else ''

    def _l10n_cr_fe_xml_find_product(self, cabys):
        if not cabys:
            return self.env['product.product']
        return self.env['product.product'].search([('l10n_cr_fe_cabys', '=', cabys)], limit=1)

    def _l10n_cr_fe_xml_find_tax(self, tarifa_percent):
        if not tarifa_percent:
            return self.env['account.tax']
        return self.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'),
            ('amount', '=', tarifa_percent),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

    def _l10n_cr_fe_build_vals_from_proveedor_xml(self, xml_bytes):
        """Parsea un XML de factura de proveedor (schema Hacienda v4.4) y
        devuelve el dict de creación para un account.move in_invoice. Usado
        tanto por el asistente manual (l10n_cr.fe.proveedor.upload) como por
        el flujo automático de lectura de correo — misma lógica, un solo
        lugar. Levanta UserError si el XML no tiene los datos mínimos."""
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError:
            raise UserError(_("El archivo no es un XML válido."))

        clave = self._l10n_cr_fe_xml_find_text(root, 'Clave')
        fecha_emision = self._l10n_cr_fe_xml_find_text(root, 'FechaEmision')
        emisor_el = root.find('.//{*}Emisor')
        if emisor_el is None or not clave:
            raise UserError(_(
                "El XML no tiene los datos mínimos de un comprobante electrónico (Clave/Emisor)."))
        emisor_nombre = self._l10n_cr_fe_xml_find_text(emisor_el, 'Nombre')
        emisor_cedula = self._l10n_cr_fe_xml_find_text(emisor_el, 'Numero')
        emisor_email = self._l10n_cr_fe_xml_find_text(emisor_el, 'CorreoElectronico')
        if not emisor_cedula:
            raise UserError(_("El XML no tiene la identificación del emisor."))

        partner = self.env['res.partner'].search([
            ('vat', '=', emisor_cedula),
            ('company_id', 'in', (False, self.env.company.id)),
        ], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': emisor_nombre or emisor_cedula,
                'vat': emisor_cedula,
                'email': emisor_email or False,
                'company_type': 'company',
            })

        invoice_lines = []
        for linea in root.findall('.//{*}LineaDetalle'):
            cabys = self._l10n_cr_fe_xml_find_text(linea, 'CodigoCABYS')
            cantidad = float(self._l10n_cr_fe_xml_find_text(linea, 'Cantidad') or '0')
            precio_unitario = float(self._l10n_cr_fe_xml_find_text(linea, 'PrecioUnitario') or '0')
            detalle = self._l10n_cr_fe_xml_find_text(linea, 'Detalle')
            tarifa_text = self._l10n_cr_fe_xml_find_text(linea, 'Tarifa')
            tarifa_percent = float(tarifa_text) if tarifa_text else 0.0
            product = self._l10n_cr_fe_xml_find_product(cabys)
            tax = self._l10n_cr_fe_xml_find_tax(tarifa_percent)
            invoice_lines.append((0, 0, {
                'product_id': product.id or False,
                'quantity': cantidad,
                'price_unit': precio_unitario,
                'name': detalle or (product.display_name if product else _("Completar producto")),
                'tax_ids': [(6, 0, tax.ids)],
            }))

        if not invoice_lines:
            raise UserError(_("El XML no tiene líneas de detalle."))

        monto_impuesto_text = self._l10n_cr_fe_xml_find_text(root, 'TotalImpuesto')
        total_factura_text = self._l10n_cr_fe_xml_find_text(root, 'TotalComprobante')
        subtotal_text = self._l10n_cr_fe_xml_find_text(root, 'TotalVentaNeta')

        return {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': fecha_emision.split('T')[0] if fecha_emision else False,
            'l10n_cr_fe_proveedor_clave': clave,
            'l10n_cr_fe_proveedor_fecha_emision': fecha_emision,
            'l10n_cr_fe_proveedor_monto_impuesto': float(monto_impuesto_text) if monto_impuesto_text else 0.0,
            'l10n_cr_fe_proveedor_total': float(total_factura_text) if total_factura_text else 0.0,
            'l10n_cr_fe_proveedor_subtotal': float(subtotal_text) if subtotal_text else 0.0,
            'invoice_line_ids': invoice_lines,
        }
```

- [ ] **Step 4: Correr los tests para confirmar que pasan (GREEN)**

Run: mismo comando del Step 2.
Expected: `0 failed, 0 error(s) of 5 tests`.

- [ ] **Step 5: Simplificar el asistente para que delegue en el método compartido**

Reemplazar el contenido completo de `addons/l10n_cr_fe_crlibre/wizards/proveedor_upload.py`:

```python
import base64

from odoo import fields, models


class L10nCrFeProveedorUpload(models.TransientModel):
    _name = 'l10n_cr.fe.proveedor.upload'
    _description = "Cargar factura electrónica de un proveedor"

    xml_file = fields.Binary(string="Archivo XML", required=True)
    xml_filename = fields.Char(string="Nombre del archivo")

    def action_procesar(self):
        self.ensure_one()
        vals = self.env['account.move']._l10n_cr_fe_build_vals_from_proveedor_xml(
            base64.b64decode(self.xml_file))
        invoice = self.env['account.move'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }
```

- [ ] **Step 6: Correr TODOS los tests del asistente para confirmar que no hay regresión**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestProveedorUpload,/l10n_cr_fe_crlibre:TestProveedorXmlParser --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: `0 failed, 0 error(s)` en ambas clases de test (los tests existentes de `TestProveedorUpload` deben seguir pasando exactamente igual, sin haberlos tocado — confirma que el refactor no cambió el comportamiento del asistente).

- [ ] **Step 7: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/wizards/proveedor_upload.py addons/l10n_cr_fe_crlibre/tests/test_proveedor_xml_parser.py
git commit -m "refactor(l10n_cr_fe_crlibre): extraer parseo de XML de proveedor a account.move

Se mueve la logica de parseo del XML (Clave/Emisor/lineas/ResumenFactura,
matching de CABYS e impuesto, resolucion de partner) del asistente manual
a un metodo compartido en account.move, para que el flujo automatico de
lectura de correo (siguiente tarea) reutilice exactamente la misma logica
sin duplicarla.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Modelo `l10n_cr.fe.proveedor.email` con el hook de procesamiento de adjuntos

**Files:**
- Create: `addons/l10n_cr_fe_crlibre/models/proveedor_email.py`
- Modify: `addons/l10n_cr_fe_crlibre/models/__init__.py`
- Modify: `addons/l10n_cr_fe_crlibre/security/ir.model.access.csv`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_proveedor_email.py`

**Interfaces:**
- Consumes: `account.move._l10n_cr_fe_build_vals_from_proveedor_xml(xml_bytes)` de la Task 1.
- Produces: modelo `l10n_cr.fe.proveedor.email` con campos `email_from` (Char), `date` (Datetime), `state` (Selection: `procesado`/`duplicado`/`sin_xml_valido`), `move_id` (Many2one `account.move`), `error_message` (Text); método `_l10n_cr_fe_procesar_adjuntos(self, message)` donde `message` es un recordset `mail.message` (usa `message.attachment_ids`).

- [ ] **Step 1: Escribir los tests del modelo y el hook (deben fallar)**

Crear `addons/l10n_cr_fe_crlibre/tests/test_proveedor_email.py`:

```python
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
```

- [ ] **Step 2: Correr los tests para confirmar que fallan (RED)**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestProveedorEmail --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: FAIL — el modelo `l10n_cr.fe.proveedor.email` todavía no existe (`KeyError` o `ValueError` al hacer `self.env['l10n_cr.fe.proveedor.email']`).

- [ ] **Step 3: Crear el modelo con el hook**

Crear `addons/l10n_cr_fe_crlibre/models/proveedor_email.py`:

```python
import base64

from odoo import _, fields, models
from odoo.exceptions import UserError


class L10nCrFeProveedorEmail(models.Model):
    _name = 'l10n_cr.fe.proveedor.email'
    _inherit = ['mail.thread']
    _description = "Correo entrante de proveedor (XML de factura electrónica)"
    _order = 'id desc'
    _primary_email = 'email_from'

    email_from = fields.Char(string="Remitente", readonly=True)
    date = fields.Datetime(string="Fecha de recepción", readonly=True)
    state = fields.Selection([
        ('procesado', "Factura creada"),
        ('duplicado', "Ya existía (Clave duplicada)"),
        ('sin_xml_valido', "Sin XML válido"),
    ], string="Estado", readonly=True)
    move_id = fields.Many2one('account.move', string="Factura de proveedor", readonly=True)
    error_message = fields.Text(string="Motivo", readonly=True)

    def _l10n_cr_fe_procesar_adjuntos(self, message):
        self.ensure_one()
        for attachment in message.attachment_ids.filtered(
                lambda a: a.name and a.name.lower().endswith('.xml')):
            try:
                vals = self.env['account.move']._l10n_cr_fe_build_vals_from_proveedor_xml(
                    base64.b64decode(attachment.datas))
            except UserError:
                continue
            clave = vals['l10n_cr_fe_proveedor_clave']
            existing = self.env['account.move'].search(
                [('l10n_cr_fe_proveedor_clave', '=', clave)], limit=1)
            if existing:
                self.write({'state': 'duplicado', 'move_id': existing.id})
            else:
                move = self.env['account.move'].create(vals)
                self.write({'state': 'procesado', 'move_id': move.id})
            return
        self.write({
            'state': 'sin_xml_valido',
            'error_message': _("El correo no traía ningún adjunto XML de factura "
                                "electrónica válido."),
        })
```

Registrar el modelo nuevo en `addons/l10n_cr_fe_crlibre/models/__init__.py`, agregando la línea al final:

```python
from . import crlibre_client
from . import fe_config
from . import product_template
from . import res_partner
from . import account_move
from . import proveedor_email
```

Agregar los permisos en `addons/l10n_cr_fe_crlibre/security/ir.model.access.csv` (dos líneas nuevas al final del archivo):

```csv
access_l10n_cr_fe_proveedor_email_user,l10n_cr.fe.proveedor.email.user,model_l10n_cr_fe_proveedor_email,account.group_account_invoice,1,0,0,0
access_l10n_cr_fe_proveedor_email_admin,l10n_cr.fe.proveedor.email.admin,model_l10n_cr_fe_proveedor_email,account.group_account_manager,1,1,1,1
```

- [ ] **Step 4: Correr los tests para confirmar que pasan (GREEN)**

Run: mismo comando del Step 2.
Expected: `0 failed, 0 error(s) of 4 tests`.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/proveedor_email.py addons/l10n_cr_fe_crlibre/models/__init__.py addons/l10n_cr_fe_crlibre/security/ir.model.access.csv addons/l10n_cr_fe_crlibre/tests/test_proveedor_email.py
git commit -m "feat(l10n_cr_fe_crlibre): modelo de bandeja de entrada para XML de proveedores por correo

Nuevo modelo l10n_cr.fe.proveedor.email (hereda mail.thread) que sera
el destino del fetchmail.server dedicado a proveedores. Su hook revisa
los adjuntos del correo entrante: si hay un XML valido de factura CR
v4.4, crea el account.move (reutilizando el parseo compartido de la
tarea anterior) y detecta duplicados por Clave; si no, registra el
motivo sin crear ninguna factura.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Vistas, menú y registro en el manifest

**Files:**
- Create: `addons/l10n_cr_fe_crlibre/views/proveedor_email_views.xml`
- Modify: `addons/l10n_cr_fe_crlibre/__manifest__.py`

**Interfaces:**
- Consumes: modelo `l10n_cr.fe.proveedor.email` de la Task 2 (campos `email_from`, `date`, `state`, `move_id`, `error_message`).
- Produces: menú "Bandeja de facturas de proveedores" visible en Contabilidad, junto al menú existente "Cargar factura de proveedor (FE)".

- [ ] **Step 1: Crear las vistas y el menú**

Crear `addons/l10n_cr_fe_crlibre/views/proveedor_email_views.xml`:

```xml
<odoo>
    <record id="view_l10n_cr_fe_proveedor_email_list" model="ir.ui.view">
        <field name="name">l10n_cr.fe.proveedor.email.list</field>
        <field name="model">l10n_cr.fe.proveedor.email</field>
        <field name="arch" type="xml">
            <list>
                <field name="date"/>
                <field name="email_from"/>
                <field name="state"/>
                <field name="move_id"/>
            </list>
        </field>
    </record>
    <record id="view_l10n_cr_fe_proveedor_email_form" model="ir.ui.view">
        <field name="name">l10n_cr.fe.proveedor.email.form</field>
        <field name="model">l10n_cr.fe.proveedor.email</field>
        <field name="arch" type="xml">
            <form string="Correo de proveedor">
                <sheet>
                    <group>
                        <field name="email_from"/>
                        <field name="date"/>
                        <field name="state"/>
                        <field name="move_id"/>
                        <field name="error_message" invisible="state != 'sin_xml_valido'"/>
                    </group>
                </sheet>
                <chatter reload_on_attachment="True"/>
            </form>
        </field>
    </record>
    <record id="action_l10n_cr_fe_proveedor_email" model="ir.actions.act_window">
        <field name="name">Bandeja de facturas de proveedores</field>
        <field name="res_model">l10n_cr.fe.proveedor.email</field>
        <field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_l10n_cr_fe_proveedor_email"
              name="Bandeja de facturas de proveedores"
              parent="account.menu_finance_payables"
              action="action_l10n_cr_fe_proveedor_email"
              sequence="16"/>
</odoo>
```

- [ ] **Step 2: Registrar el archivo de vista en el manifest**

En `addons/l10n_cr_fe_crlibre/__manifest__.py`, agregar la línea nueva después de `'views/mr_motivo_wizard_views.xml',`:

```python
        'views/mr_motivo_wizard_views.xml',
        'views/proveedor_email_views.xml',
```

- [ ] **Step 3: Actualizar el módulo y confirmar que carga sin errores**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: `Module l10n_cr_fe_crlibre loaded in ...` sin ningún `ERROR` en el log (en particular, sin errores de parseo de vista ni de referencia de menú faltante).

- [ ] **Step 4: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/views/proveedor_email_views.xml addons/l10n_cr_fe_crlibre/__manifest__.py
git commit -m "feat(l10n_cr_fe_crlibre): vistas y menu para la bandeja de facturas de proveedores

Lista/formulario para auditar el modelo l10n_cr.fe.proveedor.email:
que correos llegaron, en que quedaron (factura creada/duplicado/sin
XML valido), y la factura resultante si aplica.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Mapear remitente/fecha del correo entrante y prueba de integración end-to-end

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/proveedor_email.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_proveedor_email.py`

**Interfaces:**
- Consumes: todo lo de las Tasks 1-3.
- Produces: nada nuevo para otras tareas — esta es la última tarea del plan.

**Contexto técnico (verificado contra el código fuente real de Odoo, `odoo/addons/mail/models/mail_thread.py`):**
- `mail.thread.message_new(msg_dict, custom_values=None)` es un método `@api.model`. Por defecto, si el modelo define el atributo de clase `_primary_email = 'email_from'` (ya se agregó en la Task 2), Odoo copia automáticamente `msg_dict['email_from']` a ese campo — **no hace falta código extra para eso**. El campo `date` NO se mapea automáticamente; hay que hacerlo a mano sobrescribiendo `message_new`.
- `mail.thread.message_process(model, message, ...)` (classmethod de instancia, se llama como `self.env['mail.thread'].message_process(...)`) recibe el email crudo en formato RFC2822 (bytes o str) y devuelve el **id entero** (`int`) del registro creado/actualizado — hay que hacer `.browse(...)` sobre ese id para obtener el recordset.

- [ ] **Step 1: Escribir el test de integración end-to-end (debe fallar)**

Agregar al final de `addons/l10n_cr_fe_crlibre/tests/test_proveedor_email.py` (agregar el import `uuid` y `from email.message import EmailMessage` al inicio del archivo, junto a los imports existentes):

```python
import uuid
from email.message import EmailMessage
```

Y el test nuevo, dentro de la clase `TestProveedorEmail`:

```python
    def _build_raw_email(self, xml_string, sender='proveedor@x.cr', subject='Factura'):
        msg = EmailMessage()
        msg['From'] = sender
        msg['To'] = 'facturas@tuempresa.cr'
        msg['Subject'] = subject
        msg['Message-Id'] = '<test-%s@x.cr>' % uuid.uuid4()
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
```

- [ ] **Step 2: Correr el test para confirmar que falla (RED)**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons --test-enable --test-tags /l10n_cr_fe_crlibre:TestProveedorEmail.test_message_process_end_to_end_crea_registro_y_factura --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: FAIL — `record.state` queda vacío/`False` (el registro se crea por el `message_new` genérico de `mail.thread`, pero como todavía no existe `_message_post_after_hook`, nunca se llama a `_l10n_cr_fe_procesar_adjuntos`; y `record.date` también queda vacío porque `message_new` no está sobrescrito aún).

- [ ] **Step 3: Sobrescribir `message_new` y `_message_post_after_hook`**

En `addons/l10n_cr_fe_crlibre/models/proveedor_email.py`, cambiar el import de `odoo` para incluir `api`:

```python
from odoo import _, api, fields, models
```

Y agregar estos dos métodos a la clase `L10nCrFeProveedorEmail` (antes de `_l10n_cr_fe_procesar_adjuntos`):

```python
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        custom_values = dict(custom_values or {})
        custom_values.setdefault('date', msg_dict.get('date'))
        return super().message_new(msg_dict, custom_values=custom_values)

    def _message_post_after_hook(self, new_message, message_values):
        res = super()._message_post_after_hook(new_message, message_values)
        self._l10n_cr_fe_procesar_adjuntos(new_message)
        return res
```

- [ ] **Step 4: Correr el test para confirmar que pasa (GREEN)**

Run: mismo comando del Step 2.
Expected: PASS.

- [ ] **Step 5: Correr TODA la suite del módulo para confirmar que no hay ninguna regresión**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: `0 failed, 0 error(s)` en toda la suite (la de este módulo tenía 120 tests antes de este plan; debe subir en 10 — 5 de `TestProveedorXmlParser` + 5 de `TestProveedorEmail` — sin que ningún test existente se rompa).

- [ ] **Step 6: Actualizar la spec con la nota de verificación técnica**

En `docs/superpowers/specs/2026-07-29-lectura-automatica-buzon-correo-design.md`, al final de la sección 7 ("Verificación"), agregar:

```markdown

**Nota de implementación:** se confirmó contra el código fuente de `mail.thread` que `_primary_email = 'email_from'` (atributo de clase) le basta a Odoo para mapear automáticamente el remitente sin código adicional; solo `date` necesitó un override explícito de `message_new`. `message_process` devuelve el id entero del registro creado, no un recordset.
```

- [ ] **Step 7: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/proveedor_email.py addons/l10n_cr_fe_crlibre/tests/test_proveedor_email.py docs/superpowers/specs/2026-07-29-lectura-automatica-buzon-correo-design.md
git commit -m "feat(l10n_cr_fe_crlibre): mapear remitente/fecha del correo y prueba end-to-end

Se completa el modelo l10n_cr.fe.proveedor.email con _primary_email
(remitente automatico) y un override de message_new para la fecha de
recepcion. Se agrega una prueba de integracion completa usando
mail.thread.message_process (sin conexion IMAP real), que ejercita
todo el camino real que usara fetchmail.server: correo crudo -> nuevo
registro -> hook -> factura de proveedor creada.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

- [ ] **Step 8: Reiniciar el servidor vivo**

Run:
```bash
docker restart erp-odoo-1
```

Esto recarga el código en memoria del contenedor `erp-odoo-1` para que el usuario pueda ver el nuevo menú "Bandeja de facturas de proveedores" en la interfaz. **Recordar al usuario**: para que esto funcione con un buzón real, todavía falta el paso de configuración externa descrito en la sección 2 de la spec (proyecto OAuth en Google Cloud Console + crear el registro `fetchmail.server` con `server_type='gmail'` y `object_id` apuntando a `l10n_cr.fe.proveedor.email`) — eso no lo hace este plan.
