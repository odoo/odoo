# Nota de Débito Electrónica (ND) desde una Factura — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir crear y enviar a Hacienda una Nota de Débito Electrónica (v4.4, tipoDocumento `ND`) desde una Factura Electrónica de venta ya aceptada, usando el wizard nativo de Odoo para notas de débito.

**Architecture:** Se reutiliza toda la tubería existente de `l10n_cr_fe_crlibre` (construcción de detalle de líneas, resumen de totales, firma, envío, consulta de estado), generalizada por el tipo de documento resuelto en `_l10n_cr_fe_get_tipo_documento_info()` — mismo patrón ya usado para Nota de Crédito, Tiquete Electrónico y Mensaje Receptor. Se extiende el módulo core `account_debit_note` (nueva dependencia) para capturar el motivo/código de referencia de la ND, mismo patrón que la extensión ya construida de `account.move.reversal` para Nota de Crédito.

**Tech Stack:** Odoo 19 ORM (Python), XML views, `TransactionCase` con mocks de `unittest.mock.patch` sobre `CrlibreFeClient` (sin llamadas HTTP reales en tests).

## Global Constraints

- Spec de referencia: `docs/superpowers/specs/2026-07-30-nota-debito-electronica-design.md`.
- Seguir el estilo TDD ya establecido en este módulo: escribir el test, correrlo para confirmar que falla (RED), implementar, correrlo para confirmar que pasa (GREEN), commit.
- Comando estándar para correr tests de este módulo (reemplazar `<TAGS>` por el tag específico o `/l10n_cr_fe_crlibre` para todo el módulo):
  ```bash
  MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags <TAGS> --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
  ```
  El flag `-u l10n_cr_fe_crlibre` es necesario siempre que se agreguen/cambien campos, modelos o vistas — actualiza el esquema/registro antes de correr los tests. **Importante para la Tarea 1:** una vez que el manifest declare `account_debit_note` como dependencia nueva, el primer `-u l10n_cr_fe_crlibre` que se corra después de ese cambio instala automáticamente `account_debit_note` (Odoo instala cualquier dependencia nueva del módulo que se está actualizando) — no hace falta un `-i` aparte.
  - Suite base antes de este plan: 134 tests. Este plan agrega 13 tests nuevos (147 al final).
- Imports ordenados: futuro → stdlib → terceros → odoo (primero) → odoo.addons (local) — ya enforced por `ruff.toml`.
- Prefijo de métodos propios de este módulo: `_l10n_cr_fe_*` (convención ya establecida en `account_move.py`).
- Después del último task, reiniciar el contenedor vivo (`docker restart erp-odoo-1`) para que el usuario pueda probar manualmente.

---

### Task 1: Dependencia `account_debit_note` + tipo de documento ND en `account.move`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/__manifest__.py`
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Test: `addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py`

**Interfaces:**
- Consumes: campo nativo `debit_origin_id` en `account.move` (viene del módulo `account_debit_note`, no existe hasta que se agregue la dependencia).
- Produces: constantes de módulo `L10N_CR_FE_TIPO_DOCUMENTO_ND`, `L10N_CR_FE_MOTIVO_ND`, `L10N_CR_FE_MOTIVO_CODIGO_MAP_ND`. Campo `account.move.l10n_cr_fe_motivo_nd`. `_l10n_cr_fe_get_tipo_documento_info()` reconoce ND. Usado por las Tareas 2-5.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py`:

```python
    def test_motivo_nd_selection_maps_to_expected_codigo_referencia(self):
        from odoo.addons.l10n_cr_fe_crlibre.models.account_move import L10N_CR_FE_MOTIVO_CODIGO_MAP_ND
        self.assertEqual(L10N_CR_FE_MOTIVO_CODIGO_MAP_ND, {
            'correccion_monto': '02',
            'cargo_financiero': '10',
            'referencia_otro_documento': '04',
            'otros': '99',
        })

    def test_tipo_documento_nd_constant(self):
        from odoo.addons.l10n_cr_fe_crlibre.models.account_move import L10N_CR_FE_TIPO_DOCUMENTO_ND
        self.assertEqual(L10N_CR_FE_TIPO_DOCUMENTO_ND, {
            'clave': 'ND', 'consecutivo_codigo': '02', 'gen_xml_action': 'gen_xml_nd',
        })

    def test_motivo_nd_field_exists_with_default(self):
        partner = self.env['res.partner'].create({'name': 'Cliente ND Fields'})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
        })
        self.assertFalse(invoice.l10n_cr_fe_motivo_nd)

    def test_get_tipo_documento_info_returns_nd_when_debit_origin_set(self):
        partner = self.env['res.partner'].create({'name': 'Cliente ND Dispatch'})
        original = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
        })
        debit_note = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'debit_origin_id': original.id,
        })
        info = debit_note._l10n_cr_fe_get_tipo_documento_info()
        self.assertEqual(info['clave'], 'ND')
        self.assertEqual(info['consecutivo_codigo'], '02')
