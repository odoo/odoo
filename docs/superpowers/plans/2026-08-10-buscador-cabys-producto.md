# Buscador CABYS en producto — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar un buscador de códigos CABYS (por texto libre o código exacto) contra la API pública de Hacienda, accesible desde el formulario de producto, que muestra varias coincidencias y solo aplica CABYS + descripción + impuesto de venta cuando el usuario confirma explícitamente una de ellas.

**Architecture:** Un `AbstractModel` (`l10n_cr.fe.cabys.client`) hace `GET` a `https://api.hacienda.go.cr/fe/cabys` y normaliza la respuesta. Un `TransientModel` wizard (`l10n_cr.fe.cabys.wizard`) orquesta la búsqueda y muestra resultados en un `One2many` a un segundo `TransientModel` de línea (`l10n_cr.fe.cabys.wizard.line`); cada línea tiene su propio botón "Usar este código" que escribe sobre el `product.template` de origen. `product.template` gana un campo de descripción CABYS y un botón que abre el wizard.

**Tech Stack:** Odoo 19 ORM (`odoo/orm/`), `requests` para HTTP, `odoo.tests.common.TransactionCase` con `unittest.mock.patch` para pruebas.

## Global Constraints

- Nunca asignar CABYS, descripción o impuesto sin una confirmación explícita del usuario (clic en "Usar este código" de una fila concreta) — ver spec sección 1, "Decisión de diseño clave".
- El impuesto de venta solo se asigna si existe un `account.tax` (`type_tax_use='sale'`) con esa tarifa exacta en la empresa activa; si no existe, CABYS y descripción igual se guardan y se avisa sin bloquear — ver spec sección 5.
- URL de la API de Hacienda fija (`https://api.hacienda.go.cr/fe/cabys`), no depende de `ir.config_parameter` ni de ambiente sandbox/producción — ver spec sección 4.1.
- Seguir las convenciones ya establecidas en `addons/l10n_cr_fe_crlibre/`: excepción tipada por cliente HTTP, wizards como `TransientModel` con acciones que devuelven `{'type': 'ir.actions.act_window_close'}`, tests con `@tagged('post_install', '-at_install')` y mocking vía `unittest.mock.patch`.

---

### Task 1: Cliente HTTP del catálogo CABYS

**Files:**
- Create: `addons/l10n_cr_fe_crlibre/models/cabys_client.py`
- Modify: `addons/l10n_cr_fe_crlibre/models/__init__.py`
- Test: `addons/l10n_cr_fe_crlibre/tests/test_cabys_client.py`

**Interfaces:**
- Produces: `CabysApiError(Exception)`; modelo `l10n_cr.fe.cabys.client` (`AbstractModel`) con método `buscar(self, query)` → `list[dict]`, cada dict con claves `codigo` (str), `descripcion` (str), `impuesto` (float). Lanza `CabysApiError` en cualquier fallo (texto corto, red, HTTP≠200, JSON inválido).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `addons/l10n_cr_fe_crlibre/tests/test_cabys_client.py`:

