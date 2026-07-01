# PoC Odoo ↔ API_Hacienda (CRLibre) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Desde una factura de cliente en Odoo, un botón genera la clave de 50 dígitos y el XML de Factura Electrónica v4.4 (sin firmar) llamando a la API_Hacienda de CRLibre, y guarda ambos en la factura.

**Architecture:** Addon Odoo `l10n_cr_fe_crlibre` que extiende `account.move`. Un modelo cliente HTTP llama a dos endpoints `users_openAccess` de la API PHP (`w=clave&r=clave` y `w=genXML&r=gen_xml_fe`) vía `host.docker.internal:8080`. Los datos del emisor y la URL viven en `ir.config_parameter`. No hay firma, token ni envío.

**Tech Stack:** Odoo 19 (Python 3), PostgreSQL, librería `requests` (incluida en Odoo), API_Hacienda (PHP + MariaDB en Docker).

## Global Constraints

- El addon vive en `addons/l10n_cr_fe_crlibre/` (montado en el contenedor Odoo como `/mnt/extra-addons`).
- **No se modifica** el código de la API_Hacienda (es AGPL v3; solo lo consumimos).
- Base de datos Odoo: `odoo`. El contenedor Odoo es `erp-odoo-1`; conexión: `--db_host=db --db_user=odoo --db_password=odoo`.
- Endpoints de la API: `clave` y `gen_xml_fe` son `users_openAccess` (sin login/token/certificado).
- El XML se recibe **codificado en base64** en el campo `xml` de la respuesta; hay que decodificarlo.
- `tipoDocumento` para el PoC = `FE`. `situacion` = `normal`. Moneda por defecto `CRC` con `tipo_cambio` `1`.
- Cada línea de `detalles` DEBE incluir: `codigoCABYS`, `subTotal`, `impuestoAsumidoEmisorFabrica`, `impuestoNeto` (la API los valida y responde error si faltan).
- `license` del addon: `LGPL-3`.
- Comandos Odoo se ejecutan dentro del contenedor con `docker exec erp-odoo-1 ...`.
- **Comando de test (verificado en Task 3):** el servidor ya ocupa 8069, y Git Bash mangla el tag `/modulo`. Usar:
  `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
  Resultado esperado en el log: `0 failed, 0 error(s) of N tests`.

---

## Task 1: Levantar la API y capturar el formato real de respuesta

Objetivo: dejar la API corriendo y documentar el envelope JSON exacto de `clave` y `gen_xml_fe`, para que las tareas siguientes mapeen contra respuestas reales. No hay código Odoo aquí; el deliverable es un archivo de notas con las respuestas reales.

**Files:**
- Create: `docs/superpowers/plans/notes/api-samples.md`

- [ ] **Step 1: Crear `www/settings.php` vacío y levantar el stack de la API**

Run:
```bash
cd /d/API_Hacienda
touch www/settings.php
docker compose up -d
```
Expected: contenedores `crlibre-app` y `crlibre-mariadb` en estado `Up`. Verificar con `docker compose ps`.

- [ ] **Step 2: Smoke test del endpoint de ejemplo**

Run:
```bash
curl -s "http://localhost:8080/api.php?w=ejemplo&r=hola"
```
Expected: una respuesta JSON (no error 500). Si da error de conexión a la BD, revisar que MariaDB cargó `recursos/sql/api_base.sql`.

- [ ] **Step 3: Llamar a `clave` y guardar la respuesta**

Run:
```bash
curl -s "http://localhost:8080/api.php?w=clave&r=clave&tipoDocumento=FE&tipoCedula=fisico&cedula=702320717&consecutivo=1&situacion=normal&codigoSeguridad=12345678&sucursal=001&terminal=00001"
```
Expected: JSON con `clave` (50 dígitos), `consecutivo` (20 dígitos) y `length`. Copiar la salida literal.

- [ ] **Step 4: Llamar a `gen_xml_fe` con un detalle mínimo y guardar la respuesta**

Run (una sola línea):
```bash
curl -s -G "http://localhost:8080/api.php" \
  --data-urlencode "w=genXML" --data-urlencode "r=gen_xml_fe" \
  --data-urlencode "clave=<CLAVE_DEL_PASO_3>" \
  --data-urlencode "proveedor_sistemas=702320717" \
  --data-urlencode "codigo_actividad_emisor=011101" \
  --data-urlencode "consecutivo=<CONSECUTIVO_DEL_PASO_3>" \
  --data-urlencode "fecha_emision=2026-06-30T09:00:00-06:00" \
  --data-urlencode "emisor_nombre=Frutas Demo SA" \
  --data-urlencode "emisor_tipo_identif=01" \
  --data-urlencode "emisor_num_identif=702320717" \
  --data-urlencode "emisor_provincia=1" --data-urlencode "emisor_canton=01" \
  --data-urlencode "emisor_distrito=08" --data-urlencode "emisor_otras_senas=Local demo" \
  --data-urlencode "emisor_email=demo@demo.cr" \
  --data-urlencode "receptor_nombre=Cliente Demo" \
  --data-urlencode "receptor_tipo_identif=01" --data-urlencode "receptor_num_identif=102340567" \
  --data-urlencode "condicion_venta=01" \
  --data-urlencode 'medios_pago=[{"tipoMedioPago":"01","totalMedioPago":1130.00}]' \
  --data-urlencode "cod_moneda=CRC" --data-urlencode "tipo_cambio=1" \
  --data-urlencode "total_ventas=1000.00" --data-urlencode "total_ventas_neta=1000.00" \
  --data-urlencode "total_comprobante=1130.00" \
  --data-urlencode 'detalles=[{"codigoCABYS":"0111101000000","cantidad":1,"unidadMedida":"Unid","detalle":"Producto demo","precioUnitario":1000.00,"montoTotal":1000.00,"subTotal":1000.00,"baseImponible":1000.00,"impuesto":[{"codigo":"01","codigoTarifa":"08","tarifa":13,"monto":130.00}],"impuestoAsumidoEmisorFabrica":0,"impuestoNeto":130.00,"montoTotalLinea":1130.00}]'