```

- [ ] **Step 2: Correr los tests para confirmar que fallan (RED)**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveFeFields --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: FAIL con `ImportError`/`AttributeError` en los tres primeros tests nuevos (las constantes y el campo no existen); el cuarto (`test_get_tipo_documento_info_returns_nd_when_debit_origin_set`) también falla, con `ValueError: Invalid field 'debit_origin_id'` porque `account_debit_note` todavía no es dependencia.

- [ ] **Step 3: Agregar la dependencia al manifest**

En `addons/l10n_cr_fe_crlibre/__manifest__.py`, reemplazar:

```python
    'depends': ['account', 'l10n_cr'],
```

por:

```python
    'depends': ['account', 'l10n_cr', 'account_debit_note'],
```

- [ ] **Step 4: Agregar las constantes y el campo en `account_move.py`**

Abrir `addons/l10n_cr_fe_crlibre/models/account_move.py`. Justo después del bloque `L10N_CR_FE_TIPO_DOCUMENTO_MR` (termina con la línea `}`, antes del comentario `# Motivos de negocio para una nota de crédito...`), insertar:

```python
# Nota de Debito (ND): igual que Tiquete Electronico, comparte move_type
# 'out_invoice' con Factura, asi que no puede tener su propia entrada en
# L10N_CR_FE_TIPO_DOCUMENTO (indexado por move_type). Se distingue por el
# campo nativo debit_origin_id (modulo account_debit_note), no por move_type.
# Se resuelve en _l10n_cr_fe_get_tipo_documento_info().
L10N_CR_FE_TIPO_DOCUMENTO_ND = {'clave': 'ND', 'consecutivo_codigo': '02', 'gen_xml_action': 'gen_xml_nd'}
```

Justo después del bloque `L10N_CR_FE_MOTIVO_CODIGO_MAP` (el de Nota de Crédito, termina con `}`, antes del comentario `# Catálogo completo de "Código de referencia"...`), insertar:

```python
# Motivos de negocio para una nota de debito, mostrados al usuario en el
# wizard nativo de Nota de Debito (account.debit.note). Cada uno mapea a un
# codigo oficial de Hacienda -- reutiliza el mismo catalogo completo que NC
# (L10N_CR_FE_CODIGO_REFERENCIA, mas abajo), pero con opciones de negocio
# distintas porque una ND aumenta el monto en vez de reducirlo.
L10N_CR_FE_MOTIVO_ND = [
    ('correccion_monto', "Corrección de monto, precio, cantidad o descuento"),
    ('cargo_financiero', "Cargo financiero (intereses, cargos por mora)"),
    ('referencia_otro_documento', "Referencia a otro documento"),
    ('otros', "Otros"),
]

L10N_CR_FE_MOTIVO_CODIGO_MAP_ND = {
    'correccion_monto': '02',
    'cargo_financiero': '10',
    'referencia_otro_documento': '04',
    'otros': '99',
}
```

Dentro de la clase `AccountMove`, justo después del campo `l10n_cr_fe_razon` (`l10n_cr_fe_razon = fields.Char(string="Razón (Hacienda)", copy=False)`), agregar:

```python
    l10n_cr_fe_motivo_nd = fields.Selection(
        L10N_CR_FE_MOTIVO_ND, string="Motivo de la nota de débito", copy=False)
```

Reemplazar el método `_l10n_cr_fe_get_tipo_documento_info`:

```python
    def _l10n_cr_fe_get_tipo_documento_info(self):
        self.ensure_one()
        if self.move_type == 'out_invoice' and self.debit_origin_id:
            return L10N_CR_FE_TIPO_DOCUMENTO_ND
        if self.move_type == 'out_invoice' and self.l10n_cr_fe_es_tiquete:
            return L10N_CR_FE_TIPO_DOCUMENTO_TE
        if self.move_type == 'in_invoice':
            return L10N_CR_FE_TIPO_DOCUMENTO_MR.get(self.l10n_cr_fe_mr_decision)
        return L10N_CR_FE_TIPO_DOCUMENTO.get(self.move_type)
```

