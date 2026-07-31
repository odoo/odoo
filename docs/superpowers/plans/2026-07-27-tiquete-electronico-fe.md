# Tiquete Electrónico desde factura de consumidor final — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir emitir un Tiquete Electrónico (Hacienda v4.4, `tipoDocumento=04`) desde una factura normal de Odoo (`out_invoice`), marcada manualmente como "consumidor final", reutilizando el flujo de generación/envío FE ya existente.

**Architecture:** Generaliza el despacho por tipo de documento que ya existe en `l10n_cr_fe_crlibre` (`L10N_CR_FE_TIPO_DOCUMENTO`, usado hoy para Factura y Nota de Crédito) para un tercer caso que comparte `move_type='out_invoice'` con Factura pero se distingue por un campo booleano nuevo. Un método de resolución centralizado (`_l10n_cr_fe_get_tipo_documento_info`) reemplaza los accesos directos al diccionario por `move_type`.

**Tech Stack:** Odoo 19 ORM (Python), vistas XML, `odoo.tests.common.TransactionCase`, cliente HTTP propio (`crlibre_client.py`) contra la API_Hacienda (CRLibre).

## Global Constraints

- No se modifica ningún archivo bajo `odoo/` ni `addons/account/` — solo `addons/l10n_cr_fe_crlibre/`.
- El disparador de Tiquete es manual (campo booleano en la factura, marcado por el usuario) — no hay detección automática por cliente.
- Cuando el Tiquete está marcado, el bloque `Receptor` se omite por completo del XML (`omitir_receptor: 'true'`) sin importar qué contacto tenga la factura — no se envía nombre ni identificación a Hacienda.
- El consecutivo de Tiquete usa su propio código de tipo de documento (`'04'`), independiente de Factura (`'01'`) y Nota de Crédito (`'03'`), reutilizando el mecanismo de secuencias por tipo de documento ya existente en `fe_config.py` sin cambios.
- Corregir un Tiquete con Nota de Crédito no está soportado en este plan — debe fallar con un `UserError` claro, no generar un documento inválido.
- No se toca el módulo POS de Odoo ni se agregan campos de "consumidor final por defecto" en `res.partner`.

---

### Task 1: Campo `l10n_cr_fe_es_tiquete` + resolución de tipo de documento + vista

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py:26-29` (constante nueva), `:67-91` (campo nuevo), `:93-95` (helper nuevo después de `_l10n_cr_fe_get_config`), `:138-151` (`_l10n_cr_fe_build_clave_params` usa el helper)
- Modify: `addons/l10n_cr_fe_crlibre/views/account_move_views.xml:22-29`
- Test: `addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py`, `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`

**Interfaces:**
- Consumes: `L10N_CR_FE_TIPO_DOCUMENTO` (dict existente, sin cambios), campo `move_type` nativo de `account.move`.
- Produces: campo `l10n_cr_fe_es_tiquete` (Boolean, default `False`); constante `L10N_CR_FE_TIPO_DOCUMENTO_TE` (dict `{'clave': 'TE', 'consecutivo_codigo': '04', 'gen_xml_action': 'gen_xml_te'}`); método `_l10n_cr_fe_get_tipo_documento_info(self) -> dict | None` — usado por Task 2 y por `_l10n_cr_fe_build_clave_params`.

- [ ] **Step 1: Escribir los tests que fallan**

En `addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py`, agregar al final de la clase `TestAccountMoveFeFields`:

```python
    def test_es_tiquete_field_defaults_false(self):
        partner = self.env['res.partner'].create({'name': 'Cliente Tiquete Fields'})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
        })
        self.assertFalse(invoice.l10n_cr_fe_es_tiquete)

    def test_tipo_documento_te_constant(self):
        from odoo.addons.l10n_cr_fe_crlibre.models.account_move import L10N_CR_FE_TIPO_DOCUMENTO_TE
        self.assertEqual(L10N_CR_FE_TIPO_DOCUMENTO_TE, {
            'clave': 'TE', 'consecutivo_codigo': '04', 'gen_xml_action': 'gen_xml_te',
        })