```python
from unittest.mock import MagicMock, patch

import requests

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.l10n_cr_fe_crlibre.models.cabys_client import CabysApiError


def _mock_response(status_code=200, json_data=None, raise_json=False):
    resp = MagicMock()
    resp.status_code = status_code
    if raise_json:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_data
    return resp


@tagged('post_install', '-at_install')
class TestCabysClient(TransactionCase):

    def setUp(self):
        super().setUp()
        self.client = self.env['l10n_cr.fe.cabys.client']

    def test_buscar_por_codigo_usa_parametro_codigo(self):
        resp = _mock_response(json_data=[
            {'codigo': '8311100000000', 'descripcion': 'Servicios de consultoría', 'impuesto': 13},
        ])
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    return_value=resp) as mock_get:
            resultados = self.client.buscar('8311100000000')
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs['params'], {'codigo': '8311100000000'})
        self.assertEqual(resultados, [
            {'codigo': '8311100000000', 'descripcion': 'Servicios de consultoría', 'impuesto': 13.0},
        ])

    def test_buscar_por_texto_usa_parametro_q(self):
        resp = _mock_response(json_data={
            'total': 2, 'cantidad': 2,
            'cabys': [
                {'codigo': '2314000991000', 'descripcion': 'Arroz precocido', 'impuesto': 1},
                {'codigo': '2313001000500', 'descripcion': 'Grañones de arroz', 'impuesto': 13},
            ],
        })
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    return_value=resp) as mock_get:
            resultados = self.client.buscar('arroz')
        self.assertEqual(mock_get.call_args.kwargs['params'], {'q': 'arroz'})
        self.assertEqual(len(resultados), 2)
        self.assertEqual(resultados[0]['codigo'], '2314000991000')
        self.assertEqual(resultados[0]['impuesto'], 1.0)

    def test_buscar_texto_corto_lanza_error_sin_llamar_api(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get') as mock_get:
            with self.assertRaises(CabysApiError):
                self.client.buscar('ar')
        mock_get.assert_not_called()

    def test_buscar_timeout_lanza_cabys_api_error(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    side_effect=requests.exceptions.Timeout()):
            with self.assertRaises(CabysApiError):
                self.client.buscar('arroz')

    def test_buscar_http_error_lanza_cabys_api_error(self):
        resp = _mock_response(status_code=500)
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    return_value=resp):
            with self.assertRaises(CabysApiError):
                self.client.buscar('arroz')

    def test_buscar_json_invalido_lanza_cabys_api_error(self):
        resp = _mock_response(raise_json=True)
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    return_value=resp):
            with self.assertRaises(CabysApiError):
                self.client.buscar('arroz')

    def test_buscar_sin_coincidencias_devuelve_lista_vacia(self):
        resp = _mock_response(json_data={'total': 0, 'cantidad': 0, 'cabys': []})
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    return_value=resp):
            resultados = self.client.buscar('xyzxyzxyz')
        self.assertEqual(resultados, [])
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python odoo-bin -d <database> --test-enable --test-tags test_cabys_client --stop-after-init -i l10n_cr_fe_crlibre`
Expected: FAIL — `KeyError`/`ModuleNotFoundError` porque `cabys_client.py` no existe todavía.

- [ ] **Step 3: Implementar `models/cabys_client.py`**

```python
import re

import requests

from odoo import models

CABYS_URL = 'https://api.hacienda.go.cr/fe/cabys'
CABYS_CODE_RE = re.compile(r'^\d{13}$')
TIMEOUT = 15


class CabysApiError(Exception):
    """Error al consultar el catálogo CABYS público de Hacienda."""


class CabysClient(models.AbstractModel):
    _name = 'l10n_cr.fe.cabys.client'
    _description = 'Cliente HTTP para el catálogo CABYS de Hacienda'

    def buscar(self, query):
        query = (query or '').strip()
        if CABYS_CODE_RE.match(query):
            params = {'codigo': query}
        elif len(query) >= 3:
            params = {'q': query}
        else:
            raise CabysApiError(
                "Escriba un código CABYS de 13 dígitos o un texto de al menos 3 caracteres.")
        try:
            resp = requests.get(CABYS_URL, params=params, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise CabysApiError("No se pudo conectar con la API de Hacienda: %s" % exc)
        if resp.status_code != 200:
            raise CabysApiError("La API de Hacienda respondió HTTP %s" % resp.status_code)
        try:
            data = resp.json()
        except ValueError:
            raise CabysApiError("La API de Hacienda devolvió una respuesta no-JSON.")
        return self._normalizar(data)

    def _normalizar(self, data):
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get('cabys') or []
        else:
            raise CabysApiError("Respuesta inesperada de la API de Hacienda: %s" % data)
        resultados = []
        for item in items:
            if not isinstance(item, dict) or not item.get('codigo'):
                continue
            resultados.append({
                'codigo': item['codigo'],
                'descripcion': item.get('descripcion', ''),
                'impuesto': float(item.get('impuesto') or 0),
            })
        return resultados
```

Modificar `addons/l10n_cr_fe_crlibre/models/__init__.py` agregando la nueva línea de import (mantener orden alfabético relativo a las existentes, junto a `crlibre_client`):

```python
from . import cabys_client
from . import crlibre_client
from . import fe_config
from . import product_template
from . import res_partner
from . import account_move
from . import proveedor_email
```

