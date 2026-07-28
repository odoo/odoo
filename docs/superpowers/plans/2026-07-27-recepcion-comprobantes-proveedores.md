# Recepción y aceptación de comprobantes de proveedores — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir subir el XML de una factura electrónica recibida de un proveedor, revisarla en Odoo, y responder a Hacienda con el Mensaje Receptor correcto (aceptación total, aceptación parcial o rechazo), creando la factura de proveedor correspondiente en el mismo flujo.

**Architecture:** Extiende `l10n_cr_fe_crlibre` (mismo módulo de FE/NC/TE), generalizando la resolución de tipo de documento (`_l10n_cr_fe_get_tipo_documento_info`) y el despacho de envío (`_l10n_cr_fe_generate_and_send`) para un cuarto caso: `move_type='in_invoice'`, cuyo tipo de documento (CCE/CPCE/RCE) depende de la decisión del usuario, no de un flag fijo. Un asistente nuevo parsea el XML del proveedor y arma la factura en borrador; tres acciones nuevas disparan cada decisión.

**Tech Stack:** Odoo 19 ORM (Python), `xml.etree.ElementTree` para parsear el XML recibido, vistas XML, `odoo.tests.common.TransactionCase`, cliente HTTP propio (`crlibre_client.py`) contra la API_Hacienda (CRLibre).

## Global Constraints

- No se modifica ningún archivo bajo `odoo/` ni `addons/account/` — solo `addons/l10n_cr_fe_crlibre/`.
- Cada decisión (`aceptado`/`aceptado_parcial`/`rechazado`) es un tipo de documento Hacienda distinto con su propio consecutivo independiente: `CCE` (código `05`), `CPCE` (código `06`), `RCE` (código `07`) — verificado contra `clave.php` real.
- El envío del Mensaje Receptor usa la acción `sendMensaje` de la API (parámetro adicional obligatorio `consecutivoReceptor`), **no** la acción genérica `send`/`json` que usa `send_fe` para FE/NC/TE — requiere un método de cliente nuevo (`send_mr`), no reutilizar `send_fe`.
- La aceptación parcial no tiene desglose por línea en el XML de Hacienda (`genXMLMr` solo lleva un monto total y un monto de impuesto agregados) — el usuario ajusta las líneas de la factura de proveedor en Odoo directamente (edición nativa, sin asistente de selección nuevo) antes de aceptar parcialmente; el monto reportado sale de ahí.
- `l10n_cr_fe_mr_motivo` es obligatorio para `aceptado_parcial` y `rechazado`.
- Al cargar el XML: buscar producto por CABYS existente; si no se encuentra, la línea queda sin producto para completar a mano — nunca se crean productos automáticamente. De forma análoga, buscar un impuesto de compra (`account.tax`, `type_tax_use='purchase'`) por porcentaje; si no se encuentra, la línea queda sin impuesto para completar a mano.
- Rechazar una factura de proveedor no contabiliza el `in_invoice` (queda en borrador, no se llama `action_post`).
- Fuera de alcance (no implementar en este plan): lectura automática de correo, comparación contra Orden de Compra, recordatorios de plazo, correo automático al proveedor, Nota de Débito y otros comprobantes especiales.

---

### Task 1: Campos + resolución de tipo de documento para `in_invoice`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py:26-34` (constante nueva), `:86-90` (campos nuevos), `:106-110` (helper), `:384-389` (`action_post`)
- Test: `addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py`, `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`

**Interfaces:**
- Consumes: `L10N_CR_FE_TIPO_DOCUMENTO`, `L10N_CR_FE_TIPO_DOCUMENTO_TE`, `_l10n_cr_fe_get_tipo_documento_info()` (existentes, de Tiquete Electrónico).
- Produces: constante `L10N_CR_FE_TIPO_DOCUMENTO_MR` (dict por decisión); campos `l10n_cr_fe_mr_decision`, `l10n_cr_fe_mr_motivo`, `l10n_cr_fe_proveedor_clave`, `l10n_cr_fe_proveedor_fecha_emision`; `_l10n_cr_fe_get_tipo_documento_info()` ahora resuelve `in_invoice` por `l10n_cr_fe_mr_decision` (retorna `None`/falsy si no hay decisión aún) — usado por Tasks 2 y 3.

- [ ] **Step 1: Escribir los tests que fallan**

En `addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py`, agregar al final de la clase `TestAccountMoveFeFields`:

```python
    def test_mr_fields_exist_with_defaults(self):
        partner = self.env['res.partner'].create({'name': 'Proveedor MR Fields'})
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
        })
        self.assertFalse(bill.l10n_cr_fe_mr_decision)
        self.assertFalse(bill.l10n_cr_fe_mr_motivo)
        self.assertFalse(bill.l10n_cr_fe_proveedor_clave)
        self.assertFalse(bill.l10n_cr_fe_proveedor_fecha_emision)

    def test_tipo_documento_mr_constant(self):
        from odoo.addons.l10n_cr_fe_crlibre.models.account_move import L10N_CR_FE_TIPO_DOCUMENTO_MR
        self.assertEqual(L10N_CR_FE_TIPO_DOCUMENTO_MR, {
            'aceptado': {'clave': 'CCE', 'consecutivo_codigo': '05', 'gen_xml_action': 'gen_xml_mr'},
            'aceptado_parcial': {'clave': 'CPCE', 'consecutivo_codigo': '06', 'gen_xml_action': 'gen_xml_mr'},
            'rechazado': {'clave': 'RCE', 'consecutivo_codigo': '07', 'gen_xml_action': 'gen_xml_mr'},
        })
```

En `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`, agregar al final de la clase `TestAccountMoveMapping`:

```python
    def test_get_tipo_documento_info_in_invoice_without_decision_returns_falsy(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
        })
        self.assertFalse(bill._l10n_cr_fe_get_tipo_documento_info())

    def test_get_tipo_documento_info_in_invoice_resolves_by_decision(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_mr_decision': 'aceptado_parcial',
        })
        info = bill._l10n_cr_fe_get_tipo_documento_info()
        self.assertEqual(info['clave'], 'CPCE')
        self.assertEqual(info['consecutivo_codigo'], '06')
```

- [ ] **Step 2: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveFeFields.test_tipo_documento_mr_constant --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: FAIL — `ImportError: cannot import name 'L10N_CR_FE_TIPO_DOCUMENTO_MR'`.

- [ ] **Step 3: Implementar la constante, los campos y el helper**

En `addons/l10n_cr_fe_crlibre/models/account_move.py`, después de la constante `L10N_CR_FE_TIPO_DOCUMENTO_TE` (línea 34), agregar:

```python

# Mensaje Receptor (MR): respuesta obligatoria de Hacienda cuando esta empresa
# recibe una factura electronica de un proveedor. Cada decision (aceptar
# total, aceptar parcial, rechazar) es su propio tipo de documento con su
# propio consecutivo independiente (Anexo v4.4): 05=CCE (aceptacion total),
# 06=CPCE (aceptacion parcial), 07=RCE (rechazo). Se resuelve por
# l10n_cr_fe_mr_decision, no por move_type, en _l10n_cr_fe_get_tipo_documento_info().
L10N_CR_FE_TIPO_DOCUMENTO_MR = {
    'aceptado': {'clave': 'CCE', 'consecutivo_codigo': '05', 'gen_xml_action': 'gen_xml_mr'},
    'aceptado_parcial': {'clave': 'CPCE', 'consecutivo_codigo': '06', 'gen_xml_action': 'gen_xml_mr'},
    'rechazado': {'clave': 'RCE', 'consecutivo_codigo': '07', 'gen_xml_action': 'gen_xml_mr'},
}
```

Luego, en la declaración de campos de la clase `AccountMove` (después de `l10n_cr_fe_es_tiquete`, antes de `l10n_cr_fe_state`), agregar:

```python
    l10n_cr_fe_mr_decision = fields.Selection(
        selection=[
            ('aceptado', "Aceptado"),
            ('aceptado_parcial', "Aceptado parcialmente"),
            ('rechazado', "Rechazado"),
        ],
        string="Decisión sobre la factura del proveedor", copy=False)
    l10n_cr_fe_mr_motivo = fields.Char(string="Motivo (Mensaje Receptor)", copy=False)
    l10n_cr_fe_proveedor_clave = fields.Char(string="Clave de la factura del proveedor", readonly=True, copy=False)
    l10n_cr_fe_proveedor_fecha_emision = fields.Char(string="Fecha de emisión (proveedor)", readonly=True, copy=False)
```

Luego, reemplazar `_l10n_cr_fe_get_tipo_documento_info`:

```python
    def _l10n_cr_fe_get_tipo_documento_info(self):
        self.ensure_one()
        if self.move_type == 'out_invoice' and self.l10n_cr_fe_es_tiquete:
            return L10N_CR_FE_TIPO_DOCUMENTO_TE
        return L10N_CR_FE_TIPO_DOCUMENTO.get(self.move_type)
```

por:

```python
    def _l10n_cr_fe_get_tipo_documento_info(self):
        self.ensure_one()
        if self.move_type == 'out_invoice' and self.l10n_cr_fe_es_tiquete:
            return L10N_CR_FE_TIPO_DOCUMENTO_TE
        if self.move_type == 'in_invoice':
            return L10N_CR_FE_TIPO_DOCUMENTO_MR.get(self.l10n_cr_fe_mr_decision)
        return L10N_CR_FE_TIPO_DOCUMENTO.get(self.move_type)
```

Por último, en `action_post`, reemplazar:

```python
    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.move_type in L10N_CR_FE_TIPO_DOCUMENTO:
                move._l10n_cr_fe_generate_and_send()
        return res
```

por:

```python
    def action_post(self):
        res = super().action_post()
        for move in self:
            if move._l10n_cr_fe_get_tipo_documento_info():
                move._l10n_cr_fe_generate_and_send()
        return res
```

- [ ] **Step 4: Correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveFeFields,/l10n_cr_fe_crlibre:TestAccountMoveMapping --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: PASS — todos los tests de ambas clases, incluyendo los 4 nuevos, sin regresión en FE/NC/TE (el refactor de `action_post` no cambia su comportamiento para esos tipos: `_l10n_cr_fe_get_tipo_documento_info()` sigue devolviendo lo mismo que antes para `out_invoice`/`out_refund`).

- [ ] **Step 5: Correr también los tests de despacho existentes (regresión ampliada)**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestActionPostFe,/l10n_cr_fe_crlibre:TestTiqueteElectronicoFe,/l10n_cr_fe_crlibre:TestNotaCreditoFe --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: PASS — el cambio de `action_post` no afecta el despacho de FE/NC/TE ya construido.

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py
git commit -m "feat(l10n_cr_fe): campos y resolucion de tipo de documento para Mensaje Receptor"
```

---

### Task 2: Cliente HTTP `gen_xml_mr` y `send_mr`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/crlibre_client.py` (después de `gen_xml_te`, y después de `send_fe`)
- Test: `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`

**Interfaces:**
- Consumes: patrón existente de `gen_xml_fe`/`gen_xml_nc`/`gen_xml_te` y de `send_fe` en `crlibre_client.py`.
- Produces: `CrlibreFeClient.gen_xml_mr(self, params) -> str` (XML decodificado); `CrlibreFeClient.send_mr(self, token, clave, fecha_iso, emisor_tipo, emisor_num, receptor_tipo, receptor_num, consecutivo_receptor, xml_firmado, environment) -> dict` — usados por Task 3.

- [ ] **Step 1: Escribir los tests que fallan**

En `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`, agregar al final de la clase `TestCrlibreClient`:

```python
    def test_gen_xml_mr_decodes_base64(self):
        import base64
        xml = '<MensajeReceptor>ok</MensajeReceptor>'
        payload = {'status': 'ok',
                   'resp': {'clave': '5' * 50, 'xml': base64.b64encode(xml.encode()).decode()}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.gen_xml_mr({'clave': '5' * 50})
        self.assertEqual(result, xml)
        self.assertEqual(m.call_args.kwargs['data']['r'], 'gen_xml_mr')

    def test_send_mr_includes_consecutivo_receptor(self):
        raw_lines = ['HTTP/1.1 202 Accepted', 'Content-Type: application/json', '', '']
        payload = {'status': 'ok', 'resp': {'httpStatus': 202, 'text': raw_lines}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.send_mr(
                token='tok', clave='5' * 50, fecha_iso='2026-07-27T09:00:00-06:00',
                emisor_tipo='01', emisor_num='702320717',
                receptor_tipo='02', receptor_num='3101123456',
                consecutivo_receptor='0' * 20,
                xml_firmado='<MensajeReceptor/>', environment='stag')
        self.assertEqual(result['http_status'], 202)
        called_data = m.call_args.kwargs['data']
        self.assertEqual(called_data['r'], 'sendMensaje')
        self.assertEqual(called_data['consecutivoReceptor'], '0' * 20)
        self.assertEqual(called_data['recp_tipoIdentificacion'], '02')
        self.assertEqual(called_data['recp_numeroIdentificacion'], '3101123456')

    def test_send_mr_error_status_raises(self):
        payload = {'status': 'ok', 'resp': {'httpStatus': 400, 'text': ['HTTP/1.1 400 Bad Request', '']}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)):
            with self.assertRaises(CrlibreApiError):
                self.client.send_mr(
                    token='tok', clave='5' * 50, fecha_iso='2026-07-27T09:00:00-06:00',
                    emisor_tipo='01', emisor_num='702320717',
                    receptor_tipo='02', receptor_num='3101123456',
                    consecutivo_receptor='0' * 20,
                    xml_firmado='<MensajeReceptor/>', environment='stag')
```

- [ ] **Step 2: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons --test-enable --test-tags /l10n_cr_fe_crlibre:TestCrlibreClient.test_gen_xml_mr_decodes_base64 --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: FAIL — `AttributeError: 'CrlibreFeClient' object has no attribute 'gen_xml_mr'`.

- [ ] **Step 3: Implementar `gen_xml_mr` y `send_mr`**

En `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`, después del método `gen_xml_te`, agregar:

```python
    def gen_xml_mr(self, params):
        resp = self._call('genXML', 'gen_xml_mr', params)
        if not isinstance(resp, dict) or not resp.get('xml'):
            raise CrlibreApiError("Respuesta inesperada de 'gen_xml_mr': %s" % resp)
        return base64.b64decode(resp['xml']).decode('utf-8')
```

Y después del método `send_fe`, agregar:

```python
    def send_mr(self, token, clave, fecha_iso, emisor_tipo, emisor_num,
                receptor_tipo, receptor_num, consecutivo_receptor, xml_firmado, environment):
        resp = self._call('send', 'sendMensaje', {
            'token': token,
            'clave': clave,
            'fecha': fecha_iso,
            'emi_tipoIdentificacion': emisor_tipo,
            'emi_numeroIdentificacion': emisor_num,
            'recp_tipoIdentificacion': receptor_tipo,
            'recp_numeroIdentificacion': receptor_num,
            'consecutivoReceptor': consecutivo_receptor,
            'comprobanteXml': base64.b64encode(xml_firmado.encode('utf-8')).decode('ascii'),
            'client_id': self._CLIENT_ID_BY_ENVIRONMENT[environment],
        })
        if not isinstance(resp, dict) or 'httpStatus' not in resp:
            raise CrlibreApiError("Respuesta inesperada de 'send/sendMensaje': %s" % resp)
        http_status = resp['httpStatus']
        if http_status not in (200, 202):
            raise CrlibreApiError("Hacienda rechazó el envío (HTTP %s): %s" % (http_status, resp.get('text')))
        return {'http_status': http_status, 'raw': resp.get('text') or []}
```

- [ ] **Step 4: Correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestCrlibreClient --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: PASS — todos los tests de `TestCrlibreClient`, incluyendo los 3 nuevos.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/crlibre_client.py addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py
git commit -m "feat(l10n_cr_fe): agregar gen_xml_mr y send_mr al cliente HTTP"
```

---

### Task 3: Construir y despachar el Mensaje Receptor (aceptar total/parcial/rechazar)

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py` (nuevo método `_l10n_cr_fe_build_mr_params`, generalizar `_l10n_cr_fe_generate_and_send`, 3 acciones nuevas)
- Create: `addons/l10n_cr_fe_crlibre/tests/test_recepcion_proveedores_fe.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`
- Test: `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`

**Interfaces:**
- Consumes: `_l10n_cr_fe_get_tipo_documento_info()`, `l10n_cr_fe_mr_decision`, `l10n_cr_fe_mr_motivo`, `l10n_cr_fe_proveedor_clave`, `l10n_cr_fe_proveedor_fecha_emision` (Task 1); `client.gen_xml_mr`, `client.send_mr` (Task 2); `_l10n_cr_fe_build_detalles`, `_l10n_cr_fe_build_resumen_totals`, `_l10n_cr_fe_get_config` (ya existentes, reutilizados sin cambios).
- Produces: `_l10n_cr_fe_build_mr_params(self, consecutivo, detalles) -> dict`; `action_l10n_cr_fe_aceptar_total()`, `action_l10n_cr_fe_aceptar_parcial()`, `action_l10n_cr_fe_rechazar()` — usados por Task 5 (botones de vista).

- [ ] **Step 1: Escribir los tests que fallan**

En `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`, agregar al final de la clase `TestAccountMoveMapping`:

```python
    def test_build_mr_params_uses_proveedor_and_own_config(self):
        proveedor = self.env['res.partner'].create({'name': 'Proveedor X', 'vat': '3101987654'})
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'partner_id': proveedor.id,
            'l10n_cr_fe_proveedor_clave': '6' * 50,
            'l10n_cr_fe_proveedor_fecha_emision': '2026-07-20T08:00:00-06:00',
            'l10n_cr_fe_mr_decision': 'aceptado_parcial',
            'l10n_cr_fe_mr_motivo': 'Cantidad distinta a lo facturado',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })
        detalles = bill._l10n_cr_fe_build_detalles()
        params = bill._l10n_cr_fe_build_mr_params('0' * 20, detalles)
        self.assertEqual(params['clave'], '6' * 50)
        self.assertEqual(params['numero_cedula_emisor'], '3101987654')
        self.assertEqual(params['fecha_emision_doc'], '2026-07-20T08:00:00-06:00')
        self.assertEqual(params['mensaje'], '2')
        self.assertEqual(params['detalle_mensaje'], 'Cantidad distinta a lo facturado')
        self.assertEqual(params['total_factura'], 1000.0)
        self.assertEqual(params['numero_cedula_receptor'], '702320717')
        self.assertEqual(params['numero_consecutivo_receptor'], '0' * 20)
```

Crear `addons/l10n_cr_fe_crlibre/tests/test_recepcion_proveedores_fe.py` con:

```python
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRecepcionProveedoresFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas MR Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas MR Test SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de demostración',
            'email': 'demo@frutasdemo.cr',
            'hacienda_username': 'user@stag.comprobanteselectronicos.go.cr',
            'hacienda_password': 'secret',
            'certificate_pin': '1234',
            'certificate_download_code': 'DC_YA_SUBIDO',
        })
        self.partner = self.env['res.partner'].create({'name': 'Proveedor Demo', 'vat': '3101123456'})
        self.product = self.env['product.product'].create({
            'name': 'Producto demo', 'l10n_cr_fe_cabys': '0111101000000'})

    def _create_bill(self):
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_proveedor_clave': '5' * 50,
            'l10n_cr_fe_proveedor_fecha_emision': '2026-07-27T10:00:00-06:00',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })

    def _patch_full_success(self):
        clave = '7' * 50
        return [
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                  return_value={'clave': clave, 'consecutivo': '0' * 20}),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_mr',
                  return_value='<MensajeReceptor>sin firmar</MensajeReceptor>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                  return_value='tok123'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.sign_xml',
                  return_value='<MensajeReceptor>firmada</MensajeReceptor>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.send_mr',
                  return_value={'http_status': 202, 'raw': []}),
        ]

    def test_aceptar_total_sends_cce_and_posts(self):
        bill = self._create_bill()
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            bill.action_l10n_cr_fe_aceptar_total()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
        self.assertEqual(bill.l10n_cr_fe_mr_decision, 'aceptado')
        self.assertEqual(bill.state, 'posted')
        self.assertEqual(bill.l10n_cr_fe_clave, '7' * 50)

    def test_aceptar_parcial_requires_motivo(self):
        bill = self._create_bill()
        with self.assertRaises(UserError):
            bill.action_l10n_cr_fe_aceptar_parcial()

    def test_aceptar_parcial_sends_cpce_and_posts(self):
        bill = self._create_bill()
        bill.l10n_cr_fe_mr_motivo = 'Cantidad recibida distinta a la facturada'
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            bill.action_l10n_cr_fe_aceptar_parcial()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
        self.assertEqual(bill.l10n_cr_fe_mr_decision, 'aceptado_parcial')
        self.assertEqual(bill.state, 'posted')

    def test_rechazar_requires_motivo(self):
        bill = self._create_bill()
        with self.assertRaises(UserError):
            bill.action_l10n_cr_fe_rechazar()

    def test_rechazar_sends_rce_without_posting(self):
        bill = self._create_bill()
        bill.l10n_cr_fe_mr_motivo = 'Factura no corresponde a compra realizada'
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            bill.action_l10n_cr_fe_rechazar()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
        self.assertEqual(bill.l10n_cr_fe_mr_decision, 'rechazado')
        self.assertEqual(bill.state, 'draft')

    def test_tipo_documento_resolves_per_decision(self):
        bill = self._create_bill()
        bill.l10n_cr_fe_mr_decision = 'aceptado'
        self.assertEqual(bill._l10n_cr_fe_get_tipo_documento_info()['clave'], 'CCE')
        bill.l10n_cr_fe_mr_decision = 'aceptado_parcial'
        self.assertEqual(bill._l10n_cr_fe_get_tipo_documento_info()['clave'], 'CPCE')
        bill.l10n_cr_fe_mr_decision = 'rechazado'
        self.assertEqual(bill._l10n_cr_fe_get_tipo_documento_info()['clave'], 'RCE')
```

En `addons/l10n_cr_fe_crlibre/tests/__init__.py`, agregar al final:

```python
from . import test_recepcion_proveedores_fe
```

- [ ] **Step 2: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestRecepcionProveedoresFe.test_aceptar_total_sends_cce_and_posts --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: FAIL — `AttributeError: 'account.move' object has no attribute 'action_l10n_cr_fe_aceptar_total'`.

- [ ] **Step 3: Implementar `_l10n_cr_fe_build_mr_params`, generalizar el despacho, y las 3 acciones**

En `addons/l10n_cr_fe_crlibre/models/account_move.py`, agregar el método nuevo justo después de `_l10n_cr_fe_build_genxml_params` (antes de `_l10n_cr_fe_generate_and_send`):