- [ ] **Step 5: Correr los tests para confirmar que pasan (GREEN)**

Mismo comando del Step 2. Esperado: los cuatro tests nuevos en PASS, y los 134 tests previos del módulo siguen en 0 failed/0 error (esto además confirma que `account_debit_note` se instaló correctamente como dependencia nueva).

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/__manifest__.py addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py
git commit -m "feat(l10n_cr_fe_crlibre): agregar dependencia account_debit_note y tipo de documento ND

Nueva dependencia del modulo core account_debit_note (wizard nativo de
Nota de Debito). _l10n_cr_fe_get_tipo_documento_info() distingue una ND
por el campo nativo debit_origin_id, ya que comparte move_type
'out_invoice' con la Factura normal -- mismo patron ya usado para
Tiquete Electronico.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `gen_xml_nd` en el cliente HTTP

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`
- Test: `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`

**Interfaces:**
- Consumes: nada nuevo.
- Produces: `CrlibreFeClient.gen_xml_nd(self, params) -> str` (XML decodificado). Usado por la Tarea 4.

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`:

```python
    def test_gen_xml_nd_decodes_base64(self):
        import base64
        xml = '<NotaDebitoElectronica>ok</NotaDebitoElectronica>'
        payload = {'status': 'ok',
                   'resp': {'clave': '5' * 50, 'xml': base64.b64encode(xml.encode()).decode()}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.gen_xml_nd({'clave': '5' * 50})
        self.assertEqual(result, xml)
        self.assertEqual(m.call_args.kwargs['data']['r'], 'gen_xml_nd')
```

- [ ] **Step 2: Confirmar que falla**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons --test-enable --test-tags /l10n_cr_fe_crlibre:TestCrlibreClient.test_gen_xml_nd_decodes_base64 --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: FAIL con `AttributeError: 'l10n.cr.fe.client' object has no attribute 'gen_xml_nd'`.

- [ ] **Step 3: Implementar**

En `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`, justo después del método `gen_xml_nc`, agregar:

```python
    def gen_xml_nd(self, params):
        resp = self._call('genXML', 'gen_xml_nd', params)
        if not isinstance(resp, dict) or not resp.get('xml'):
            raise CrlibreApiError("Respuesta inesperada de 'gen_xml_nd': %s" % resp)
        return base64.b64decode(resp['xml']).decode('utf-8')
```

- [ ] **Step 4: Confirmar que pasa**

Mismo comando del Step 2. Esperado: PASS.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/crlibre_client.py addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py
git commit -m "feat(l10n_cr_fe_crlibre): agregar gen_xml_nd al cliente HTTP para notas de debito

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `InformacionReferencia` en `_l10n_cr_fe_build_genxml_params`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py` (método `_l10n_cr_fe_build_genxml_params`)
- Test: `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`

**Interfaces:**
- Consumes: `debit_origin_id` (nativo), `l10n_cr_fe_clave`/`l10n_cr_fe_fecha_emision` de la factura original, `self.l10n_cr_fe_codigo_referencia`/`l10n_cr_fe_razon` (Tarea 1 y campos ya existentes de NC).
- Produces: parámetro `informacion_referencia` (JSON) en el dict que retorna `_l10n_cr_fe_build_genxml_params`, también presente cuando hay `debit_origin_id` (no solo para `out_refund`). Usado por la Tarea 4.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`:

```python
    def test_build_clave_params_nota_debito_uses_nd(self):
        original = self.invoice
        original.write({'l10n_cr_fe_clave': '5' * 50, 'l10n_cr_fe_state': 'aceptado'})
        debit_note = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'debit_origin_id': original.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 500.0,
                'name': 'Cargo adicional', 'tax_ids': [(6, 0, [])],
            })],
        })
        params = debit_note._l10n_cr_fe_build_clave_params()
        self.assertEqual(params['tipoDocumento'], 'ND')
        self.assertEqual(len(params['consecutivo']), 10)

    def test_build_genxml_params_nota_debito_includes_informacion_referencia(self):
        import json as json_module
        original = self.invoice
        original.write({
            'l10n_cr_fe_clave': '5' * 50,
            'l10n_cr_fe_fecha_emision': '2026-07-01T10:00:00-06:00',
            'l10n_cr_fe_state': 'aceptado',
        })
        debit_note = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'debit_origin_id': original.id,
            'l10n_cr_fe_motivo_nd': 'cargo_financiero',
            'l10n_cr_fe_codigo_referencia': '10',
            'l10n_cr_fe_razon': 'Interés por mora en el pago',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 500.0,
                'name': 'Cargo adicional', 'tax_ids': [(6, 0, [])],
            })],
        })
        detalles = debit_note._l10n_cr_fe_build_detalles()
        params = debit_note._l10n_cr_fe_build_genxml_params('9' * 50, '0' * 20, detalles)
        referencia = json_module.loads(params['informacion_referencia'])
        self.assertEqual(len(referencia), 1)
        self.assertEqual(referencia[0]['tipoDoc'], '01')
        self.assertEqual(referencia[0]['numero'], '5' * 50)
        self.assertEqual(referencia[0]['fechaEmision'], '2026-07-01T10:00:00-06:00')
        self.assertEqual(referencia[0]['codigo'], '10')
        self.assertEqual(referencia[0]['razon'], 'Interés por mora en el pago')
```

- [ ] **Step 2: Confirmar que fallan**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountMoveMapping.test_build_clave_params_nota_debito_uses_nd,/l10n_cr_fe_crlibre:TestAccountMoveMapping.test_build_genxml_params_nota_debito_includes_informacion_referencia --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: el primer test (`test_build_clave_params_nota_debito_uses_nd`) ya pasa (la Tarea 1 ya generalizó `_l10n_cr_fe_build_clave_params` vía `_l10n_cr_fe_get_tipo_documento_info`) — sirve como test de regresión. El segundo falla con `KeyError: 'informacion_referencia'`.

- [ ] **Step 3: Implementar**

En `addons/l10n_cr_fe_crlibre/models/account_move.py`, dentro de `_l10n_cr_fe_build_genxml_params`, reemplazar:

```python
        if self.move_type == 'out_refund':
            original = self.reversed_entry_id
            params['informacion_referencia'] = json.dumps([{
                'tipoDoc': '01',  # Factura electrónica (catálogo TipoDocReferenciaType)
                'numero': original.l10n_cr_fe_clave,
                'fechaEmision': original.l10n_cr_fe_fecha_emision,
                'codigo': self.l10n_cr_fe_codigo_referencia,
                'razon': self.l10n_cr_fe_razon or '',
            }])
        return params
```

por:

```python
        if self.move_type == 'out_refund':
            original = self.reversed_entry_id
            params['informacion_referencia'] = json.dumps([{
                'tipoDoc': '01',  # Factura electrónica (catálogo TipoDocReferenciaType)
                'numero': original.l10n_cr_fe_clave,
                'fechaEmision': original.l10n_cr_fe_fecha_emision,
                'codigo': self.l10n_cr_fe_codigo_referencia,
                'razon': self.l10n_cr_fe_razon or '',
            }])
        elif self.debit_origin_id:
            original = self.debit_origin_id
            params['informacion_referencia'] = json.dumps([{
                'tipoDoc': '01',  # Factura electrónica (catálogo TipoDocReferenciaType)
                'numero': original.l10n_cr_fe_clave,
                'fechaEmision': original.l10n_cr_fe_fecha_emision,
                'codigo': self.l10n_cr_fe_codigo_referencia,
                'razon': self.l10n_cr_fe_razon or '',
            }])
        return params
```

- [ ] **Step 4: Confirmar que pasan**