- [ ] **Step 4: Ejecutar los tests y verificar que pasan**

Run: `python odoo-bin -d <database> --test-enable --test-tags test_cabys_client --stop-after-init -i l10n_cr_fe_crlibre`
Expected: PASS — 7 tests en verde.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/cabys_client.py addons/l10n_cr_fe_crlibre/models/__init__.py addons/l10n_cr_fe_crlibre/tests/test_cabys_client.py
git commit -m "feat(l10n_cr_fe_crlibre): agregar cliente HTTP del catálogo CABYS de Hacienda"
```

---

### Task 2: Campo de descripción CABYS y botón en `product.template`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/product_template.py`
- Test: `addons/l10n_cr_fe_crlibre/tests/test_product_template.py`

**Interfaces:**
- Consumes: nada de Task 1 todavía (el botón solo abre una ventana; el wizard destino se crea en Task 3).
- Produces: campo `l10n_cr_fe_cabys_descripcion` (Char) en `product.template`; método `action_l10n_cr_fe_buscar_cabys(self)` que devuelve un dict de acción `ir.actions.act_window` apuntando a `res_model='l10n_cr.fe.cabys.wizard'` con `context={'default_product_id': self.id}`. Las tareas siguientes dependen de ese nombre de modelo y esa clave de contexto exactos.

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `addons/l10n_cr_fe_crlibre/tests/test_product_template.py`:

```python
    def test_action_buscar_cabys_abre_wizard_con_producto(self):
        product = self.env['product.template'].create({'name': 'Aguacate Hass'})
        action = product.action_l10n_cr_fe_buscar_cabys()
        self.assertEqual(action['res_model'], 'l10n_cr.fe.cabys.wizard')
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['target'], 'new')
        self.assertEqual(action['context']['default_product_id'], product.id)
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `python odoo-bin -d <database> --test-enable --test-tags test_product_template --stop-after-init -i l10n_cr_fe_crlibre`
Expected: FAIL — `AttributeError: 'product.template' object has no attribute 'action_l10n_cr_fe_buscar_cabys'`.

- [ ] **Step 3: Implementar el campo y el método**

En `addons/l10n_cr_fe_crlibre/models/product_template.py`, agregar el campo nuevo justo después de `l10n_cr_fe_cabys` y el método al final de la clase:

```python
import re

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