```
Expected: JSON con `clave` y `xml` (base64). Decodificar el `xml` con `echo '<base64>' | base64 -d` y confirmar que empieza con `<FacturaElectronica` y contiene el namespace `v4.4`.

- [ ] **Step 5: Documentar y commitear las muestras**

Escribir en `docs/superpowers/plans/notes/api-samples.md`:
- La URL de cada llamada.
- El JSON de respuesta literal de `clave` y de `gen_xml_fe`.
- El nombre exacto de las claves del envelope (p. ej. si la respuesta es `{"clave":...}` directo o viene envuelta en `{"response":...}`).

```bash
cd /d/ERP
git add docs/superpowers/plans/notes/api-samples.md
git commit -m "docs: capturar formato real de respuestas clave y gen_xml_fe de API_Hacienda"
```

---

## Task 2: Scaffold del addon e instalación

**Files:**
- Create: `addons/l10n_cr_fe_crlibre/__init__.py`
- Create: `addons/l10n_cr_fe_crlibre/__manifest__.py`
- Create: `addons/l10n_cr_fe_crlibre/models/__init__.py`

**Interfaces:**
- Produces: módulo Odoo instalable `l10n_cr_fe_crlibre`.

- [ ] **Step 1: Crear `__manifest__.py`**

```python
# Part of the PoC integration Odoo <-> API_Hacienda (CRLibre).
{
    'name': "Costa Rica - Factura Electrónica (PoC CRLibre)",
    'version': '19.0.1.0.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': "PoC: genera clave y XML de FE v4.4 vía API_Hacienda de CRLibre",
    'depends': ['account', 'l10n_cr'],
    'data': [
        'data/config_params.xml',
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
```

- [ ] **Step 2: Crear los `__init__.py`**

`addons/l10n_cr_fe_crlibre/__init__.py`:
```python
from . import models
```

`addons/l10n_cr_fe_crlibre/models/__init__.py`:
```python
from . import crlibre_client
from . import account_move
```

- [ ] **Step 3: Crear placeholders vacíos para que el módulo cargue**

Crear `addons/l10n_cr_fe_crlibre/models/crlibre_client.py` con:
```python
from odoo import models
```
Crear `addons/l10n_cr_fe_crlibre/models/account_move.py` con:
```python
from odoo import models
```
Crear `addons/l10n_cr_fe_crlibre/data/config_params.xml` con:
```xml
<odoo noupdate="1"></odoo>
```
Crear `addons/l10n_cr_fe_crlibre/views/account_move_views.xml` con:
```xml
<odoo></odoo>
```

- [ ] **Step 4: Instalar el módulo**

Run:
```bash
docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -i l10n_cr_fe_crlibre --stop-after-init
```
Expected: en el log, `Module l10n_cr_fe_crlibre loaded` y `Modules loaded.` sin tracebacks.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre
git commit -m "feat(l10n_cr_fe): scaffold del addon PoC de factura electrónica CR"
```

---

## Task 3: Cliente HTTP `l10n_cr.fe.client`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`
- Create: `addons/l10n_cr_fe_crlibre/tests/__init__.py`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`

**Interfaces:**
- Consumes: `ir.config_parameter` `l10n_cr_fe.api_url`.
- Produces:
  - `AbstractModel` `l10n_cr.fe.client` con:
    - `_get_base_url(self) -> str`
    - `get_clave(self, params: dict) -> dict` → `{'clave': str, 'consecutivo': str}`
    - `gen_xml_fe(self, params: dict) -> str` (XML ya decodificado de base64)
  - excepción `CrlibreApiError(Exception)`

> Nota: los nombres de clave del envelope (`clave`, `consecutivo`, `xml`) se toman de `docs/superpowers/plans/notes/api-samples.md` (Task 1). Si el envelope viene anidado, ajustar `_parse` en el Step 3 según lo documentado.

- [ ] **Step 1: Escribir el test que falla**

`addons/l10n_cr_fe_crlibre/tests/__init__.py`:
```python
from . import test_crlibre_client
```

`addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`:
```python
from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client import CrlibreApiError


@tagged('post_install', '-at_install')
class TestCrlibreClient(TransactionCase):

    def setUp(self):
        super().setUp()
        self.client = self.env['l10n_cr.fe.client']
        self.env['ir.config_parameter'].sudo().set_param(
            'l10n_cr_fe.api_url', 'http://host.docker.internal:8080')

    def _mock_response(self, json_data, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = json_data
        return resp

    def test_get_clave_returns_clave_and_consecutivo(self):
        # La API envuelve los datos en {"status":"ok","resp":{...}}
        payload = {'status': 'ok', 'resp': {'clave': '5' * 50, 'consecutivo': '0' * 20, 'length': 50}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.get_clave({'tipoDocumento': 'FE'})
        self.assertEqual(result['clave'], '5' * 50)
        self.assertEqual(result['consecutivo'], '0' * 20)
        m.assert_called_once()

    def test_gen_xml_fe_decodes_base64(self):
        import base64
        xml = '<FacturaElectronica>ok</FacturaElectronica>'
        payload = {'status': 'ok',
                   'resp': {'clave': '5' * 50, 'xml': base64.b64encode(xml.encode()).decode()}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)):
            result = self.client.gen_xml_fe({'clave': '5' * 50})
        self.assertEqual(result, xml)

    def test_http_error_raises(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response({}, status=500)):
            with self.assertRaises(CrlibreApiError):
                self.client.get_clave({'tipoDocumento': 'FE'})
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run:
```bash
docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init
```
Expected: FALLA (ImportError de `CrlibreApiError` o el modelo `l10n_cr.fe.client` no existe).

- [ ] **Step 3: Implementar el cliente**

`addons/l10n_cr_fe_crlibre/models/crlibre_client.py`:
```python
import base64
import logging

import requests

from odoo import models

_logger = logging.getLogger(__name__)

TIMEOUT = 30


class CrlibreApiError(Exception):
    """Error al comunicarse con la API_Hacienda de CRLibre."""


class CrlibreFeClient(models.AbstractModel):
    _name = 'l10n_cr.fe.client'
    _description = 'Cliente HTTP para la API_Hacienda (CRLibre)'

    def _get_base_url(self):
        url = self.env['ir.config_parameter'].sudo().get_param('l10n_cr_fe.api_url')
        if not url:
            raise CrlibreApiError("Falta configurar 'l10n_cr_fe.api_url'.")
        return url.rstrip('/')

    def _call(self, w, r, params):
        query = dict(params or {})
        query['w'] = w
        query['r'] = r
        url = self._get_base_url() + '/api.php'
        try:
            resp = requests.get(url, params=query, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise CrlibreApiError("No se pudo conectar con la API: %s" % exc)
        if resp.status_code != 200:
            raise CrlibreApiError("La API respondió HTTP %s" % resp.status_code)
        try:
            data = resp.json()
        except ValueError:
            raise CrlibreApiError("La API devolvió una respuesta no-JSON.")
        # La API envuelve todo en {"status": "...", "resp": <datos>} (ver Task 1 / api-samples.md)
        if not isinstance(data, dict) or data.get('status') != 'ok':
            raise CrlibreApiError("La API respondió estado no-ok: %s" % data)
        return data.get('resp')

    def get_clave(self, params):
        resp = self._call('clave', 'clave', params)
        if not isinstance(resp, dict) or not resp.get('clave'):
            raise CrlibreApiError("Respuesta inesperada de 'clave': %s" % resp)
        return {'clave': resp['clave'], 'consecutivo': resp.get('consecutivo', '')}

    def gen_xml_fe(self, params):
        resp = self._call('genXML', 'gen_xml_fe', params)
        if not isinstance(resp, dict) or not resp.get('xml'):
            raise CrlibreApiError("Respuesta inesperada de 'gen_xml_fe': %s" % resp)
        return base64.b64decode(resp['xml']).decode('utf-8')
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run:
```bash
docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init
```
Expected: los 3 tests PASAN.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/crlibre_client.py addons/l10n_cr_fe_crlibre/tests
git commit -m "feat(l10n_cr_fe): cliente HTTP para clave y gen_xml_fe con tests"
```

---

## Task 4: Parámetros de configuración del emisor

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/data/config_params.xml`

**Interfaces:**
- Produces: `ir.config_parameter` sembrados: `l10n_cr_fe.api_url`, `l10n_cr_fe.proveedor_sistemas`, `l10n_cr_fe.emisor_*`, `l10n_cr_fe.default_cabys`.

- [ ] **Step 1: Escribir el data file**

`addons/l10n_cr_fe_crlibre/data/config_params.xml`:
```xml
<odoo noupdate="1">
    <record id="param_api_url" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.api_url</field>
        <field name="value">http://host.docker.internal:8080</field>
    </record>
    <record id="param_proveedor_sistemas" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.proveedor_sistemas</field>
        <field name="value">702320717</field>
    </record>
    <record id="param_emisor_cedula" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.emisor_cedula</field>
        <field name="value">702320717</field>
    </record>
    <record id="param_emisor_tipo_identif" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.emisor_tipo_identif</field>
        <field name="value">01</field>
    </record>
    <record id="param_emisor_nombre" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.emisor_nombre</field>
        <field name="value">Frutas Demo SA</field>
    </record>
    <record id="param_emisor_actividad" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.emisor_codigo_actividad</field>
        <field name="value">011101</field>
    </record>
    <record id="param_emisor_provincia" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.emisor_provincia</field>
        <field name="value">1</field>
    </record>
    <record id="param_emisor_canton" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.emisor_canton</field>
        <field name="value">01</field>
    </record>
    <record id="param_emisor_distrito" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.emisor_distrito</field>
        <field name="value">08</field>
    </record>
    <record id="param_emisor_otras_senas" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.emisor_otras_senas</field>
        <field name="value">Local de demostración</field>
    </record>
    <record id="param_emisor_email" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.emisor_email</field>
        <field name="value">demo@frutasdemo.cr</field>
    </record>
    <record id="param_default_cabys" model="ir.config_parameter">
        <field name="key">l10n_cr_fe.default_cabys</field>
        <field name="value">0111101000000</field>
    </record>
</odoo>
```

- [ ] **Step 2: Actualizar el módulo y verificar los parámetros**

Run:
```bash
docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --stop-after-init
docker exec erp-odoo-1 odoo shell -d odoo --db_host=db --db_user=odoo --db_password=odoo -c "print(env['ir.config_parameter'].sudo().get_param('l10n_cr_fe.emisor_cedula'))" --stop-after-init 2>/dev/null | tail -1
```
Expected: imprime `702320717`.

- [ ] **Step 3: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/data/config_params.xml
git commit -m "feat(l10n_cr_fe): parámetros de configuración del emisor para el PoC"
```

---

## Task 5: Mapeo factura → parámetros de la API

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`

**Interfaces:**
- Consumes: `ir.config_parameter` `l10n_cr_fe.*` (Task 4).
- Produces (en `account.move`):
  - campos `l10n_cr_fe_clave` (Char), `l10n_cr_fe_consecutivo` (Char), `l10n_cr_fe_xml` (Text), `l10n_cr_fe_state` (Selection).
  - `_l10n_cr_fe_param(self, key) -> str`
  - `_l10n_cr_fe_build_detalles(self) -> list[dict]`
  - `_l10n_cr_fe_build_clave_params(self) -> dict`
  - `_l10n_cr_fe_build_genxml_params(self, clave, consecutivo, detalles) -> dict`

- [ ] **Step 1: Escribir el test que falla**

Agregar a `addons/l10n_cr_fe_crlibre/tests/__init__.py`:
```python
from . import test_crlibre_client
from . import test_account_move_mapping
```

`addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`:
```python
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountMoveMapping(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Cliente Demo',
            'vat': '102340567',
        })
        product = self.env['product.product'].create({'name': 'Producto demo'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 1,
                'price_unit': 1000.0,
                'name': 'Producto demo',
            })],
        })

    def test_build_detalles_has_required_fields(self):
        detalles = self.invoice._l10n_cr_fe_build_detalles()
        self.assertEqual(len(detalles), 1)
        d = detalles[0]
        for field in ('codigoCABYS', 'subTotal', 'impuestoAsumidoEmisorFabrica',
                      'impuestoNeto', 'cantidad', 'unidadMedida', 'detalle',
                      'precioUnitario', 'montoTotal', 'montoTotalLinea'):
            self.assertIn(field, d)
        self.assertEqual(d['cantidad'], 1.0)
        self.assertEqual(d['precioUnitario'], 1000.0)

    def test_build_clave_params(self):
        params = self.invoice._l10n_cr_fe_build_clave_params()
        self.assertEqual(params['tipoDocumento'], 'FE')
        self.assertEqual(params['situacion'], 'normal')
        self.assertEqual(params['cedula'], '702320717')
        self.assertEqual(len(params['codigoSeguridad']), 8)
        self.assertTrue(params['codigoSeguridad'].isdigit())

    def test_build_genxml_params_serializes_detalles(self):
        import json
        detalles = self.invoice._l10n_cr_fe_build_detalles()
        params = self.invoice._l10n_cr_fe_build_genxml_params('5' * 50, '0' * 20, detalles)
        self.assertEqual(params['clave'], '5' * 50)
        self.assertEqual(params['consecutivo'], '0' * 20)
        self.assertEqual(params['receptor_num_identif'], '102340567')
        # detalles y medios_pago van serializados como JSON string
        self.assertIsInstance(params['detalles'], str)
        self.assertEqual(json.loads(params['detalles'])[0]['codigoCABYS'], '0111101000000')
        self.assertIsInstance(params['medios_pago'], str)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run:
```bash
docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init
```
Expected: FALLA (los métodos `_l10n_cr_fe_*` no existen).

- [ ] **Step 3: Implementar campos y mapeo**

`addons/l10n_cr_fe_crlibre/models/account_move.py`:
```python
import json
import random
from datetime import datetime

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_cr_fe_clave = fields.Char(string="Clave FE", readonly=True, copy=False)
    l10n_cr_fe_consecutivo = fields.Char(string="Consecutivo FE", readonly=True, copy=False)
    l10n_cr_fe_xml = fields.Text(string="XML FE", readonly=True, copy=False)
    l10n_cr_fe_state = fields.Selection(
        selection=[('draft', "Borrador"), ('generated', "Generado"), ('error', "Error")],
        string="Estado FE", default='draft', readonly=True, copy=False)

    def _l10n_cr_fe_param(self, key):
        return self.env['ir.config_parameter'].sudo().get_param('l10n_cr_fe.' + key) or ''

    def _l10n_cr_fe_build_detalles(self):
        self.ensure_one()
        cabys = self._l10n_cr_fe_param('default_cabys')
        detalles = []
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            subtotal = line.price_subtotal
            impuesto_neto = line.price_total - line.price_subtotal
            detalle = {
                'codigoCABYS': cabys,
                'cantidad': line.quantity,
                'unidadMedida': 'Unid',
                'detalle': line.name or (line.product_id.display_name or 'Producto'),
                'precioUnitario': line.price_unit,
                'montoTotal': line.price_unit * line.quantity,
                'subTotal': subtotal,
                'baseImponible': subtotal,
                'impuestoAsumidoEmisorFabrica': 0,
                'impuestoNeto': impuesto_neto,
                'montoTotalLinea': line.price_total,
            }
            if impuesto_neto:
                detalle['impuesto'] = [{
                    'codigo': '01',
                    'codigoTarifa': '08',
                    'tarifa': 13,
                    'monto': impuesto_neto,
                }]
            detalles.append(detalle)
        return detalles

    def _l10n_cr_fe_build_clave_params(self):
        self.ensure_one()
        return {
            'tipoDocumento': 'FE',
            'tipoCedula': self._l10n_cr_fe_param('emisor_tipo_identif') == '02' and 'juridico' or 'fisico',
            'cedula': self._l10n_cr_fe_param('emisor_cedula'),
            'situacion': 'normal',
            'consecutivo': str(self.id),
            'codigoSeguridad': str(random.randint(0, 99999999)).zfill(8),
            'sucursal': '001',
            'terminal': '00001',
        }

    def _l10n_cr_fe_build_genxml_params(self, clave, consecutivo, detalles):
        self.ensure_one()
        fecha = fields.Datetime.context_timestamp(self, datetime.now())
        total = self.amount_total
        base = self.amount_untaxed
        medios_pago = [{'tipoMedioPago': '01', 'totalMedioPago': total}]
        return {
            'clave': clave,
            'proveedor_sistemas': self._l10n_cr_fe_param('proveedor_sistemas'),
            'codigo_actividad_emisor': self._l10n_cr_fe_param('emisor_codigo_actividad'),
            'consecutivo': consecutivo,
            'fecha_emision': fecha.strftime('%Y-%m-%dT%H:%M:%S-06:00'),
            'emisor_nombre': self._l10n_cr_fe_param('emisor_nombre'),
            'emisor_tipo_identif': self._l10n_cr_fe_param('emisor_tipo_identif'),
            'emisor_num_identif': self._l10n_cr_fe_param('emisor_cedula'),
            'emisor_provincia': self._l10n_cr_fe_param('emisor_provincia'),
            'emisor_canton': self._l10n_cr_fe_param('emisor_canton'),
            'emisor_distrito': self._l10n_cr_fe_param('emisor_distrito'),
            'emisor_otras_senas': self._l10n_cr_fe_param('emisor_otras_senas'),
            'emisor_email': self._l10n_cr_fe_param('emisor_email'),
            'receptor_nombre': self.partner_id.name or '',
            'receptor_tipo_identif': '01',
            'receptor_num_identif': (self.partner_id.vat or '').replace('-', '') or '000000000',
            'condicion_venta': '01',
            'medios_pago': json.dumps(medios_pago),
            'cod_moneda': self.currency_id.name or 'CRC',
            'tipo_cambio': '1',
            'total_ventas': base,
            'total_ventas_neta': base,
            'total_comprobante': total,
            'detalles': json.dumps(detalles),
        }
```