Mismo comando del Step 2. Esperado: los dos tests en PASS, y `test_build_genxml_params_factura_has_no_informacion_referencia` (existente) sigue en PASS (una Factura normal no tiene `debit_origin_id`, así que ninguna de las dos ramas nuevas aplica).

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py
git commit -m "feat(l10n_cr_fe_crlibre): armar InformacionReferencia para notas de debito

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Validación y envío real de la ND en `_l10n_cr_fe_generate_and_send`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py` (método `_l10n_cr_fe_generate_and_send`)
- Create: `addons/l10n_cr_fe_crlibre/tests/test_nota_debito_fe.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`

**Interfaces:**
- Consumes: `L10N_CR_FE_TIPO_DOCUMENTO_ND` (Tarea 1), `client.gen_xml_nd` (Tarea 2), `informacion_referencia` (Tarea 3).
- Produces: `_l10n_cr_fe_generate_and_send()` valida y envía correctamente una ND; `action_post()` la dispara igual que para FE/NC/TE (ya generalizado, sin cambios ahí).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `addons/l10n_cr_fe_crlibre/tests/test_nota_debito_fe.py`:

```python
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestNotaDebitoFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas ND Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas ND Test SA',
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
        self.original_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_clave': '5' * 50,
            'l10n_cr_fe_fecha_emision': '2026-07-01T10:00:00-06:00',
            'l10n_cr_fe_state': 'aceptado',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })

    def _create_debit_note(self):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'debit_origin_id': self.original_invoice.id,
            'l10n_cr_fe_motivo_nd': 'cargo_financiero',
            'l10n_cr_fe_codigo_referencia': '10',
            'l10n_cr_fe_razon': 'Interés por pago tardío',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 100.0,
                'name': 'Interés por mora', 'tax_ids': [(6, 0, [])],
            })],
        })

    def _patch_full_success(self):
        clave = '9' * 50
        return [
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                  return_value={'clave': clave, 'consecutivo': '0' * 20}),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_nd',
                  return_value='<NotaDebitoElectronica>sin firmar</NotaDebitoElectronica>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                  return_value='tok123'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.sign_xml',
                  return_value='<NotaDebitoElectronica>firmada</NotaDebitoElectronica>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.send_fe',
                  return_value={'http_status': 202, 'raw': []}),
        ]

    def test_action_post_sends_debit_note_using_gen_xml_nd(self):
        debit_note = self._create_debit_note()
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            debit_note.action_post()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(debit_note.l10n_cr_fe_state, 'enviado')
        self.assertEqual(debit_note.l10n_cr_fe_clave, '9' * 50)
        self.assertIn('firmada', debit_note.l10n_cr_fe_xml_firmado)

    def test_action_post_blocks_debit_note_when_original_not_aceptado(self):
        self.original_invoice.l10n_cr_fe_state = 'enviado'
        debit_note = self._create_debit_note()
        debit_note.action_post()
        self.assertEqual(debit_note.state, 'posted')
        self.assertEqual(debit_note.l10n_cr_fe_state, 'error')

    def test_action_post_blocks_debit_note_on_tiquete_original(self):
        self.original_invoice.l10n_cr_fe_es_tiquete = True
        debit_note = self._create_debit_note()
        debit_note.action_post()
        self.assertEqual(debit_note.state, 'posted')
        self.assertEqual(debit_note.l10n_cr_fe_state, 'error')
```

- [ ] **Step 2: Registrar el archivo de test nuevo**

En `addons/l10n_cr_fe_crlibre/tests/__init__.py`, agregar la línea `from . import test_nota_debito_fe` junto a los demás `from . import test_*` ya existentes (por ejemplo, justo después de `from . import test_nota_credito_fe`).

- [ ] **Step 3: Confirmar que fallan**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestNotaDebitoFe --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: `test_action_post_sends_debit_note_using_gen_xml_nd` FALLA porque `l10n_cr_fe_state` queda en `'draft'` (todavía no hay validación/rama específica para ND en `_l10n_cr_fe_generate_and_send`, pero como el `tipo_doc` ya resuelve a ND desde la Tarea 1, en realidad **puede que ya pase** sin cambios adicionales — si es así, es correcto, ya que la Tarea 1-3 dejaron la tubería genérica funcionando). Los otros dos tests (bloqueo por no-aceptado y por tiquete) SÍ deben fallar: sin la validación nueva, el envío se intenta igual y termina en `'enviado'` en vez de `'error'`, porque nada bloquea el envío de una ND sobre un original no aceptado.

- [ ] **Step 4: Implementar la validación**

En `addons/l10n_cr_fe_crlibre/models/account_move.py`, dentro de `_l10n_cr_fe_generate_and_send`, reemplazar:

```python
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
```

por:

```python
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
            if tipo_doc == L10N_CR_FE_TIPO_DOCUMENTO_ND:
                original = self.debit_origin_id
                if not original or original.l10n_cr_fe_state != 'aceptado':
                    raise UserError(_(
                        "No se puede generar la nota de débito: la factura original "
                        "aún no ha sido aceptada por Hacienda."))
                if original.l10n_cr_fe_es_tiquete:
                    raise UserError(_(
                        "No se puede generar una nota de débito sobre un Tiquete "
                        "Electrónico todavía — esta corrección no está soportada."))

            config = self._l10n_cr_fe_get_config()