CABYS_RE = re.compile(r'^\d{13}$')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_cr_fe_cabys = fields.Char(string="Código CABYS")
    l10n_cr_fe_cabys_descripcion = fields.Char(string="Descripción CABYS", readonly=True)

    @api.constrains('l10n_cr_fe_cabys')
    def _check_l10n_cr_fe_cabys(self):
        for product in self:
            if product.l10n_cr_fe_cabys and not CABYS_RE.match(product.l10n_cr_fe_cabys):
                raise ValidationError(
                    _("El código CABYS de '%s' debe tener exactamente 13 dígitos.") % product.name)

    def action_l10n_cr_fe_buscar_cabys(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_cr.fe.cabys.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_id': self.id},
        }
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `python odoo-bin -d <database> --test-enable --test-tags test_product_template --stop-after-init -i l10n_cr_fe_crlibre`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/product_template.py addons/l10n_cr_fe_crlibre/tests/test_product_template.py
git commit -m "feat(l10n_cr_fe_crlibre): agregar descripción CABYS y acción para abrir el buscador"
```

---

### Task 3: Wizard de búsqueda y selección CABYS

**Files:**
- Create: `addons/l10n_cr_fe_crlibre/wizards/cabys_wizard.py`
- Modify: `addons/l10n_cr_fe_crlibre/wizards/__init__.py`
- Test: `addons/l10n_cr_fe_crlibre/tests/test_cabys_wizard.py`

**Interfaces:**
- Consumes: `l10n_cr.fe.cabys.client.buscar(query)` (Task 1); `product.template.l10n_cr_fe_cabys_descripcion` (Task 2).
- Produces: modelos `l10n_cr.fe.cabys.wizard` (campos `product_id`, `query`, `searched`, `result_ids`) y `l10n_cr.fe.cabys.wizard.line` (campos `wizard_id`, `codigo`, `descripcion`, `impuesto`); métodos `action_buscar(self)` en el wizard y `action_usar(self)` en la línea. Las vistas de Task 4 referencian estos nombres exactos.

**Nota sobre el mecanismo de selección:** el spec (sección 4.2) dejó el mecanismo concreto de "seleccionar una fila y confirmar" a definir en este plan. Se resuelve con un botón "Usar este código" por fila (`action_usar` en `l10n_cr.fe.cabys.wizard.line`) en vez de un radio-select más un botón de confirmación separado: un clic en la fila correcta ya es la selección y la confirmación explícita en un solo acto, cumpliendo el requisito de la sección 1 del spec (nunca asignar sin confirmación del usuario) sin un paso intermedio redundante.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `addons/l10n_cr_fe_crlibre/tests/test_cabys_wizard.py`:

```python
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCabysWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas Demo Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env.user.company_id = self.company
        self.product = self.env['product.template'].create({'name': 'Aguacate Hass'})

    def _patch_buscar(self, resultados):
        return patch(
            'odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.CabysClient.buscar',
            return_value=resultados)

    def test_action_buscar_llena_result_ids(self):
        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({
            'product_id': self.product.id, 'query': 'aguacate',
        })
        resultados = [
            {'codigo': '0131100020400', 'descripcion': 'Aguacate haas, fresco', 'impuesto': 1.0},
            {'codigo': '0131100020100', 'descripcion': 'Aguacate, otro tipo', 'impuesto': 13.0},
        ]
        with self._patch_buscar(resultados):
            wizard.action_buscar()
        self.assertTrue(wizard.searched)
        self.assertEqual(len(wizard.result_ids), 2)
        self.assertEqual(wizard.result_ids[0].codigo, '0131100020400')
        self.assertEqual(wizard.result_ids[0].impuesto, 1.0)

    def test_action_buscar_sin_resultados_deja_searched_true(self):
        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({
            'product_id': self.product.id, 'query': 'xyzxyzxyz',
        })
        with self._patch_buscar([]):
            wizard.action_buscar()
        self.assertTrue(wizard.searched)
        self.assertEqual(len(wizard.result_ids), 0)

    def test_action_buscar_repetido_reemplaza_resultados_anteriores(self):
        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({
            'product_id': self.product.id, 'query': 'aguacate',
        })
        with self._patch_buscar([{'codigo': '0131100020400', 'descripcion': 'x', 'impuesto': 1.0}]):
            wizard.action_buscar()
        with self._patch_buscar([{'codigo': '0131100020100', 'descripcion': 'y', 'impuesto': 13.0}]):
            wizard.action_buscar()
        self.assertEqual(len(wizard.result_ids), 1)
        self.assertEqual(wizard.result_ids[0].codigo, '0131100020100')

    def test_action_buscar_propaga_error_de_red_como_usererror(self):
        from odoo.exceptions import UserError

        from odoo.addons.l10n_cr_fe_crlibre.models.cabys_client import CabysApiError

        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({
            'product_id': self.product.id, 'query': 'aguacate',
        })
        with patch(
            'odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.CabysClient.buscar',
            side_effect=CabysApiError("No se pudo conectar con la API de Hacienda: timeout"),
        ):
            with self.assertRaises(UserError):
                wizard.action_buscar()
        self.assertFalse(wizard.searched)

    def test_action_usar_con_impuesto_configurado_asigna_todo(self):
        tax = self.env['account.tax'].create({
            'name': 'IVA 1%', 'amount_type': 'percent', 'amount': 1.0,
            'type_tax_use': 'sale', 'company_id': self.company.id,
        })
        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({'product_id': self.product.id})
        line = self.env['l10n_cr.fe.cabys.wizard.line'].create({
            'wizard_id': wizard.id, 'codigo': '0131100020400',
            'descripcion': 'Aguacate haas, fresco', 'impuesto': 1.0,
        })
        result = line.action_usar()
        self.assertEqual(result, {'type': 'ir.actions.act_window_close'})
        self.assertEqual(self.product.l10n_cr_fe_cabys, '0131100020400')
        self.assertEqual(self.product.l10n_cr_fe_cabys_descripcion, 'Aguacate haas, fresco')
        self.assertEqual(self.product.taxes_id, tax)

    def test_action_usar_sin_impuesto_configurado_no_lo_toca(self):
        original_taxes = self.product.taxes_id
        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({'product_id': self.product.id})
        line = self.env['l10n_cr.fe.cabys.wizard.line'].create({
            'wizard_id': wizard.id, 'codigo': '0131100020400',
            'descripcion': 'Aguacate haas, fresco', 'impuesto': 1.0,
        })
        line.action_usar()
        self.assertEqual(self.product.l10n_cr_fe_cabys, '0131100020400')
        self.assertEqual(self.product.taxes_id, original_taxes)
        self.assertTrue(any(
            'no existe un impuesto de venta' in (msg.body or '')
            for msg in self.product.message_ids))
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python odoo-bin -d <database> --test-enable --test-tags test_cabys_wizard --stop-after-init -i l10n_cr_fe_crlibre`
Expected: FAIL — `l10n_cr.fe.cabys.wizard` no existe como modelo todavía.

- [ ] **Step 3: Implementar `wizards/cabys_wizard.py`**

```python
from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_cr_fe_crlibre.models.cabys_client import CabysApiError