> Nota de implementación: en Odoo 19 las líneas de sección/nota tienen `display_type` distinto de `'product'`; el filtro las excluye. Verificar el valor real de `display_type` para líneas normales en esta versión antes de dar por bueno el test (si difiere, ajustar el filtro).

- [ ] **Step 4: Correr el test y verificar que pasa**

Run:
```bash
docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init
```
Expected: los tests de mapeo PASAN.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests
git commit -m "feat(l10n_cr_fe): campos FE y mapeo factura->parámetros de la API"
```

---

## Task 6: Orquestación del botón `action_l10n_cr_fe_generate`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_generate_action.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`

**Interfaces:**
- Consumes: `l10n_cr.fe.client.get_clave`, `l10n_cr.fe.client.gen_xml_fe` (Task 3); métodos de mapeo (Task 5).
- Produces: `action_l10n_cr_fe_generate(self)` que llena `l10n_cr_fe_clave`, `l10n_cr_fe_consecutivo`, `l10n_cr_fe_xml`, `l10n_cr_fe_state` y postea en el chatter.

- [ ] **Step 1: Escribir el test que falla**

Agregar a `addons/l10n_cr_fe_crlibre/tests/__init__.py`:
```python
from . import test_generate_action
```

`addons/l10n_cr_fe_crlibre/tests/test_generate_action.py`:
```python
from unittest.mock import patch
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError
from odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client import CrlibreApiError


@tagged('post_install', '-at_install')
class TestGenerateAction(TransactionCase):

    def setUp(self):
        super().setUp()
        partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        product = self.env['product.product'].create({'name': 'Producto demo'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo',
            })],
        })

    def test_generate_success(self):
        clave = '5' * 50
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                   return_value={'clave': clave, 'consecutivo': '0' * 20}), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_fe',
                   return_value='<FacturaElectronica>ok</FacturaElectronica>'):
            self.invoice.action_l10n_cr_fe_generate()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'generated')
        self.assertEqual(self.invoice.l10n_cr_fe_clave, clave)
        self.assertIn('FacturaElectronica', self.invoice.l10n_cr_fe_xml)

    def test_generate_api_error_sets_state_error(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                   side_effect=CrlibreApiError('boom')):
            with self.assertRaises(UserError):
                self.invoice.action_l10n_cr_fe_generate()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'error')
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run:
```bash
docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init
```
Expected: FALLA (`action_l10n_cr_fe_generate` no existe).

- [ ] **Step 3: Implementar la orquestación**

Agregar los imports y el método a `addons/l10n_cr_fe_crlibre/models/account_move.py`.

Al inicio del archivo, junto a los imports existentes, añadir:
```python
from odoo.exceptions import UserError
from .crlibre_client import CrlibreApiError
```

Agregar dentro de la clase `AccountMove`:
```python
    def action_l10n_cr_fe_generate(self):
        self.ensure_one()
        if self.move_type != 'out_invoice':
            raise UserError("Solo aplica a facturas de cliente.")
        if not self.partner_id:
            raise UserError("La factura no tiene cliente (receptor).")
        client = self.env['l10n_cr.fe.client']
        try:
            clave_params = self._l10n_cr_fe_build_clave_params()
            clave_res = client.get_clave(clave_params)
            detalles = self._l10n_cr_fe_build_detalles()
            genxml_params = self._l10n_cr_fe_build_genxml_params(
                clave_res['clave'], clave_res['consecutivo'], detalles)
            xml = client.gen_xml_fe(genxml_params)
        except CrlibreApiError as exc:
            self.l10n_cr_fe_state = 'error'
            self.message_post(body="Error al generar el comprobante FE: %s" % exc)
            raise UserError("No se pudo generar el comprobante: %s" % exc)
        self.write({
            'l10n_cr_fe_clave': clave_res['clave'],
            'l10n_cr_fe_consecutivo': clave_res['consecutivo'],
            'l10n_cr_fe_xml': xml,
            'l10n_cr_fe_state': 'generated',
        })
        self.message_post(body="Comprobante FE generado (PoC). Clave: %s" % clave_res['clave'])
        return True
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run:
```bash
docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init
```
Expected: todos los tests PASAN.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests
git commit -m "feat(l10n_cr_fe): acción de generación con manejo de errores y tests"
```

---

## Task 7: Vista — botón y campos en la factura

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`