```

- [ ] **Step 5: Confirmar que pasan**

Mismo comando del Step 3. Esperado: los tres tests en PASS.

- [ ] **Step 6: Correr TODA la suite del módulo para confirmar que no hay regresión**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: `0 failed, 0 error(s)`, en particular `test_action_post_blocks_credit_note_when_original_not_aceptado` (NC) y todos los tests de Tiquete/MR siguen en PASS — confirma que la rama nueva de ND no interfiere con las ramas de NC/TE/MR.

- [ ] **Step 7: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests/test_nota_debito_fe.py addons/l10n_cr_fe_crlibre/tests/__init__.py
git commit -m "feat(l10n_cr_fe_crlibre): validar y enviar nota de debito a Hacienda

_l10n_cr_fe_generate_and_send() ahora bloquea el envio de una ND si la
factura original no esta aceptada por Hacienda, o si es un Tiquete
Electronico -- mismo criterio ya aplicado a Nota de Credito. El resto
del envio (gen_xml_nd, firma, send_fe) ya funcionaba generico desde las
tareas anteriores.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Wizard `account.debit.note` extendido (motivo + código de referencia) y su vista

**Files:**
- Create: `addons/l10n_cr_fe_crlibre/wizards/account_debit_note.py`
- Modify: `addons/l10n_cr_fe_crlibre/wizards/__init__.py`
- Create: `addons/l10n_cr_fe_crlibre/views/account_debit_note_views.xml`
- Modify: `addons/l10n_cr_fe_crlibre/__manifest__.py`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_account_debit_note.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`

**Interfaces:**
- Consumes: `L10N_CR_FE_MOTIVO_ND`, `L10N_CR_FE_MOTIVO_CODIGO_MAP_ND`, `L10N_CR_FE_CODIGO_REFERENCIA` (Tarea 1 y campos ya existentes).
- Produces: al confirmar el wizard (`create_debit`), la ND creada trae `l10n_cr_fe_motivo_nd`, `l10n_cr_fe_codigo_referencia` y `l10n_cr_fe_razon` ya poblados.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `addons/l10n_cr_fe_crlibre/tests/test_account_debit_note.py`:

```python
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountDebitNoteFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas Debit Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas Debit Test SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de demostración',
            'email': 'demo@frutasdemo.cr',
        })
        self.partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        self.product = self.env['product.product'].create({
            'name': 'Producto demo', 'l10n_cr_fe_cabys': '0111101000000'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_clave': '5' * 50,
            'l10n_cr_fe_state': 'aceptado',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })
        self.invoice.action_post()

    def test_motivo_nd_computes_expected_codigo_referencia(self):
        wizard = self.env['account.debit.note'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'l10n_cr_fe_motivo_nd': 'cargo_financiero',
            })
        self.assertEqual(wizard.l10n_cr_fe_codigo_referencia, '10')

    def test_applicable_true_for_accepted_fe_invoice(self):
        wizard = self.env['account.debit.note'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({})
        self.assertTrue(wizard.l10n_cr_fe_applicable)

    def test_create_debit_copies_motivo_to_debit_note(self):
        wizard = self.env['account.debit.note'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'l10n_cr_fe_motivo_nd': 'correccion_monto',
                'reason': 'Se facturó de menos por error de digitación',
            })
        action = wizard.create_debit()
        debit_note = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(debit_note.l10n_cr_fe_motivo_nd, 'correccion_monto')
        self.assertEqual(debit_note.l10n_cr_fe_codigo_referencia, '02')
        self.assertEqual(debit_note.l10n_cr_fe_razon, 'Se facturó de menos por error de digitación')
        self.assertEqual(debit_note.debit_origin_id, self.invoice)
```

- [ ] **Step 2: Registrar el archivo de test nuevo**

En `addons/l10n_cr_fe_crlibre/tests/__init__.py`, agregar `from . import test_account_debit_note` junto a los demás imports.

- [ ] **Step 3: Confirmar que fallan**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre:TestAccountDebitNoteFe --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: FAIL — `ValueError: Invalid field 'l10n_cr_fe_motivo_nd' on model 'account.debit.note'` (el wizard no está extendido todavía).