class L10nCrFeCabysWizard(models.TransientModel):
    _name = 'l10n_cr.fe.cabys.wizard'
    _description = "Buscador de códigos CABYS (Hacienda)"

    product_id = fields.Many2one('product.template', required=True, readonly=True)
    query = fields.Char(string="Buscar (texto o código CABYS)")
    searched = fields.Boolean(default=False)
    result_ids = fields.One2many('l10n_cr.fe.cabys.wizard.line', 'wizard_id')

    def action_buscar(self):
        self.ensure_one()
        client = self.env['l10n_cr.fe.cabys.client']
        try:
            resultados = client.buscar(self.query)
        except CabysApiError as exc:
            raise UserError(str(exc))
        self.result_ids = [(5, 0, 0)] + [(0, 0, {
            'codigo': r['codigo'], 'descripcion': r['descripcion'], 'impuesto': r['impuesto'],
        }) for r in resultados]
        self.searched = True
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_cr.fe.cabys.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }


class L10nCrFeCabysWizardLine(models.TransientModel):
    _name = 'l10n_cr.fe.cabys.wizard.line'
    _description = "Resultado de búsqueda CABYS"

    wizard_id = fields.Many2one('l10n_cr.fe.cabys.wizard', required=True, ondelete='cascade')
    codigo = fields.Char(readonly=True)
    descripcion = fields.Char(readonly=True)
    impuesto = fields.Float(string="IVA %", readonly=True)

    def action_usar(self):
        self.ensure_one()
        product = self.wizard_id.product_id
        product.write({
            'l10n_cr_fe_cabys': self.codigo,
            'l10n_cr_fe_cabys_descripcion': self.descripcion,
        })
        tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', self.impuesto),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if tax:
            product.taxes_id = [(6, 0, tax.ids)]
        else:
            product.message_post(body=_(
                "Código CABYS %s asignado (IVA %.2f%%), pero no existe un impuesto de venta "
                "con esa tarifa configurado en Odoo. Configúrelo para que se use en las facturas."
            ) % (self.codigo, self.impuesto))
        return {'type': 'ir.actions.act_window_close'}
```

Modificar `addons/l10n_cr_fe_crlibre/wizards/__init__.py`:

```python
from . import account_move_reversal
from . import proveedor_upload
from . import mr_motivo_wizard
from . import account_debit_note
from . import cabys_wizard
```

- [ ] **Step 4: Ejecutar los tests y verificar que pasan**

Run: `python odoo-bin -d <database> --test-enable --test-tags test_cabys_wizard --stop-after-init -i l10n_cr_fe_crlibre`
Expected: PASS — 5 tests en verde.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/wizards/cabys_wizard.py addons/l10n_cr_fe_crlibre/wizards/__init__.py addons/l10n_cr_fe_crlibre/tests/test_cabys_wizard.py
git commit -m "feat(l10n_cr_fe_crlibre): agregar wizard de búsqueda y selección de CABYS"
```

---