**Interfaces:**
- Consumes: campos y acción de Tasks 5 y 6.

- [ ] **Step 1: Escribir la vista**

`addons/l10n_cr_fe_crlibre/views/account_move_views.xml`:
```xml
<odoo>
    <record id="view_move_form_l10n_cr_fe" model="ir.ui.view">
        <field name="name">account.move.form.l10n.cr.fe</field>
        <field name="model">account.move</field>
        <field name="inherit_id" ref="account.view_move_form"/>
        <field name="arch" type="xml">
            <xpath expr="//header" position="inside">
                <button name="action_l10n_cr_fe_generate"
                        string="Generar comprobante (PoC)"
                        type="object" class="btn-primary"
                        invisible="move_type != 'out_invoice'"/>
                <field name="l10n_cr_fe_state" widget="statusbar"
                       invisible="move_type != 'out_invoice'"/>
            </xpath>
            <xpath expr="//notebook" position="inside">
                <page string="Factura Electrónica CR"
                      invisible="move_type != 'out_invoice'">
                    <group>
                        <field name="l10n_cr_fe_clave"/>
                        <field name="l10n_cr_fe_consecutivo"/>
                    </group>
                    <field name="l10n_cr_fe_xml"/>
                </page>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 2: Actualizar el módulo y verificar que la vista carga**

Run:
```bash
docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --stop-after-init
```
Expected: sin errores de parseo de vista (`ParseError`) en el log; termina en `Modules loaded.`

- [ ] **Step 3: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/views/account_move_views.xml
git commit -m "feat(l10n_cr_fe): botón y pestaña FE en el formulario de factura"
```