```python
    def _l10n_cr_fe_build_mr_params(self, consecutivo, detalles):
        self.ensure_one()
        config = self._l10n_cr_fe_get_config()
        resumen = self._l10n_cr_fe_build_resumen_totals(detalles)
        mensaje_codigo = {'aceptado': '1', 'aceptado_parcial': '2', 'rechazado': '3'}[self.l10n_cr_fe_mr_decision]
        return {
            'clave': self.l10n_cr_fe_proveedor_clave,
            'numero_cedula_emisor': (self.partner_id.vat or '').replace('-', '').strip(),
            'fecha_emision_doc': self.l10n_cr_fe_proveedor_fecha_emision,
            'mensaje': mensaje_codigo,
            'detalle_mensaje': self.l10n_cr_fe_mr_motivo or '',
            'monto_total_impuesto': resumen['total_impuestos'],
            'codigo_actividad': config.economic_activity_code,
            'total_factura': resumen['total_comprobante'],
            'numero_cedula_receptor': config.identification_number,
            'numero_consecutivo_receptor': consecutivo,
        }
```

Reemplazar `_l10n_cr_fe_generate_and_send` completo:

```python
    def _l10n_cr_fe_generate_and_send(self):
        self.ensure_one()
        if self.move_type not in L10N_CR_FE_TIPO_DOCUMENTO:
            return
        if not self.partner_id:
            raise UserError(_("El comprobante no tiene cliente (receptor)."))

        client = self.env['l10n_cr.fe.client']
        try:
            if self.move_type == 'out_refund':
                original = self.reversed_entry_id
                if not original or original.l10n_cr_fe_state != 'aceptado':
                    raise UserError(_(
                        "No se puede generar la nota de crédito: la factura original "
                        "aún no ha sido aceptada por Hacienda."))
                if original.l10n_cr_fe_es_tiquete:
                    raise UserError(_(
                        "No se puede generar una nota de crédito sobre un Tiquete "
                        "Electrónico todavía — esta corrección no está soportada."))

            config = self._l10n_cr_fe_get_config()
            download_code = config._l10n_cr_fe_ensure_certificate_uploaded()
            clave_params = self._l10n_cr_fe_build_clave_params()
            clave_res = client.get_clave(clave_params)
            detalles = self._l10n_cr_fe_build_detalles()
            genxml_params = self._l10n_cr_fe_build_genxml_params(
                clave_res['clave'], clave_res['consecutivo'], detalles)
            gen_xml_action = self._l10n_cr_fe_get_tipo_documento_info()['gen_xml_action']
            xml = getattr(client, gen_xml_action)(genxml_params)
            token = client.get_hacienda_token(
                config.hacienda_username, config.hacienda_password, config.environment)
            xml_firmado = client.sign_xml(download_code, config.certificate_pin, xml)
            if self._l10n_cr_fe_get_tipo_documento_info() == L10N_CR_FE_TIPO_DOCUMENTO_TE:
                receptor_tipo, receptor_num = '', ''
            else:
                receptor_tipo = self.partner_id.l10n_cr_fe_identification_type or '01'
                receptor_num = self.partner_id.vat.replace('-', '').strip()
            client.send_fe(
                token=token, clave=clave_res['clave'], fecha_iso=genxml_params['fecha_emision'],
                emisor_tipo=config.identification_type, emisor_num=config.identification_number,
                receptor_tipo=receptor_tipo, receptor_num=receptor_num,
                xml_firmado=xml_firmado, environment=config.environment)
        except (CrlibreApiError, UserError) as exc:
            self.l10n_cr_fe_state = 'error'
            self.message_post(body=_("Error en el flujo de Factura Electrónica: %s") % exc)
            return

        self.write({
            'l10n_cr_fe_clave': clave_res['clave'],
            'l10n_cr_fe_consecutivo': clave_res['consecutivo'],
            'l10n_cr_fe_fecha_emision': genxml_params['fecha_emision'],
            'l10n_cr_fe_xml': xml,
            'l10n_cr_fe_xml_firmado': xml_firmado,
            'l10n_cr_fe_state': 'enviado',
        })
        self.message_post(body=_("Comprobante FE enviado a Hacienda. Clave: %s") % clave_res['clave'])
```

por:

```python
    def _l10n_cr_fe_generate_and_send(self):
        self.ensure_one()
        tipo_doc = self._l10n_cr_fe_get_tipo_documento_info()
        if not tipo_doc:
            return
        if not self.partner_id:
            raise UserError(_("El comprobante no tiene cliente (receptor)."))

        client = self.env['l10n_cr.fe.client']
        try:
            if self.move_type == 'out_refund':
                original = self.reversed_entry_id
                if not original or original.l10n_cr_fe_state != 'aceptado':
                    raise UserError(_(
                        "No se puede generar la nota de crédito: la factura original "
                        "aún no ha sido aceptada por Hacienda."))
                if original.l10n_cr_fe_es_tiquete:
                    raise UserError(_(
                        "No se puede generar una nota de crédito sobre un Tiquete "
                        "Electrónico todavía — esta corrección no está soportada."))

            config = self._l10n_cr_fe_get_config()
            download_code = config._l10n_cr_fe_ensure_certificate_uploaded()
            clave_params = self._l10n_cr_fe_build_clave_params()
            clave_res = client.get_clave(clave_params)
            detalles = self._l10n_cr_fe_build_detalles()

            if self.move_type == 'in_invoice':
                mr_params = self._l10n_cr_fe_build_mr_params(clave_res['consecutivo'], detalles)
                xml = client.gen_xml_mr(mr_params)
                token = client.get_hacienda_token(
                    config.hacienda_username, config.hacienda_password, config.environment)
                xml_firmado = client.sign_xml(download_code, config.certificate_pin, xml)
                fecha = fields.Datetime.context_timestamp(self, datetime.now())
                fecha_iso = fecha.strftime('%Y-%m-%dT%H:%M:%S-06:00')
                client.send_mr(
                    token=token, clave=clave_res['clave'], fecha_iso=fecha_iso,
                    emisor_tipo=config.identification_type, emisor_num=config.identification_number,
                    receptor_tipo=self.partner_id.l10n_cr_fe_identification_type or '01',
                    receptor_num=(self.partner_id.vat or '').replace('-', '').strip(),
                    consecutivo_receptor=clave_res['consecutivo'],
                    xml_firmado=xml_firmado, environment=config.environment)
            else:
                genxml_params = self._l10n_cr_fe_build_genxml_params(
                    clave_res['clave'], clave_res['consecutivo'], detalles)
                gen_xml_action = tipo_doc['gen_xml_action']
                xml = getattr(client, gen_xml_action)(genxml_params)
                token = client.get_hacienda_token(
                    config.hacienda_username, config.hacienda_password, config.environment)
                xml_firmado = client.sign_xml(download_code, config.certificate_pin, xml)
                if tipo_doc == L10N_CR_FE_TIPO_DOCUMENTO_TE:
                    receptor_tipo, receptor_num = '', ''
                else:
                    receptor_tipo = self.partner_id.l10n_cr_fe_identification_type or '01'
                    receptor_num = self.partner_id.vat.replace('-', '').strip()
                fecha_iso = genxml_params['fecha_emision']
                client.send_fe(
                    token=token, clave=clave_res['clave'], fecha_iso=fecha_iso,
                    emisor_tipo=config.identification_type, emisor_num=config.identification_number,
                    receptor_tipo=receptor_tipo, receptor_num=receptor_num,
                    xml_firmado=xml_firmado, environment=config.environment)
        except (CrlibreApiError, UserError) as exc:
            self.l10n_cr_fe_state = 'error'
            self.message_post(body=_("Error en el flujo de Factura Electrónica: %s") % exc)
            return

        self.write({
            'l10n_cr_fe_clave': clave_res['clave'],
            'l10n_cr_fe_consecutivo': clave_res['consecutivo'],
            'l10n_cr_fe_fecha_emision': fecha_iso,
            'l10n_cr_fe_xml': xml,
            'l10n_cr_fe_xml_firmado': xml_firmado,
            'l10n_cr_fe_state': 'enviado',
        })
        self.message_post(body=_("Comprobante FE enviado a Hacienda. Clave: %s") % clave_res['clave'])
```

Nota: el `if self.move_type not in L10N_CR_FE_TIPO_DOCUMENTO: return` original se reemplaza por `tipo_doc = self._l10n_cr_fe_get_tipo_documento_info(); if not tipo_doc: return` — para `in_invoice` sin decisión todavía, `tipo_doc` es `None` (Task 1) y el método no hace nada, igual que hoy para un `move_type` no soportado.

Por último, agregar las 3 acciones nuevas después de `action_l10n_cr_fe_reintentar` (antes de `action_post`):

```python
    def action_l10n_cr_fe_aceptar_total(self):
        self.ensure_one()
        self.l10n_cr_fe_mr_decision = 'aceptado'
        self.action_post()

    def action_l10n_cr_fe_aceptar_parcial(self):
        self.ensure_one()
        if not self.l10n_cr_fe_mr_motivo:
            raise UserError(_("Debes indicar el motivo de la aceptación parcial."))
        self.l10n_cr_fe_mr_decision = 'aceptado_parcial'
        self.action_post()

    def action_l10n_cr_fe_rechazar(self):
        self.ensure_one()
        if not self.l10n_cr_fe_mr_motivo:
            raise UserError(_("Debes indicar el motivo del rechazo."))
        self.l10n_cr_fe_mr_decision = 'rechazado'
        self._l10n_cr_fe_generate_and_send()
```

- [ ] **Step 4: Correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestRecepcionProveedoresFe,/l10n_cr_fe_crlibre:TestAccountMoveMapping --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: PASS — todos los tests de ambas clases.

- [ ] **Step 5: Correr la suite completa del módulo para confirmar que no hay regresiones en FE/NC/TE**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: `0 failed, 0 error(s)` en la línea final `odoo.tests.result` — el reescrito de `_l10n_cr_fe_generate_and_send` preserva exactamente el camino FE/NC/TE (misma secuencia de llamadas, solo dentro de un `else`).

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py addons/l10n_cr_fe_crlibre/tests/test_recepcion_proveedores_fe.py addons/l10n_cr_fe_crlibre/tests/__init__.py
git commit -m "feat(l10n_cr_fe): construir y despachar el Mensaje Receptor (aceptar/rechazar)"
```

---

### Task 4: Asistente para cargar la factura del proveedor

**Files:**
- Create: `addons/l10n_cr_fe_crlibre/wizards/proveedor_upload.py`
- Modify: `addons/l10n_cr_fe_crlibre/wizards/__init__.py`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_proveedor_upload.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`

**Interfaces:**
- Consumes: `l10n_cr_fe_proveedor_clave`/`l10n_cr_fe_proveedor_fecha_emision` (Task 1); `product.l10n_cr_fe_cabys` (existente); `res.partner.vat` (existente).
- Produces: modelo `l10n_cr.fe.proveedor.upload` (`TransientModel`) con método `action_procesar(self) -> dict` (acción de ventana devolviendo la factura creada) — usado por Task 5 (vista del asistente).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `addons/l10n_cr_fe_crlibre/tests/test_proveedor_upload.py` con:

```python
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

    def test_invalid_xml_raises(self):
        with self.assertRaises(UserError):
            self._upload('esto no es xml')
```

En `addons/l10n_cr_fe_crlibre/tests/__init__.py`, agregar al final:

```python
from . import test_proveedor_upload
```

- [ ] **Step 2: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestProveedorUpload.test_parses_clave_and_fecha_emision --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: FAIL — `KeyError: 'l10n_cr.fe.proveedor.upload'` (el modelo todavía no existe).

- [ ] **Step 3: Implementar el asistente**

Crear `addons/l10n_cr_fe_crlibre/wizards/proveedor_upload.py`:

```python
import base64
import xml.etree.ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import UserError


class L10nCrFeProveedorUpload(models.TransientModel):
    _name = 'l10n_cr.fe.proveedor.upload'
    _description = "Cargar factura electrónica de un proveedor"

    xml_file = fields.Binary(string="Archivo XML", required=True)
    xml_filename = fields.Char(string="Nombre del archivo")

    def _find_text(self, node, tag):
        el = node.find('.//{*}%s' % tag)
        return el.text.strip() if el is not None and el.text else ''

    def _find_product(self, cabys):
        if not cabys:
            return self.env['product.product']
        return self.env['product.product'].search([('l10n_cr_fe_cabys', '=', cabys)], limit=1)

    def _find_tax(self, tarifa_percent):
        if not tarifa_percent:
            return self.env['account.tax']
        return self.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'),
            ('amount', '=', tarifa_percent),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

    def action_procesar(self):
        self.ensure_one()
        try:
            root = ET.fromstring(base64.b64decode(self.xml_file))
        except ET.ParseError:
            raise UserError(_("El archivo no es un XML válido."))

        clave = self._find_text(root, 'Clave')
        fecha_emision = self._find_text(root, 'FechaEmision')
        emisor_el = root.find('.//{*}Emisor')
        if emisor_el is None or not clave:
            raise UserError(_(
                "El XML no tiene los datos mínimos de un comprobante electrónico (Clave/Emisor)."))
        emisor_nombre = self._find_text(emisor_el, 'Nombre')
        emisor_cedula = self._find_text(emisor_el, 'Numero')
        emisor_email = self._find_text(emisor_el, 'CorreoElectronico')
        if not emisor_cedula:
            raise UserError(_("El XML no tiene la identificación del emisor."))

        partner = self.env['res.partner'].search([('vat', '=', emisor_cedula)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': emisor_nombre or emisor_cedula,
                'vat': emisor_cedula,
                'email': emisor_email or False,
                'company_type': 'company',
            })

        invoice_lines = []
        for linea in root.findall('.//{*}LineaDetalle'):
            cabys = self._find_text(linea, 'CodigoCABYS')
            cantidad = float(self._find_text(linea, 'Cantidad') or '0')
            precio_unitario = float(self._find_text(linea, 'PrecioUnitario') or '0')
            detalle = self._find_text(linea, 'Detalle')
            tarifa_text = self._find_text(linea, 'Tarifa')
            tarifa_percent = float(tarifa_text) if tarifa_text else 0.0
            product = self._find_product(cabys)
            tax = self._find_tax(tarifa_percent)
            invoice_lines.append((0, 0, {
                'product_id': product.id or False,
                'quantity': cantidad,
                'price_unit': precio_unitario,
                'name': detalle or (product.display_name if product else _("Completar producto")),
                'tax_ids': [(6, 0, tax.ids)],
            }))

        if not invoice_lines:
            raise UserError(_("El XML no tiene líneas de detalle."))

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'l10n_cr_fe_proveedor_clave': clave,
            'l10n_cr_fe_proveedor_fecha_emision': fecha_emision,
            'invoice_line_ids': invoice_lines,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }
```

En `addons/l10n_cr_fe_crlibre/wizards/__init__.py`, agregar al final:

```python
from . import proveedor_upload
```

- [ ] **Step 4: Correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestProveedorUpload --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: PASS — los 6 tests de `TestProveedorUpload`.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/wizards/proveedor_upload.py addons/l10n_cr_fe_crlibre/wizards/__init__.py addons/l10n_cr_fe_crlibre/tests/test_proveedor_upload.py addons/l10n_cr_fe_crlibre/tests/__init__.py
git commit -m "feat(l10n_cr_fe): asistente para cargar factura de proveedor desde XML"
```

---

### Task 5: Vistas, permisos, y menú

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`
- Create: `addons/l10n_cr_fe_crlibre/views/proveedor_upload_views.xml`
- Modify: `addons/l10n_cr_fe_crlibre/security/ir.model.access.csv`
- Modify: `addons/l10n_cr_fe_crlibre/__manifest__.py`

**Interfaces:**
- Consumes: `l10n_cr_fe_mr_decision`, `l10n_cr_fe_mr_motivo`, `l10n_cr_fe_proveedor_clave`, `l10n_cr_fe_proveedor_fecha_emision` (Task 1); `action_l10n_cr_fe_aceptar_total`, `action_l10n_cr_fe_aceptar_parcial`, `action_l10n_cr_fe_rechazar` (Task 3); modelo `l10n_cr.fe.proveedor.upload` y `action_procesar` (Task 4).
- Produces: UI completa — sin interfaz nueva para tareas futuras.

- [ ] **Step 1: Actualizar la vista del formulario de factura**

En `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`, reemplazar el archivo completo por:

```xml
<odoo>
    <record id="view_move_form_l10n_cr_fe" model="ir.ui.view">
        <field name="name">account.move.form.l10n.cr.fe</field>
        <field name="model">account.move</field>
        <field name="inherit_id" ref="account.view_move_form"/>
        <field name="arch" type="xml">
            <xpath expr="//header" position="inside">
                <button name="action_l10n_cr_fe_consultar_estado"
                        string="Consultar estado FE"
                        type="object" class="btn-secondary"
                        invisible="l10n_cr_fe_state != 'enviado'"/>
                <button name="action_l10n_cr_fe_reintentar"
                        string="Reintentar envío FE"
                        type="object" class="btn-primary"
                        invisible="l10n_cr_fe_state != 'rechazado'"/>
                <button name="action_l10n_cr_fe_aceptar_total"
                        string="Aceptar total"
                        type="object" class="btn-primary"
                        invisible="move_type != 'in_invoice' or not l10n_cr_fe_proveedor_clave or l10n_cr_fe_mr_decision"/>
                <button name="action_l10n_cr_fe_aceptar_parcial"
                        string="Aceptar parcial"
                        type="object" class="btn-secondary"
                        invisible="move_type != 'in_invoice' or not l10n_cr_fe_proveedor_clave or l10n_cr_fe_mr_decision"/>
                <button name="action_l10n_cr_fe_rechazar"
                        string="Rechazar"
                        type="object" class="btn-secondary"
                        invisible="move_type != 'in_invoice' or not l10n_cr_fe_proveedor_clave or l10n_cr_fe_mr_decision"/>
                <field name="l10n_cr_fe_state" widget="statusbar"
                       invisible="move_type not in ('out_invoice', 'out_refund', 'in_invoice')"/>
            </xpath>
            <xpath expr="//notebook" position="inside">
                <page string="Factura Electrónica CR"
                      invisible="move_type not in ('out_invoice', 'out_refund', 'in_invoice')">
                    <group>
                        <field name="l10n_cr_fe_clave"/>
                        <field name="l10n_cr_fe_consecutivo"/>
                        <field name="l10n_cr_fe_es_tiquete" invisible="move_type != 'out_invoice'"/>
                        <field name="l10n_cr_fe_motivo_rechazo" invisible="l10n_cr_fe_state != 'rechazado'"/>
                        <field name="l10n_cr_fe_motivo" invisible="move_type != 'out_refund'"/>
                        <field name="l10n_cr_fe_codigo_referencia" invisible="move_type != 'out_refund'"/>
                        <field name="l10n_cr_fe_razon" invisible="move_type != 'out_refund'"/>
                        <field name="l10n_cr_fe_proveedor_clave" invisible="move_type != 'in_invoice'"/>
                        <field name="l10n_cr_fe_proveedor_fecha_emision" invisible="move_type != 'in_invoice'"/>
                        <field name="l10n_cr_fe_mr_decision" invisible="move_type != 'in_invoice'"/>
                        <field name="l10n_cr_fe_mr_motivo" invisible="move_type != 'in_invoice'"/>
                    </group>
                    <field name="l10n_cr_fe_xml"/>
                    <field name="l10n_cr_fe_xml_firmado"/>
                    <field name="l10n_cr_fe_respuesta_xml"/>
                </page>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 2: Crear la vista y el menú del asistente**

Crear `addons/l10n_cr_fe_crlibre/views/proveedor_upload_views.xml`:

```xml
<odoo>
    <record id="view_l10n_cr_fe_proveedor_upload_form" model="ir.ui.view">
        <field name="name">l10n_cr.fe.proveedor.upload.form</field>
        <field name="model">l10n_cr.fe.proveedor.upload</field>
        <field name="arch" type="xml">
            <form string="Cargar factura de proveedor">
                <group>
                    <field name="xml_file" filename="xml_filename"/>
                    <field name="xml_filename" invisible="1"/>
                </group>
                <footer>
                    <button name="action_procesar" string="Procesar" type="object" class="btn-primary"/>
                    <button string="Cancelar" special="cancel" class="btn-secondary"/>
                </footer>
            </form>
        </field>
    </record>
    <record id="action_l10n_cr_fe_proveedor_upload" model="ir.actions.act_window">
        <field name="name">Cargar factura de proveedor</field>
        <field name="res_model">l10n_cr.fe.proveedor.upload</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>
    <menuitem id="menu_l10n_cr_fe_proveedor_upload"
              name="Cargar factura de proveedor (FE)"
              parent="account.menu_finance_payables"
              action="action_l10n_cr_fe_proveedor_upload"
              sequence="15"/>
</odoo>
```

- [ ] **Step 3: Agregar el permiso de acceso al asistente**

En `addons/l10n_cr_fe_crlibre/security/ir.model.access.csv`, agregar al final:

```csv
access_l10n_cr_fe_proveedor_upload,l10n_cr.fe.proveedor.upload,model_l10n_cr_fe_proveedor_upload,account.group_account_invoice,1,1,1,1
```

- [ ] **Step 4: Registrar el archivo de vista nuevo en el manifest**

En `addons/l10n_cr_fe_crlibre/__manifest__.py`, reemplazar:

```python
    'data': [
        'data/system_params.xml',
        'security/l10n_cr_fe_security.xml',
        'security/ir.model.access.csv',
        'views/fe_config_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'views/account_move_reversal_views.xml',
        'data/mail_template.xml',
    ],
```

por:

```python
    'data': [
        'data/system_params.xml',
        'security/l10n_cr_fe_security.xml',
        'security/ir.model.access.csv',
        'views/fe_config_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'views/account_move_reversal_views.xml',
        'views/proveedor_upload_views.xml',
        'data/mail_template.xml',
    ],
```

- [ ] **Step 5: Correr la suite completa para confirmar que el módulo carga sin errores y no hay regresiones**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: `0 failed, 0 error(s)` en la línea final `odoo.tests.result`. Si hay un error de XML/vista inválida (referencia rota, campo inexistente), el log de `-u` lo muestra durante la carga de módulos, antes de llegar a los tests — revisar ahí primero si algo falla en este paso.

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/views/account_move_views.xml addons/l10n_cr_fe_crlibre/views/proveedor_upload_views.xml addons/l10n_cr_fe_crlibre/security/ir.model.access.csv addons/l10n_cr_fe_crlibre/__manifest__.py
git commit -m "feat(l10n_cr_fe): vistas, botones y menu para recepcion de comprobantes de proveedores"
```

---

## Verificación manual pendiente (fuera de las tareas automatizadas)

Ninguna tarea de este plan corre un navegador. Después de que las 5 tareas estén mergeadas, verificar en la UI: subir un XML real de una factura de proveedor (o el de prueba del Task 4) desde **Proveedores → Cargar factura de proveedor (FE)**, confirmar que arma el borrador correctamente, y probar los 3 botones ("Aceptar total", "Aceptar parcial" editando una línea antes, "Rechazar" con motivo) contra el sandbox real de Hacienda — confirmando que cada uno genera el tipo de documento correcto (`CCE`/`CPCE`/`RCE`) y que "Consultar estado FE" funciona igual que para Factura/Nota de Crédito/Tiquete.