```

En `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`, agregar al final de la clase `TestAccountMoveMapping`:

```python
    def test_build_clave_params_tiquete_uses_te(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_es_tiquete': True,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })
        params = invoice._l10n_cr_fe_build_clave_params()
        self.assertEqual(params['tipoDocumento'], 'TE')
        self.assertEqual(len(params['consecutivo']), 10)

    def test_get_tipo_documento_info_returns_fe_when_not_tiquete(self):
        info = self.invoice._l10n_cr_fe_get_tipo_documento_info()
        self.assertEqual(info['clave'], 'FE')
```

- [ ] **Step 2: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveFeFields.test_tipo_documento_te_constant --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: FAIL — `ImportError: cannot import name 'L10N_CR_FE_TIPO_DOCUMENTO_TE'`.

- [ ] **Step 3: Agregar la constante, el campo y el helper**

En `addons/l10n_cr_fe_crlibre/models/account_move.py`, reemplazar (líneas 26-29):

```python
L10N_CR_FE_TIPO_DOCUMENTO = {
    'out_invoice': {'clave': 'FE', 'consecutivo_codigo': '01', 'gen_xml_action': 'gen_xml_fe'},
    'out_refund': {'clave': 'NC', 'consecutivo_codigo': '03', 'gen_xml_action': 'gen_xml_nc'},
}
```

por:

```python
L10N_CR_FE_TIPO_DOCUMENTO = {
    'out_invoice': {'clave': 'FE', 'consecutivo_codigo': '01', 'gen_xml_action': 'gen_xml_fe'},
    'out_refund': {'clave': 'NC', 'consecutivo_codigo': '03', 'gen_xml_action': 'gen_xml_nc'},
}

# Tiquete Electronico (TE): comparte move_type 'out_invoice' con Factura, asi que
# no puede tener su propia entrada en L10N_CR_FE_TIPO_DOCUMENTO (indexado por
# move_type). Se resuelve aparte en _l10n_cr_fe_get_tipo_documento_info().
L10N_CR_FE_TIPO_DOCUMENTO_TE = {'clave': 'TE', 'consecutivo_codigo': '04', 'gen_xml_action': 'gen_xml_te'}
```

Luego, en la declaración de campos de la clase `AccountMove` (después de `l10n_cr_fe_razon`, línea 81, antes de `l10n_cr_fe_state`), agregar:

```python
    l10n_cr_fe_es_tiquete = fields.Boolean(
        string="Consumidor final (Tiquete Electrónico)",
        help="Si está marcado, este comprobante se emite ante Hacienda como Tiquete "
             "Electrónico (sin identificar al receptor) en vez de Factura Electrónica.")
```

Luego, justo después del método `_l10n_cr_fe_get_config` (líneas 93-95), agregar:

```python
    def _l10n_cr_fe_get_tipo_documento_info(self):
        self.ensure_one()
        if self.move_type == 'out_invoice' and self.l10n_cr_fe_es_tiquete:
            return L10N_CR_FE_TIPO_DOCUMENTO_TE
        return L10N_CR_FE_TIPO_DOCUMENTO.get(self.move_type)
```

Por último, en `_l10n_cr_fe_build_clave_params`, reemplazar:

```python
        tipo_doc = L10N_CR_FE_TIPO_DOCUMENTO[self.move_type]
```

por:

```python
        tipo_doc = self._l10n_cr_fe_get_tipo_documento_info()
```

- [ ] **Step 4: Agregar el campo a la vista**

En `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`, reemplazar:

```xml
                    <group>
                        <field name="l10n_cr_fe_clave"/>
                        <field name="l10n_cr_fe_consecutivo"/>
                        <field name="l10n_cr_fe_motivo_rechazo" invisible="l10n_cr_fe_state != 'rechazado'"/>
```

por:

```xml
                    <group>
                        <field name="l10n_cr_fe_clave"/>
                        <field name="l10n_cr_fe_consecutivo"/>
                        <field name="l10n_cr_fe_es_tiquete" invisible="move_type != 'out_invoice'"/>
                        <field name="l10n_cr_fe_motivo_rechazo" invisible="l10n_cr_fe_state != 'rechazado'"/>
```

- [ ] **Step 5: Correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveFeFields,/l10n_cr_fe_crlibre:TestAccountMoveMapping --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: PASS — todos los tests de ambas clases, incluyendo los 4 nuevos, sin regresión en los preexistentes (confirma que Factura y Nota de Crédito siguen resolviendo `tipoDocumento` igual que antes).

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/views/account_move_views.xml addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py
git commit -m "feat(l10n_cr_fe): campo y resolucion de tipo de documento para Tiquete Electronico"
```

---

### Task 2: Cliente HTTP `gen_xml_te` + despacho end-to-end

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/crlibre_client.py` (después de `gen_xml_nc`)
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py:258` (`_l10n_cr_fe_generate_and_send` usa el helper de Task 1)
- Create: `addons/l10n_cr_fe_crlibre/tests/test_tiquete_electronico_fe.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`
- Test: `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`

**Interfaces:**
- Consumes: `_l10n_cr_fe_get_tipo_documento_info()` de Task 1; patrón de `gen_xml_fe`/`gen_xml_nc` en `crlibre_client.py`.
- Produces: método `CrlibreFeClient.gen_xml_te(self, params) -> str` (XML decodificado); helper de test `_create_tiquete()` y `_patch_full_success()` en `TestTiqueteElectronicoFe`, reutilizados por Tasks 3 y 4.

- [ ] **Step 1: Escribir los tests que fallan**

En `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`, agregar al final de la clase `TestCrlibreClient`:

```python
    def test_gen_xml_te_decodes_base64(self):
        import base64
        xml = '<TiqueteElectronico>ok</TiqueteElectronico>'
        payload = {'status': 'ok',
                   'resp': {'clave': '5' * 50, 'xml': base64.b64encode(xml.encode()).decode()}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.gen_xml_te({'clave': '5' * 50})
        self.assertEqual(result, xml)
        self.assertEqual(m.call_args.kwargs['data']['r'], 'gen_xml_te')
```

Crear `addons/l10n_cr_fe_crlibre/tests/test_tiquete_electronico_fe.py` con:

```python
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestTiqueteElectronicoFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas TE Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas TE Test SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de demostración',
            'email': 'demo@frutasdemo.cr',
            'hacienda_username': 'user@stag.comprobanteselectronicos.go.cr',
            'hacienda_password': 'secret',
            'certificate_pin': '1234',
            'certificate_download_code': 'DC_YA_SUBIDO',
        })
        self.partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        self.product = self.env['product.product'].create({
            'name': 'Producto demo', 'l10n_cr_fe_cabys': '0111101000000'})

    def _create_tiquete(self):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_es_tiquete': True,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })

    def _patch_full_success(self):
        clave = '8' * 50
        return [
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                  return_value={'clave': clave, 'consecutivo': '0' * 20}),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_te',
                  return_value='<TiqueteElectronico>sin firmar</TiqueteElectronico>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                  return_value='tok123'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.sign_xml',
                  return_value='<TiqueteElectronico>firmada</TiqueteElectronico>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.send_fe',
                  return_value={'http_status': 202, 'raw': []}),
        ]

    def test_action_post_sends_tiquete_using_gen_xml_te(self):
        tiquete = self._create_tiquete()
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            tiquete.action_post()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(tiquete.l10n_cr_fe_state, 'enviado')
        self.assertEqual(tiquete.l10n_cr_fe_clave, '8' * 50)
        self.assertIn('firmada', tiquete.l10n_cr_fe_xml_firmado)
```

En `addons/l10n_cr_fe_crlibre/tests/__init__.py`, agregar al final:

```python
from . import test_tiquete_electronico_fe
```

- [ ] **Step 2: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestTiqueteElectronicoFe.test_action_post_sends_tiquete_using_gen_xml_te --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: FAIL — `AttributeError: type object 'CrlibreFeClient' has no attribute 'gen_xml_te'` (el patch no encuentra el método a interceptar).

- [ ] **Step 3: Implementar `gen_xml_te` y usar el helper en el despacho**

En `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`, después del método `gen_xml_nc`, agregar:

```python
    def gen_xml_te(self, params):
        resp = self._call('genXML', 'gen_xml_te', params)
        if not isinstance(resp, dict) or not resp.get('xml'):
            raise CrlibreApiError("Respuesta inesperada de 'gen_xml_te': %s" % resp)
        return base64.b64decode(resp['xml']).decode('utf-8')
```

En `addons/l10n_cr_fe_crlibre/models/account_move.py`, dentro de `_l10n_cr_fe_generate_and_send`, reemplazar:

```python
            gen_xml_action = L10N_CR_FE_TIPO_DOCUMENTO[self.move_type]['gen_xml_action']
```

por:

```python
            gen_xml_action = self._l10n_cr_fe_get_tipo_documento_info()['gen_xml_action']
```

- [ ] **Step 4: Correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestCrlibreClient,/l10n_cr_fe_crlibre:TestTiqueteElectronicoFe --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: PASS — todos los tests de ambas clases.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/crlibre_client.py addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py addons/l10n_cr_fe_crlibre/tests/test_tiquete_electronico_fe.py addons/l10n_cr_fe_crlibre/tests/__init__.py
git commit -m "feat(l10n_cr_fe): agregar gen_xml_te y despachar Tiquete Electronico end-to-end"
```

---

### Task 3: Receptor omitido y sin exigir cédula para Tiquete

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py:187-233` (`_l10n_cr_fe_build_genxml_params`), `:263-268` (llamada a `send_fe` en `_l10n_cr_fe_generate_and_send`)
- Test: `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`, `addons/l10n_cr_fe_crlibre/tests/test_tiquete_electronico_fe.py`

**Interfaces:**
- Consumes: `l10n_cr_fe_es_tiquete` (Task 1), `_create_tiquete()`/`_patch_full_success()` (Task 2).
- Produces: comportamiento observable — `_l10n_cr_fe_build_genxml_params` no exige `partner_id.vat` ni agrega claves `receptor_*` cuando `l10n_cr_fe_es_tiquete` es `True`; agrega `'omitir_receptor': 'true'` en su lugar.

- [ ] **Step 1: Escribir los tests que fallan**

En `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`, agregar al final de la clase `TestAccountMoveMapping`:

```python
    def test_build_genxml_params_tiquete_without_vat_omits_receptor(self):
        self.partner.vat = False
        self.invoice.l10n_cr_fe_es_tiquete = True
        detalles = self.invoice._l10n_cr_fe_build_detalles()
        params = self.invoice._l10n_cr_fe_build_genxml_params('9' * 50, '0' * 20, detalles)
        self.assertEqual(params['omitir_receptor'], 'true')
        self.assertNotIn('receptor_nombre', params)
        self.assertNotIn('receptor_tipo_identif', params)
        self.assertNotIn('receptor_num_identif', params)
```

En `addons/l10n_cr_fe_crlibre/tests/test_tiquete_electronico_fe.py`, agregar dentro de `TestTiqueteElectronicoFe`:

```python
    def test_action_post_sends_tiquete_without_partner_vat(self):
        self.partner.vat = False
        tiquete = self._create_tiquete()
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            tiquete.action_post()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(tiquete.l10n_cr_fe_state, 'enviado')
```

- [ ] **Step 2: Correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveMapping.test_build_genxml_params_tiquete_without_vat_omits_receptor --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: FAIL — `UserError: El cliente 'Cliente Demo' no tiene cédula/identificación configurada.` (el guardia actual no distingue Tiquete).

- [ ] **Step 3: Implementar la omisión del receptor**

En `addons/l10n_cr_fe_crlibre/models/account_move.py`, dentro de `_l10n_cr_fe_build_genxml_params`, reemplazar:

```python
        if not self.partner_id.vat:
            raise UserError(
                _("El cliente '%s' no tiene cédula/identificación configurada. Hacienda "
                  "rechaza los comprobantes si el receptor no tiene un número de "
                  "identificación válido.") % self.partner_id.name)
```

por:

```python
        if not self.l10n_cr_fe_es_tiquete and not self.partner_id.vat:
            raise UserError(
                _("El cliente '%s' no tiene cédula/identificación configurada. Hacienda "
                  "rechaza los comprobantes si el receptor no tiene un número de "
                  "identificación válido.") % self.partner_id.name)
```

Luego, reemplazar el diccionario `params` completo (desde `resumen = self._l10n_cr_fe_build_resumen_totals(detalles)` hasta el `}` que cierra el diccionario), que hoy es:

```python
        resumen = self._l10n_cr_fe_build_resumen_totals(detalles)
        medios_pago = [{'tipoMedioPago': '01', 'totalMedioPago': resumen['total_comprobante']}]
        params = {
            'clave': clave,
            'proveedor_sistemas': config.identification_number,
            'codigo_actividad_emisor': config.economic_activity_code,
            'consecutivo': consecutivo,
            'fecha_emision': fecha.strftime('%Y-%m-%dT%H:%M:%S-06:00'),
            'emisor_nombre': config.legal_name,
            'emisor_tipo_identif': config.identification_type,
            'emisor_num_identif': config.identification_number,
            'emisor_provincia': config.province,
            'emisor_canton': config.canton,
            'emisor_distrito': config.district,
            'emisor_otras_senas': config.address_detail,
            'emisor_email': config.email,
            'receptor_nombre': self.partner_id.name or '',
            'receptor_tipo_identif': self.partner_id.l10n_cr_fe_identification_type or '01',
            'receptor_num_identif': self.partner_id.vat.replace('-', '').strip(),
            'condicion_venta': '01',
            'medios_pago': json.dumps(medios_pago),
            'cod_moneda': self.currency_id.name or 'CRC',
            'tipo_cambio': '1',
            'detalles': json.dumps(detalles),
            **resumen,
        }
```

por la versión sin las tres claves `receptor_*` fijas, agregándolas condicionalmente después:

```python
        resumen = self._l10n_cr_fe_build_resumen_totals(detalles)
        medios_pago = [{'tipoMedioPago': '01', 'totalMedioPago': resumen['total_comprobante']}]
        params = {
            'clave': clave,
            'proveedor_sistemas': config.identification_number,
            'codigo_actividad_emisor': config.economic_activity_code,
            'consecutivo': consecutivo,
            'fecha_emision': fecha.strftime('%Y-%m-%dT%H:%M:%S-06:00'),
            'emisor_nombre': config.legal_name,
            'emisor_tipo_identif': config.identification_type,
            'emisor_num_identif': config.identification_number,
            'emisor_provincia': config.province,
            'emisor_canton': config.canton,
            'emisor_distrito': config.district,
            'emisor_otras_senas': config.address_detail,
            'emisor_email': config.email,
            'condicion_venta': '01',
            'medios_pago': json.dumps(medios_pago),
            'cod_moneda': self.currency_id.name or 'CRC',
            'tipo_cambio': '1',
            'detalles': json.dumps(detalles),
            **resumen,
        }
        if self.l10n_cr_fe_es_tiquete:
            params['omitir_receptor'] = 'true'
        else:
            params['receptor_nombre'] = self.partner_id.name or ''
            params['receptor_tipo_identif'] = self.partner_id.l10n_cr_fe_identification_type or '01'
            params['receptor_num_identif'] = self.partner_id.vat.replace('-', '').strip()
```

(El resto del método —el bloque `if self.move_type == 'out_refund': ...` y el `return params`— no cambia.)

Por último, en `_l10n_cr_fe_generate_and_send`, reemplazar:

```python
            client.send_fe(
                token=token, clave=clave_res['clave'], fecha_iso=genxml_params['fecha_emision'],
                emisor_tipo=config.identification_type, emisor_num=config.identification_number,
                receptor_tipo=self.partner_id.l10n_cr_fe_identification_type or '01',
                receptor_num=self.partner_id.vat.replace('-', '').strip(),
                xml_firmado=xml_firmado, environment=config.environment)
```

por:

```python
            if self.l10n_cr_fe_es_tiquete:
                receptor_tipo, receptor_num = '', ''
            else:
                receptor_tipo = self.partner_id.l10n_cr_fe_identification_type or '01'
                receptor_num = self.partner_id.vat.replace('-', '').strip()
            client.send_fe(
                token=token, clave=clave_res['clave'], fecha_iso=genxml_params['fecha_emision'],
                emisor_tipo=config.identification_type, emisor_num=config.identification_number,
                receptor_tipo=receptor_tipo, receptor_num=receptor_num,
                xml_firmado=xml_firmado, environment=config.environment)
```

- [ ] **Step 4: Correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveMapping,/l10n_cr_fe_crlibre:TestTiqueteElectronicoFe --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: PASS — todos los tests de ambas clases, incluyendo `test_build_genxml_params_without_receptor_vat_raises` (preexistente, confirma que una Factura normal —`l10n_cr_fe_es_tiquete=False`— sigue exigiendo cédula sin regresión).

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py addons/l10n_cr_fe_crlibre/tests/test_tiquete_electronico_fe.py
git commit -m "feat(l10n_cr_fe): omitir receptor y no exigir cedula para Tiquete Electronico"
```

---

### Task 4: Candado — Nota de Crédito sobre un Tiquete no soportada

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py:244-249` (`_l10n_cr_fe_generate_and_send`)
- Test: `addons/l10n_cr_fe_crlibre/tests/test_tiquete_electronico_fe.py`

**Interfaces:**
- Consumes: `l10n_cr_fe_es_tiquete` (Task 1), `_create_tiquete()` (Task 2).
- Produces: comportamiento observable — generar una Nota de Crédito (`out_refund`) cuyo `reversed_entry_id` tiene `l10n_cr_fe_es_tiquete=True` falla con `UserError`, dejando la NC en `l10n_cr_fe_state='error'` sin bloquear el asiento contable.

- [ ] **Step 1: Escribir el test que falla**

En `addons/l10n_cr_fe_crlibre/tests/test_tiquete_electronico_fe.py`, agregar dentro de `TestTiqueteElectronicoFe`:

```python
    def test_action_post_blocks_credit_note_on_tiquete_original(self):
        tiquete = self._create_tiquete()
        tiquete.write({'l10n_cr_fe_clave': '5' * 50, 'l10n_cr_fe_state': 'aceptado'})
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'reversed_entry_id': tiquete.id,
            'l10n_cr_fe_motivo': 'devolucion_mercancia',
            'l10n_cr_fe_codigo_referencia': '06',
            'l10n_cr_fe_razon': 'Prueba',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })
        credit_note.action_post()
        self.assertEqual(credit_note.state, 'posted')
        self.assertEqual(credit_note.l10n_cr_fe_state, 'error')
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestTiqueteElectronicoFe.test_action_post_blocks_credit_note_on_tiquete_original --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: FAIL — la nota de crédito queda en `l10n_cr_fe_state='generado'` o similar (intenta procesarse en vez de fallar), no `'error'`.

- [ ] **Step 3: Agregar el candado**

En `addons/l10n_cr_fe_crlibre/models/account_move.py`, dentro de `_l10n_cr_fe_generate_and_send`, reemplazar:

```python
            if self.move_type == 'out_refund':
                original = self.reversed_entry_id
                if not original or original.l10n_cr_fe_state != 'aceptado':
                    raise UserError(_(
                        "No se puede generar la nota de crédito: la factura original "
                        "aún no ha sido aceptada por Hacienda."))
```

por:

```python
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
```

- [ ] **Step 4: Correr el test para confirmar que pasa**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestTiqueteElectronicoFe --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: PASS — todos los tests de `TestTiqueteElectronicoFe` (5 en total: éxito básico, sin cédula, y este candado).

- [ ] **Step 5: Correr la suite completa del módulo para confirmar que no hay regresiones**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo`

Expected: `0 failed, 0 error(s)` en la línea final `odoo.tests.result`.

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests/test_tiquete_electronico_fe.py
git commit -m "feat(l10n_cr_fe): bloquear nota de credito sobre un Tiquete Electronico"
```

---

## Verificación manual pendiente (fuera de las tareas automatizadas)

Ninguna tarea de este plan corre un navegador. Después de que las 4 tareas estén mergeadas, verificar en la UI: marcar una factura nueva como "Consumidor final (Tiquete Electrónico)" con un cliente sin cédula, confirmarla, y comprobar en la pestaña "Factura Electrónica CR" que queda con clave/consecutivo generados y estado avanzando igual que una Factura normal — y que "Consultar estado FE" / "Reintentar" siguen funcionando sobre ese registro sin cambios.