### Task 4: Vistas, seguridad y registro en el manifiesto

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/views/product_template_views.xml`
- Create: `addons/l10n_cr_fe_crlibre/views/cabys_wizard_views.xml`
- Modify: `addons/l10n_cr_fe_crlibre/security/ir.model.access.csv`
- Modify: `addons/l10n_cr_fe_crlibre/__manifest__.py`
- Test: `addons/l10n_cr_fe_crlibre/tests/test_cabys_wizard.py` (agrega un caso de integración)

**Interfaces:**
- Consumes: `product.template.action_l10n_cr_fe_buscar_cabys` (Task 2); `l10n_cr.fe.cabys.wizard` / `l10n_cr.fe.cabys.wizard.line` (Task 3).
- Produces: módulo instalable de punta a punta desde la interfaz (botón → wizard → selección → producto actualizado).

- [ ] **Step 1: Escribir el test de integración que falla**

Agregar al final de `addons/l10n_cr_fe_crlibre/tests/test_cabys_wizard.py`:

```python
    def test_flujo_completo_boton_producto_hasta_seleccion(self):
        tax = self.env['account.tax'].create({
            'name': 'IVA 1%', 'amount_type': 'percent', 'amount': 1.0,
            'type_tax_use': 'sale', 'company_id': self.company.id,
        })
        action = self.product.action_l10n_cr_fe_buscar_cabys()
        wizard = self.env['l10n_cr.fe.cabys.wizard'].with_context(
            action['context']).create({'query': 'aguacate'})
        self.assertEqual(wizard.product_id, self.product)
        with self._patch_buscar([
            {'codigo': '0131100020400', 'descripcion': 'Aguacate haas, fresco', 'impuesto': 1.0},
        ]):
            wizard.action_buscar()
        wizard.result_ids.action_usar()
        self.assertEqual(self.product.l10n_cr_fe_cabys, '0131100020400')
        self.assertEqual(self.product.taxes_id, tax)
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `python odoo-bin -d <database> --test-enable --test-tags test_cabys_wizard --stop-after-init -i l10n_cr_fe_crlibre`
Expected: el resto de tests de Task 3 sigue pasando; este nuevo caso también debería pasar en lógica pura (no depende de XML), así que en este punto ya PASA — sirve como confirmación de que el flujo Python está completo antes de cablear la interfaz. Si falla, revisar Task 2/3 antes de continuar.

- [ ] **Step 3: Agregar el botón y el campo en el formulario de producto**

Reemplazar el contenido de `addons/l10n_cr_fe_crlibre/views/product_template_views.xml`:

```xml
<odoo>
    <record id="view_product_template_form_l10n_cr_fe" model="ir.ui.view">
        <field name="name">product.template.form.l10n.cr.fe</field>
        <field name="model">product.template</field>
        <field name="inherit_id" ref="product.product_template_form_view"/>
        <field name="arch" type="xml">
            <xpath expr="//group[@name='group_standard_price']/field[@name='categ_id']" position="after">
                <field name="l10n_cr_fe_cabys" string="Código CABYS"/>
                <field name="l10n_cr_fe_cabys_descripcion" string="Descripción CABYS" readonly="1"/>
                <button name="action_l10n_cr_fe_buscar_cabys" type="object"
                        string="Buscar CABYS" class="btn-link" icon="fa-search"/>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: Crear la vista del wizard**

Crear `addons/l10n_cr_fe_crlibre/views/cabys_wizard_views.xml`:

```xml
<odoo>
    <record id="view_l10n_cr_fe_cabys_wizard_form" model="ir.ui.view">
        <field name="name">l10n_cr.fe.cabys.wizard.form</field>
        <field name="model">l10n_cr.fe.cabys.wizard</field>
        <field name="arch" type="xml">
            <form string="Buscar código CABYS">
                <field name="product_id" invisible="1"/>
                <field name="searched" invisible="1"/>
                <group>
                    <field name="query" placeholder="Ej. Aguacate Hass, o un código de 13 dígitos"/>
                </group>
                <button name="action_buscar" string="Buscar" type="object"
                        class="btn-primary" icon="fa-search"/>
                <field name="result_ids" invisible="not searched">
                    <list editable="false" create="false" delete="false">
                        <field name="codigo"/>
                        <field name="descripcion"/>
                        <field name="impuesto" string="IVA %"/>
                        <button name="action_usar" type="object"
                                string="Usar este código" class="btn-link" icon="fa-check"/>
                    </list>
                </field>
                <p invisible="not searched or result_ids">
                    No se encontraron coincidencias para esta búsqueda.
                </p>
                <footer>
                    <button string="Cerrar" special="cancel" class="btn-secondary"/>
                </footer>
            </form>
        </field>
    </record>