- [ ] **Step 4: Implementar el wizard**

Crear `addons/l10n_cr_fe_crlibre/wizards/account_debit_note.py`:

```python
from odoo import api, fields, models

from odoo.addons.l10n_cr_fe_crlibre.models.account_move import (
    L10N_CR_FE_CODIGO_REFERENCIA,
    L10N_CR_FE_MOTIVO_CODIGO_MAP_ND,
    L10N_CR_FE_MOTIVO_ND,
)


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    l10n_cr_fe_applicable = fields.Boolean(compute='_compute_l10n_cr_fe_applicable')
    l10n_cr_fe_is_admin = fields.Boolean(compute='_compute_l10n_cr_fe_is_admin')
    l10n_cr_fe_motivo_nd = fields.Selection(L10N_CR_FE_MOTIVO_ND, string="Motivo de la nota de débito")
    l10n_cr_fe_codigo_referencia = fields.Selection(
        L10N_CR_FE_CODIGO_REFERENCIA, string="Código de referencia Hacienda",
        compute='_compute_l10n_cr_fe_codigo_referencia', store=True, readonly=False)

    @api.depends('move_ids')
    def _compute_l10n_cr_fe_applicable(self):
        for wizard in self:
            wizard.l10n_cr_fe_applicable = bool(
                wizard.move_ids and len(wizard.move_ids) == 1
                and wizard.move_ids.move_type == 'out_invoice'
                and wizard.move_ids.l10n_cr_fe_clave)

    def _compute_l10n_cr_fe_is_admin(self):
        is_admin = self.env.user.has_group('l10n_cr_fe_crlibre.group_fe_admin')
        for wizard in self:
            wizard.l10n_cr_fe_is_admin = is_admin

    @api.depends('l10n_cr_fe_motivo_nd')
    def _compute_l10n_cr_fe_codigo_referencia(self):
        for wizard in self:
            wizard.l10n_cr_fe_codigo_referencia = L10N_CR_FE_MOTIVO_CODIGO_MAP_ND.get(wizard.l10n_cr_fe_motivo_nd)

    def _prepare_default_values(self, move):
        return {
            **super()._prepare_default_values(move),
            'l10n_cr_fe_motivo_nd': self.l10n_cr_fe_motivo_nd,
            'l10n_cr_fe_codigo_referencia': self.l10n_cr_fe_codigo_referencia,
            'l10n_cr_fe_razon': self.reason,
        }
```

Modificar `addons/l10n_cr_fe_crlibre/wizards/__init__.py` (contenido completo, reemplaza el archivo):

```python
from . import account_move_reversal
from . import proveedor_upload
from . import mr_motivo_wizard
from . import account_debit_note
```

- [ ] **Step 5: Confirmar que pasan**

Mismo comando del Step 3. Esperado: los tres tests nuevos en PASS.

- [ ] **Step 6: Crear la vista del wizard**

Crear `addons/l10n_cr_fe_crlibre/views/account_debit_note_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_account_debit_note_inherit_l10n_cr_fe" model="ir.ui.view">
        <field name="name">account.debit.note.form.inherit.l10n.cr.fe</field>
        <field name="inherit_id" ref="account_debit_note.view_account_debit_note"/>
        <field name="model">account.debit.note</field>
        <field name="arch" type="xml">
            <field name="reason" position="before">
                <field name="l10n_cr_fe_applicable" invisible="1"/>
                <field name="l10n_cr_fe_is_admin" invisible="1"/>
                <field name="l10n_cr_fe_motivo_nd" invisible="not l10n_cr_fe_applicable"
                       required="l10n_cr_fe_applicable"/>
                <field name="l10n_cr_fe_codigo_referencia" invisible="not l10n_cr_fe_applicable"
                       readonly="not l10n_cr_fe_is_admin"/>
            </field>
        </field>
    </record>
</odoo>
```

- [ ] **Step 7: Registrar la vista nueva en el manifest**

En `addons/l10n_cr_fe_crlibre/__manifest__.py`, en la lista `'data'`, agregar `'views/account_debit_note_views.xml'` justo después de `'views/account_move_reversal_views.xml'`:

```python
        'views/account_move_views.xml',
        'views/account_move_reversal_views.xml',
        'views/account_debit_note_views.xml',
        'views/proveedor_upload_views.xml',
```