---

## Task 8: Verificación manual end-to-end

Objetivo: probar el flujo real Odoo → API con una factura de prueba. No hay commit de código; el deliverable es la confirmación.

**Files:** (ninguno)

- [ ] **Step 1: Confirmar ambos stacks arriba**

Run:
```bash
docker ps --format "{{.Names}} {{.Status}}" | grep -E "erp-odoo-1|crlibre-app|crlibre-mariadb"
```
Expected: los tres contenedores `Up`.

- [ ] **Step 2: Confirmar conectividad Odoo → API**

Run:
```bash
docker exec erp-odoo-1 python3 -c "import requests; print(requests.get('http://host.docker.internal:8080/api.php?w=ejemplo&r=hola', timeout=10).status_code)"
```
Expected: `200`. Si falla, revisar la nota de red en la spec (limitación #8) y confirmar que `host.docker.internal` resuelve desde el contenedor Odoo.

- [ ] **Step 3: Probar en la interfaz**

En `http://localhost:8069`:
1. Contabilidad → Clientes → Facturas → Nueva.
2. Elegir/crear un cliente con cédula (VAT) numérica, agregar una línea de producto con precio.
3. Guardar.
4. Pulsar **"Generar comprobante (PoC)"**.

Expected: el estado FE pasa a **Generado**; la pestaña "Factura Electrónica CR" muestra una clave de 50 dígitos y el XML; el chatter registra la clave.

- [ ] **Step 4: Validar el XML**

Copiar el contenido de `l10n_cr_fe_xml` y confirmar que:
- Empieza con `<FacturaElectronica` y declara el namespace `v4.4`.
- La `<Clave>` tiene 50 dígitos.
- Contiene `<Emisor>`, `<Receptor>`, al menos un `<LineaDetalle>` y `<ResumenFactura>`.

- [ ] **Step 5: Registrar el resultado**

Anotar en `docs/superpowers/plans/notes/api-samples.md` la clave generada y un extracto del XML como evidencia del PoC funcionando.

```bash
git add docs/superpowers/plans/notes/api-samples.md
git commit -m "docs: evidencia del PoC FE end-to-end funcionando"
```

---

## Notas de cierre

- **Fuera de alcance** (fases futuras, ver spec §9): firma XAdES con `.p12`, token OAuth, envío a Hacienda, consulta de estado, gestión real de consecutivos, mapeo de catálogos (CABYS, ubicación, unidades, impuestos), datos del emisor desde `res.company`.
- **Riesgo abierto a validar en Task 1:** el envelope exacto de las respuestas JSON. Todo el parseo en `crlibre_client.py` asume `{'clave':...}`, `{'consecutivo':...}`, `{'xml':<base64>}` a nivel raíz. Si Task 1 revela otra estructura, ajustar `get_clave`/`gen_xml_fe` antes de continuar.
- **CABYS y `codigo_actividad`** usan valores placeholder; para uso real deben corresponder a la actividad económica y a los productos reales de la empresa.