</odoo>
```

- [ ] **Step 5: Registrar acceso de seguridad**

Agregar dos filas al final de `addons/l10n_cr_fe_crlibre/security/ir.model.access.csv`:

```csv
access_l10n_cr_fe_cabys_wizard,l10n_cr.fe.cabys.wizard,model_l10n_cr_fe_cabys_wizard,account.group_account_invoice,1,1,1,1
access_l10n_cr_fe_cabys_wizard_line,l10n_cr.fe.cabys.wizard.line,model_l10n_cr_fe_cabys_wizard_line,account.group_account_invoice,1,1,1,1
```

- [ ] **Step 6: Registrar la vista nueva en el manifiesto**

En `addons/l10n_cr_fe_crlibre/__manifest__.py`, agregar `'views/cabys_wizard_views.xml'` a la lista `data`, junto a las otras vistas de wizards:

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
        'views/account_debit_note_views.xml',
        'views/proveedor_upload_views.xml',
        'views/mr_motivo_wizard_views.xml',
        'views/cabys_wizard_views.xml',
        'views/proveedor_email_views.xml',
        'data/mail_template.xml',
    ],
```

- [ ] **Step 7: Actualizar el módulo e instalar las vistas**

Run: `python odoo-bin -d <database> -u l10n_cr_fe_crlibre --stop-after-init`
Expected: termina sin errores (confirma que el XML de las vistas es válido y los `ir.model.access.csv` cargan bien).

- [ ] **Step 8: Ejecutar toda la suite del módulo**

Run: `python odoo-bin -d <database> --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init -i l10n_cr_fe_crlibre`
Expected: PASS — todos los tests existentes del módulo más los nuevos de `test_cabys_client.py` y `test_cabys_wizard.py`.

- [ ] **Step 9: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/views/product_template_views.xml addons/l10n_cr_fe_crlibre/views/cabys_wizard_views.xml addons/l10n_cr_fe_crlibre/security/ir.model.access.csv addons/l10n_cr_fe_crlibre/__manifest__.py addons/l10n_cr_fe_crlibre/tests/test_cabys_wizard.py
git commit -m "feat(l10n_cr_fe_crlibre): cablear vistas, seguridad y manifest del buscador CABYS"
```

---

### Task 5: Verificación manual en la instancia corriendo

**Files:** ninguno (solo verificación en el navegador).

- [ ] **Step 1: Abrir un producto y buscar por texto**

Con la instancia de Odoo levantada (`http://localhost:8069`), ir a Inventario/Ventas → Productos → abrir o crear un producto (ej. "Aguacate Hass"). Pulsar "Buscar CABYS", escribir "Aguacate" en el buscador y pulsar "Buscar". Verificar que aparece una lista de varias coincidencias reales de Hacienda con descripción, código e IVA%.

- [ ] **Step 2: Confirmar una selección**

Pulsar "Usar este código" en una de las filas. Verificar que el wizard se cierra y que el producto queda con `Código CABYS` y `Descripción CABYS` llenos con los valores de la fila elegida.

- [ ] **Step 3: Verificar el caso sin impuesto configurado**

Si la fila elegida tiene IVA 1% (o cualquier tarifa distinta de 13%) y esa empresa no tiene un impuesto de venta de esa tarifa, verificar que el producto igual queda con el CABYS asignado y que aparece un mensaje en el chatter del producto explicando que falta configurar el impuesto.

- [ ] **Step 4: Verificar la búsqueda por código exacto**

Repetir el flujo escribiendo un código de 13 dígitos conocido (ej. `0131100020400`) en el buscador; verificar que devuelve una sola coincidencia exacta.

---