- [ ] **Step 8: Actualizar el módulo y confirmar que carga sin errores**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: `Module l10n_cr_fe_crlibre loaded in ...` sin ningún `ERROR` en el log (en particular, sin error de xpath — confirma que `account_debit_note.view_account_debit_note` es el external ID correcto de la vista nativa).

- [ ] **Step 9: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/wizards/account_debit_note.py addons/l10n_cr_fe_crlibre/wizards/__init__.py addons/l10n_cr_fe_crlibre/views/account_debit_note_views.xml addons/l10n_cr_fe_crlibre/__manifest__.py addons/l10n_cr_fe_crlibre/tests/test_account_debit_note.py addons/l10n_cr_fe_crlibre/tests/__init__.py
git commit -m "feat(l10n_cr_fe_crlibre): extender wizard nativo de nota de debito con motivo/codigo

Mismo patron que la extension ya construida de account.move.reversal
para Nota de Credito: el wizard account.debit.note captura el motivo
de negocio, lo mapea a un codigo oficial de Hacienda (editable solo
por group_fe_admin), y lo copia a la ND resultante al confirmar.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Mostrar los campos de ND en el formulario de factura

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`

**Interfaces:**
- Consumes: `l10n_cr_fe_motivo_nd` (Tarea 1), `debit_origin_id` (nativo de `account_debit_note`, ya visible en el formulario por ese módulo).
- Produces: nada para otras tareas — última tarea del plan.

- [ ] **Step 1: Ampliar la pestaña "Factura Electrónica CR"**

En `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`, reemplazar:

```xml
                        <field name="l10n_cr_fe_motivo" invisible="move_type != 'out_refund'"/>
                        <field name="l10n_cr_fe_codigo_referencia" invisible="move_type != 'out_refund'"/>
                        <field name="l10n_cr_fe_razon" invisible="move_type != 'out_refund'"/>
```

por:

```xml
                        <field name="l10n_cr_fe_motivo" invisible="move_type != 'out_refund'"/>
                        <field name="l10n_cr_fe_motivo_nd" invisible="not debit_origin_id"/>
                        <field name="l10n_cr_fe_codigo_referencia" invisible="move_type != 'out_refund' and not debit_origin_id"/>
                        <field name="l10n_cr_fe_razon" invisible="move_type != 'out_refund' and not debit_origin_id"/>
```

No hace falta declarar `debit_origin_id` en esta vista: `l10n_cr_fe_crlibre` depende de `account_debit_note` (Tarea 1), cuya propia vista (`account_debit_note/views/account_move_view.xml`) ya agrega ese campo al formulario nativo antes de que esta vista se aplique encima — queda disponible para la condición `invisible` sin redeclararlo.

Los botones "Consultar estado FE"/"Reintentar envío FE" y el statusbar de `l10n_cr_fe_state` no necesitan cambios: ya son `invisible` solo cuando `move_type not in ('out_invoice', 'out_refund', 'in_invoice')`, y una ND es `out_invoice`, así que ya quedan cubiertos.

- [ ] **Step 2: Actualizar el módulo y confirmar que carga sin errores**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```
Expected: `Module l10n_cr_fe_crlibre loaded in ...` sin ningún `ERROR` en el log.

- [ ] **Step 3: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/views/account_move_views.xml
git commit -m "feat(l10n_cr_fe_crlibre): mostrar motivo/codigo de nota de debito en el formulario de factura

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Verificación final del plan

- [ ] **Correr la suite completa una última vez:**

```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init --http-port=8169 --db_host=db --db_user=odoo --db_password=odoo
```

Esperado: `0 failed, 0 error(s)`, con el conteo total de tests en 147 (134 previos + 4 de la Tarea 1 + 1 de la Tarea 2 + 2 de la Tarea 3 + 3 de la Tarea 4 + 3 de la Tarea 5).

- [ ] **Reiniciar el contenedor vivo:**

```bash
docker restart erp-odoo-1
```

- [ ] **Verificación manual en sandbox** (fuera del alcance de los tests automatizados, requiere credenciales reales de Hacienda que el usuario ya tiene configuradas): sobre una Factura de venta ya aceptada, usar el botón "Debit Note" del formulario, elegir motivo "Cargo financiero", agregar una línea de cargo nuevo, confirmar el wizard, y postear la ND resultante. Verificar en el chatter que Hacienda la acepta, y que el consecutivo de ND empieza en 1 independiente de los de FE/NC/TE/MR.
