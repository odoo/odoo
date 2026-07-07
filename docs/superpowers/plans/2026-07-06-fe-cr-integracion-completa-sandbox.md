# Integración completa FE CR (sandbox) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Al confirmar una factura de cliente en Odoo, generar clave+XML, firmarlo con el certificado `.p12` de la empresa, enviarlo al sandbox de Hacienda, permitir consultar su estado y, al ser aceptado, notificar al cliente por correo — todo con datos tributarios cargados desde Odoo por empresa (multi-company).

**Architecture:** Se extiende el addon existente `l10n_cr_fe_crlibre`. Un nuevo modelo `l10n_cr.fe.config` (1-a-1 con `res.company`) reemplaza los `ir.config_parameter` globales del PoC. El `AbstractModel` `l10n_cr.fe.client` gana métodos nuevos para cada endpoint de la API_Hacienda (`token`, `firmarXML`, `send`, `consultar`, más el registro/login/subida de certificado en el sistema de usuarios interno de la API). `account.move` orquesta todo desde `action_post()`.

**Tech Stack:** Odoo 19 (Python 3), PostgreSQL, `requests`, API_Hacienda (PHP, en `D:\API_Hacienda`, stack Docker aparte ya corriendo), sandbox de Hacienda (`api-sandbox.comprobanteselectronicos.go.cr`, IDP `idp.comprobanteselectronicos.go.cr`).

## Global Constraints

- El addon vive en `addons/l10n_cr_fe_crlibre/` (ya existe; se extiende, no se crea uno nuevo).
- **No se modifica el código AGPL de `D:\API_Hacienda`** salvo arreglos de infraestructura evidentes que restauren el comportamiento previsto (mismo criterio ya aplicado en el PoC: Dockerfile, entrypoint CRLF, `settings.php`, carpetas faltantes). Cualquier parche de este tipo se documenta explícitamente con su justificación, y vive en el repo `D:\API_Hacienda` (fuera de `d:\ERP`), no se commitea en este repo.
- **Las credenciales reales nunca se escriben en código, specs, planes, ni se pasan como texto plano en comandos que ejecute el asistente.** Los pasos que las requieren están marcados **"EJECUCIÓN MANUAL DEL USUARIO"** y usan placeholders (`<TU_USUARIO_STAG>`, `<TU_PIN>`, etc.) que el usuario reemplaza al ejecutar él mismo el comando, fuera de la conversación con el asistente si es posible.
- Comandos Odoo dentro del contenedor: `docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo ...`.
- **Comando de test** (heredado del PoC — el servidor ocupa 8069 y Git Bash mangla `/modulo`):
  `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
  Resultado esperado: `0 failed, 0 error(s) of N tests`.
- Tras cambiar código del addon, **reiniciar `erp-odoo-1`** (`docker restart erp-odoo-1`) antes de probar manualmente en el navegador (lección operativa ya documentada en el PoC: el proceso de test/update no refresca el servidor que atiende al navegador).
- El envelope de la API_Hacienda es siempre `{"status": "ok"|"error", "resp": <datos>}` a nivel de framework (confirmado en `api/core/tools.php`), para **todos** los endpoints, incluidos los nuevos de esta fase.
- Cualquier llamada a un endpoint con `access: users_loggedIn` de la API (ej. `fileUploader/subir_certif`) debe incluir `iam=<userName>` y `sessionKey=<sessionKey>` como parámetros (confirmado en `api/modules/users/module.php` y `api/core/boot.php`).
- El campo multipart para subir el certificado debe llamarse exactamente `fileToUpload` (fijo en `api/modules/files/module.php`, no configurable).
- `w=users` para registro/login (`api/modules/users/module.php`), `w=fileUploader` para la subida (`api/contrib/fileUploader/module.php`), `w=token` (`api/contrib/token/`), `w=firmarXML` (`api/contrib/firmarXML/`), `w=send` (`api/contrib/send/`), `w=consultar` (`api/contrib/consultar/`).

---

## Task 1: Modelo `l10n_cr.fe.config` — datos tributarios por empresa

**Files:**
- Create: `addons/l10n_cr_fe_crlibre/models/fe_config.py`
- Create: `addons/l10n_cr_fe_crlibre/security/l10n_cr_fe_security.xml`
- Create: `addons/l10n_cr_fe_crlibre/security/ir.model.access.csv`
- Create: `addons/l10n_cr_fe_crlibre/views/fe_config_views.xml`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_fe_config.py`
- Modify: `addons/l10n_cr_fe_crlibre/models/__init__.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`
- Modify: `addons/l10n_cr_fe_crlibre/__manifest__.py`

**Interfaces:**
- Produces: modelo `l10n_cr.fe.config` con `company_id` (Many2one `res.company`, único), campos tributarios, y el método `_get_for_company(self, company)` usado por tareas posteriores.
- Produces: grupo de seguridad `l10n_cr_fe.group_fe_admin`.

- [ ] **Step 1: Escribir el test que falla**

`addons/l10n_cr_fe_crlibre/tests/test_fe_config.py`:
```python
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFeConfig(TransactionCase):

    def setUp(self):
        super().setUp()
        self.config = self.env['l10n_cr.fe.config'].create({
            'company_id': self.env.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '208400858',
            'legal_name': 'Empresa Demo SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de prueba',
            'phone': '22220000', 'email': 'demo@empresa.cr',
            'hacienda_username': 'user@stag.comprobanteselectronicos.go.cr',
            'hacienda_password': 'secret',
            'certificate_pin': '1234',
        })

    def test_get_for_company_returns_config(self):
        found = self.env['l10n_cr.fe.config']._get_for_company(self.env.company)
        self.assertEqual(found, self.config)

    def test_get_for_company_raises_when_missing(self):
        other_company = self.env['res.company'].create({'name': 'Otra Empresa'})
        with self.assertRaises(UserError):
            self.env['l10n_cr.fe.config']._get_for_company(other_company)

    def test_company_id_is_unique(self):
        with self.assertRaises(Exception):
            self.env['l10n_cr.fe.config'].create({
                'company_id': self.env.company.id,
                'environment': 'stag',
                'identification_type': '01',
                'identification_number': '111111111',
            })

    def test_restricted_fields_hidden_from_non_admin(self):
        plain_user = self.env['res.users'].create({
            'name': 'Usuario Normal', 'login': 'usuario_normal_fe_test',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        with self.assertRaises(AccessError):
            self.config.with_user(plain_user).read(['hacienda_password'])
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run:
```bash
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init
```
Expected: FALLA (el modelo `l10n_cr.fe.config` no existe / import error).

- [ ] **Step 3: Crear el grupo de seguridad**

`addons/l10n_cr_fe_crlibre/security/l10n_cr_fe_security.xml`:
```xml
<odoo>
    <record id="module_category_l10n_cr_fe" model="ir.module.category">
        <field name="name">Facturación Electrónica CR</field>
    </record>
    <record id="group_fe_admin" model="res.groups">
        <field name="name">Administrador</field>
        <field name="category_id" ref="module_category_l10n_cr_fe"/>
        <field name="comment">Puede ver y editar credenciales y certificado de Factura Electrónica.</field>
    </record>
</odoo>
```

- [ ] **Step 4: Implementar el modelo**

`addons/l10n_cr_fe_crlibre/models/fe_config.py`:
```python
from odoo import fields, models, _
from odoo.exceptions import UserError


class L10nCrFeConfig(models.Model):
    _name = 'l10n_cr.fe.config'
    _description = 'Configuración de Factura Electrónica CR por empresa'

    company_id = fields.Many2one('res.company', required=True, ondelete='cascade')
    environment = fields.Selection(
        selection=[('stag', 'Sandbox (stag)'), ('prod', 'Producción')],
        string="Ambiente", required=True, default='stag')

    identification_type = fields.Selection(
        selection=[('01', 'Física'), ('02', 'Jurídica'), ('03', 'DIMEX'), ('04', 'NITE')],
        string="Tipo de identificación", required=True)
    identification_number = fields.Char(string="Cédula", required=True)
    legal_name = fields.Char(string="Razón social", required=True)
    trade_name = fields.Char(string="Nombre comercial")
    economic_activity_code = fields.Char(string="Código de actividad económica", required=True)

    province = fields.Char(string="Provincia", required=True)
    canton = fields.Char(string="Cantón", required=True)
    district = fields.Char(string="Distrito", required=True)
    neighborhood = fields.Char(string="Barrio", required=True)
    address_detail = fields.Char(string="Otras señas", required=True)
    phone = fields.Char(string="Teléfono")
    email = fields.Char(string="Correo electrónico", required=True)

    branch_number = fields.Char(string="Sucursal", default='001', required=True)
    terminal_number = fields.Char(string="Terminal", default='00001', required=True)

    hacienda_username = fields.Char(
        string="Usuario Hacienda", groups='l10n_cr_fe_crlibre.group_fe_admin')
    hacienda_password = fields.Char(
        string="Contraseña Hacienda", groups='l10n_cr_fe_crlibre.group_fe_admin')
    certificate_file = fields.Binary(
        string="Certificado .p12", groups='l10n_cr_fe_crlibre.group_fe_admin')
    certificate_filename = fields.Char(string="Nombre del archivo")
    certificate_pin = fields.Char(
        string="PIN del certificado", groups='l10n_cr_fe_crlibre.group_fe_admin')

    crlibre_api_username = fields.Char(groups='l10n_cr_fe_crlibre.group_fe_admin')
    crlibre_api_password = fields.Char(groups='l10n_cr_fe_crlibre.group_fe_admin')
    certificate_download_code = fields.Char(readonly=True)

    _sql_constraints = [
        ('company_id_uniq', 'unique(company_id)',
         "Ya existe una configuración de Factura Electrónica para esta empresa."),
    ]

    def _get_for_company(self, company):
        config = self.search([('company_id', '=', company.id)], limit=1)
        if not config:
            raise UserError(
                _("No hay configuración de Factura Electrónica para la empresa %s.") % company.name)
        return config
```

- [ ] **Step 5: Access rights**

`addons/l10n_cr_fe_crlibre/security/ir.model.access.csv`:
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_l10n_cr_fe_config_user,l10n_cr.fe.config.user,model_l10n_cr_fe_config,account.group_account_invoice,1,0,0,0
access_l10n_cr_fe_config_admin,l10n_cr.fe.config.admin,model_l10n_cr_fe_config,account.group_account_manager,1,1,1,1
```

- [ ] **Step 6: Vista y menú**

`addons/l10n_cr_fe_crlibre/views/fe_config_views.xml`:
```xml
<odoo>
    <record id="view_l10n_cr_fe_config_form" model="ir.ui.view">
        <field name="name">l10n_cr.fe.config.form</field>
        <field name="model">l10n_cr.fe.config</field>
        <field name="arch" type="xml">
            <form string="Configuración Factura Electrónica CR">
                <sheet>
                    <group>
                        <group string="General">
                            <field name="company_id"/>
                            <field name="environment"/>
                            <field name="identification_type"/>
                            <field name="identification_number"/>
                            <field name="legal_name"/>
                            <field name="trade_name"/>
                            <field name="economic_activity_code"/>
                        </group>
                        <group string="Ubicación">
                            <field name="province"/>
                            <field name="canton"/>
                            <field name="district"/>
                            <field name="neighborhood"/>
                            <field name="address_detail"/>
                            <field name="phone"/>
                            <field name="email"/>
                            <field name="branch_number"/>
                            <field name="terminal_number"/>
                        </group>
                    </group>
                    <group string="Credenciales y certificado" groups="l10n_cr_fe_crlibre.group_fe_admin">
                        <field name="hacienda_username"/>
                        <field name="hacienda_password" password="True"/>
                        <field name="certificate_file" filename="certificate_filename"/>
                        <field name="certificate_filename" invisible="1"/>
                        <field name="certificate_pin" password="True"/>
                        <field name="certificate_download_code" readonly="1"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>
    <record id="view_l10n_cr_fe_config_list" model="ir.ui.view">
        <field name="name">l10n_cr.fe.config.list</field>
        <field name="model">l10n_cr.fe.config</field>
        <field name="arch" type="xml">
            <list string="Configuración Factura Electrónica CR">
                <field name="company_id"/>
                <field name="environment"/>
                <field name="identification_number"/>
                <field name="legal_name"/>
            </list>
        </field>
    </record>
    <record id="action_l10n_cr_fe_config" model="ir.actions.act_window">
        <field name="name">Factura Electrónica CR</field>
        <field name="res_model">l10n_cr.fe.config</field>
        <field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_l10n_cr_fe_config"
              name="Factura Electrónica CR"
              parent="account.account_account_menu"
              action="action_l10n_cr_fe_config"
              groups="l10n_cr_fe_crlibre.group_fe_admin"/>
</odoo>
```

- [ ] **Step 7: Registrar los archivos nuevos**

`addons/l10n_cr_fe_crlibre/models/__init__.py`:
```python
from . import crlibre_client
from . import fe_config
from . import account_move
```

`addons/l10n_cr_fe_crlibre/tests/__init__.py` (agregar la línea, mantener las existentes):
```python
from . import test_crlibre_client
from . import test_fe_config
from . import test_account_move_mapping
from . import test_generate_action
```

`addons/l10n_cr_fe_crlibre/__manifest__.py` — reemplazar la lista `data`:
```python
    'data': [
        'security/l10n_cr_fe_security.xml',
        'security/ir.model.access.csv',
        'views/fe_config_views.xml',
        'views/account_move_views.xml',
    ],
```
(se quita `data/config_params.xml` de esta lista; se elimina en la Tarea 2).

- [ ] **Step 8: Actualizar el módulo y correr los tests**

Run:
```bash
docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --stop-after-init
MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init
```
Expected: sin `ParseError`, termina en `Modules loaded.`; los 4 tests nuevos PASAN.

- [ ] **Step 9: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/fe_config.py addons/l10n_cr_fe_crlibre/models/__init__.py \
        addons/l10n_cr_fe_crlibre/security addons/l10n_cr_fe_crlibre/views/fe_config_views.xml \
        addons/l10n_cr_fe_crlibre/tests/test_fe_config.py addons/l10n_cr_fe_crlibre/tests/__init__.py \
        addons/l10n_cr_fe_crlibre/__manifest__.py
git commit -m "feat(l10n_cr_fe): modelo de configuracion tributaria por empresa"
```

---

## Task 2: Migrar el mapeo de factura para leer de `l10n_cr.fe.config`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`
- Delete: `addons/l10n_cr_fe_crlibre/data/config_params.xml`

**Interfaces:**
- Consumes: `l10n_cr.fe.config._get_for_company(company)` (Tarea 1).
- Produces: `account.move._l10n_cr_fe_get_config(self) -> l10n_cr.fe.config`; `_l10n_cr_fe_build_clave_params`/`_l10n_cr_fe_build_genxml_params` ahora leen de ese registro en vez de `ir.config_parameter`.

- [ ] **Step 1: Actualizar el test existente para usar `l10n_cr.fe.config`**

Reemplazar el contenido de `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`:
```python
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountMoveMapping(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.env.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas Demo SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de demostración',
            'email': 'demo@frutasdemo.cr',
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Cliente Demo',
            'vat': '102340567',
        })
        self.product = self.env['product.product'].create({
            'name': 'Producto demo',
        })
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 1000.0,
                'name': 'Producto demo',
            })],
        })

    def test_build_clave_params(self):
        params = self.invoice._l10n_cr_fe_build_clave_params()
        self.assertEqual(params['tipoDocumento'], 'FE')
        self.assertEqual(params['situacion'], 'normal')
        self.assertEqual(params['cedula'], '702320717')
        self.assertEqual(len(params['codigoSeguridad']), 8)
        self.assertTrue(params['codigoSeguridad'].isdigit())

    def test_build_genxml_params_uses_company_config(self):
        import json
        detalles = [{'codigoCABYS': '0111101000000', 'cantidad': 1, 'unidadMedida': 'Unid',
                     'detalle': 'x', 'precioUnitario': 1000.0, 'montoTotal': 1000.0,
                     'subTotal': 1000.0, 'baseImponible': 1000.0,
                     'impuestoAsumidoEmisorFabrica': 0, 'impuestoNeto': 0.0,
                     'montoTotalLinea': 1000.0}]
        params = self.invoice._l10n_cr_fe_build_genxml_params('5' * 50, '0' * 20, detalles)
        self.assertEqual(params['emisor_nombre'], 'Frutas Demo SA')
        self.assertEqual(params['emisor_num_identif'], '702320717')
        self.assertEqual(params['receptor_num_identif'], '102340567')
        self.assertIsInstance(params['detalles'], str)
        self.assertEqual(json.loads(params['detalles'])[0]['codigoCABYS'], '0111101000000')
```

(Los tests de `_l10n_cr_fe_build_detalles` se mueven a la Tarea 3, porque ahí cambia su firma al requerir CABYS por producto.)

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`_l10n_cr_fe_param` sigue leyendo `ir.config_parameter`, que ya no se siembra).

- [ ] **Step 3: Reescribir el mapeo en `account_move.py`**

Reemplazar `_l10n_cr_fe_param` y los métodos que la usan en `addons/l10n_cr_fe_crlibre/models/account_move.py`:
```python
    def _l10n_cr_fe_get_config(self):
        self.ensure_one()
        return self.env['l10n_cr.fe.config']._get_for_company(self.company_id)

    def _l10n_cr_fe_build_clave_params(self):
        self.ensure_one()
        config = self._l10n_cr_fe_get_config()
        return {
            'tipoDocumento': 'FE',
            'tipoCedula': config.identification_type == '02' and 'juridico' or 'fisico',
            'cedula': config.identification_number,
            'situacion': 'normal',
            'consecutivo': str(self.id),
            'codigoSeguridad': str(random.randint(0, 99999999)).zfill(8),
            'sucursal': config.branch_number,
            'terminal': config.terminal_number,
        }

    def _l10n_cr_fe_build_genxml_params(self, clave, consecutivo, detalles):
        self.ensure_one()
        config = self._l10n_cr_fe_get_config()
        fecha = fields.Datetime.context_timestamp(self, datetime.now())
        total = self.amount_total
        base = self.amount_untaxed
        medios_pago = [{'tipoMedioPago': '01', 'totalMedioPago': total}]
        return {
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
(El consecutivo real vía `ir.sequence` reemplaza `str(self.id)` en la Tarea 4; aquí solo se migra la fuente de los datos del emisor.)

- [ ] **Step 4: Eliminar el archivo de configuración global**

```bash
git rm addons/l10n_cr_fe_crlibre/data/config_params.xml
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --stop-after-init`
Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py
git commit -m "feat(l10n_cr_fe): mapeo de factura lee configuracion por empresa en vez de parametros globales"
```

---

## Task 3: CABYS real por producto

**Files:**
- Create: `addons/l10n_cr_fe_crlibre/models/product_template.py`
- Create: `addons/l10n_cr_fe_crlibre/views/product_template_views.xml`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_product_template.py`
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Modify: `addons/l10n_cr_fe_crlibre/models/__init__.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`
- Modify: `addons/l10n_cr_fe_crlibre/__manifest__.py`

**Interfaces:**
- Produces: `product.template.l10n_cr_fe_cabys` (Char 13 dígitos, validado).
- Modifica: `account.move._l10n_cr_fe_build_detalles` ahora lee `line.product_id.l10n_cr_fe_cabys` y lanza `UserError` si falta.

- [ ] **Step 1: Escribir el test que falla (constraint de formato)**

`addons/l10n_cr_fe_crlibre/tests/test_product_template.py`:
```python
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestProductTemplateCabys(TransactionCase):

    def test_valid_cabys_is_accepted(self):
        product = self.env['product.template'].create({
            'name': 'Producto válido', 'l10n_cr_fe_cabys': '0111101000000',
        })
        self.assertEqual(product.l10n_cr_fe_cabys, '0111101000000')

    def test_invalid_cabys_length_raises(self):
        with self.assertRaises(ValidationError):
            self.env['product.template'].create({
                'name': 'Producto inválido', 'l10n_cr_fe_cabys': '123',
            })

    def test_invalid_cabys_non_digit_raises(self):
        with self.assertRaises(ValidationError):
            self.env['product.template'].create({
                'name': 'Producto inválido', 'l10n_cr_fe_cabys': 'abcdefghijklm',
            })
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (el campo no existe).

- [ ] **Step 3: Implementar el campo**

`addons/l10n_cr_fe_crlibre/models/product_template.py`:
```python
import re

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

CABYS_RE = re.compile(r'^\d{13}$')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_cr_fe_cabys = fields.Char(string="Código CABYS")

    @api.constrains('l10n_cr_fe_cabys')
    def _check_l10n_cr_fe_cabys(self):
        for product in self:
            if product.l10n_cr_fe_cabys and not CABYS_RE.match(product.l10n_cr_fe_cabys):
                raise ValidationError(
                    _("El código CABYS de '%s' debe tener exactamente 13 dígitos.") % product.name)
```

- [ ] **Step 4: Vista**

`addons/l10n_cr_fe_crlibre/views/product_template_views.xml`:
```xml
<odoo>
    <record id="view_product_template_form_l10n_cr_fe" model="ir.ui.view">
        <field name="name">product.template.form.l10n.cr.fe</field>
        <field name="model">product.template</field>
        <field name="inherit_id" ref="product.product_template_form_view"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='default_code']" position="after">
                <field name="l10n_cr_fe_cabys" string="Código CABYS"/>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 5: Registrar archivos**

`addons/l10n_cr_fe_crlibre/models/__init__.py`:
```python
from . import crlibre_client
from . import fe_config
from . import product_template
from . import account_move
```

`addons/l10n_cr_fe_crlibre/tests/__init__.py` (agregar):
```python
from . import test_product_template
```

`__manifest__.py`, agregar a `data` (después de `fe_config_views.xml`):
```python
        'views/product_template_views.xml',
```

- [ ] **Step 6: Correr el test y verificar que pasa**

Run: `docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --stop-after-init`
Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

- [ ] **Step 7: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/product_template.py addons/l10n_cr_fe_crlibre/views/product_template_views.xml \
        addons/l10n_cr_fe_crlibre/tests/test_product_template.py addons/l10n_cr_fe_crlibre/models/__init__.py \
        addons/l10n_cr_fe_crlibre/tests/__init__.py addons/l10n_cr_fe_crlibre/__manifest__.py
git commit -m "feat(l10n_cr_fe): campo CABYS por producto"
```

- [ ] **Step 8: Escribir el test que falla (detalles usan CABYS del producto)**

Agregar a `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py` (dentro de la clase existente, ajustar `setUp` para que `self.product` tenga CABYS):

Reemplazar en `setUp` la creación de `self.product`:
```python
        self.product = self.env['product.product'].create({
            'name': 'Producto demo',
            'l10n_cr_fe_cabys': '0111101000000',
        })
```

Agregar los métodos de test:
```python
    def test_build_detalles_uses_product_cabys(self):
        detalles = self.invoice._l10n_cr_fe_build_detalles()
        self.assertEqual(len(detalles), 1)
        self.assertEqual(detalles[0]['codigoCABYS'], '0111101000000')
        for field in ('subTotal', 'impuestoAsumidoEmisorFabrica', 'impuestoNeto',
                      'cantidad', 'unidadMedida', 'detalle', 'precioUnitario',
                      'montoTotal', 'montoTotalLinea'):
            self.assertIn(field, detalles[0])

    def test_build_detalles_without_cabys_raises(self):
        from odoo.exceptions import UserError
        self.product.l10n_cr_fe_cabys = False
        with self.assertRaises(UserError):
            self.invoice._l10n_cr_fe_build_detalles()
```

- [ ] **Step 9: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`_l10n_cr_fe_build_detalles` sigue usando el CABYS fijo de config).

- [ ] **Step 10: Reescribir `_l10n_cr_fe_build_detalles`**

Reemplazar en `addons/l10n_cr_fe_crlibre/models/account_move.py`:
```python
    def _l10n_cr_fe_build_detalles(self):
        self.ensure_one()
        detalles = []
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            if not line.product_id.l10n_cr_fe_cabys:
                raise UserError(
                    _("El producto '%s' no tiene código CABYS configurado.") % line.product_id.display_name)
            subtotal = line.price_subtotal
            impuesto_neto = line.price_total - line.price_subtotal
            detalle = {
                'codigoCABYS': line.product_id.l10n_cr_fe_cabys,
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
```
Agregar `_` a los imports de `odoo` en la parte superior del archivo si no está ya: `from odoo import api, fields, models, _`.

- [ ] **Step 11: Correr el test y verificar que pasa, luego commit**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py
git commit -m "feat(l10n_cr_fe): detalles de factura usan CABYS real del producto"
```

---

## Task 4: Consecutivo fiscal real vía `ir.sequence` por empresa

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/fe_config.py`
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_fe_config.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py`

**Interfaces:**
- Produces: `l10n_cr.fe.config._l10n_cr_fe_next_consecutivo(self) -> str` (10 dígitos, sin huecos, por empresa).
- Consumido por: `account_move._l10n_cr_fe_build_clave_params` (reemplaza `str(self.id)`).

- [ ] **Step 1: Escribir el test que falla**

Agregar a `addons/l10n_cr_fe_crlibre/tests/test_fe_config.py`:
```python
    def test_next_consecutivo_has_no_gaps(self):
        first = self.config._l10n_cr_fe_next_consecutivo()
        second = self.config._l10n_cr_fe_next_consecutivo()
        self.assertEqual(len(first), 10)
        self.assertEqual(int(second), int(first) + 1)

    def test_next_consecutivo_independent_per_company(self):
        other_company = self.env['res.company'].create({'name': 'Otra Empresa FE'})
        other_config = self.env['l10n_cr.fe.config'].create({
            'company_id': other_company.id,
            'environment': 'stag', 'identification_type': '01',
            'identification_number': '999999999', 'legal_name': 'Otra SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '01', 'neighborhood': '01',
            'address_detail': 'x', 'email': 'x@x.cr',
        })
        first_this = self.config._l10n_cr_fe_next_consecutivo()
        first_other = other_config._l10n_cr_fe_next_consecutivo()
        self.assertEqual(first_other, '0' * 9 + '1')
        self.assertNotEqual(first_this, first_other)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`_l10n_cr_fe_next_consecutivo` no existe).

- [ ] **Step 3: Implementar la secuencia**

Agregar a `addons/l10n_cr_fe_crlibre/models/fe_config.py` (dentro de la clase `L10nCrFeConfig`):
```python
    def _l10n_cr_fe_next_consecutivo(self):
        self.ensure_one()
        code = 'l10n_cr_fe.consecutivo.fe.%s' % self.company_id.id
        sequence = self.env['ir.sequence'].sudo().search([('code', '=', code)], limit=1)
        if not sequence:
            sequence = self.env['ir.sequence'].sudo().create({
                'name': 'Consecutivo FE - %s' % self.company_id.name,
                'code': code,
                'company_id': self.company_id.id,
                'padding': 10,
                'number_increment': 1,
                'implementation': 'no_gap',
            })
        return sequence.next_by_id()
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

- [ ] **Step 5: Usar el consecutivo real en `account_move.py`**

En `_l10n_cr_fe_build_clave_params`, reemplazar la línea `'consecutivo': str(self.id),` por:
```python
            'consecutivo': config.branch_number + config.terminal_number + '01' + config._l10n_cr_fe_next_consecutivo(),
```
(`'01'` es el tipo de documento fijo para FE, según el catálogo de Hacienda usado también en `signXML`.) Ajustar el test `test_build_clave_params` en `test_account_move_mapping.py`: reemplazar la aserción de `consecutivo` — agregar:
```python
        self.assertEqual(len(params['consecutivo']), 20)
        self.assertTrue(params['consecutivo'].isdigit())
```

- [ ] **Step 6: Correr todos los tests y verificar que pasan, luego commit**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

```bash
git add addons/l10n_cr_fe_crlibre/models/fe_config.py addons/l10n_cr_fe_crlibre/models/account_move.py \
        addons/l10n_cr_fe_crlibre/tests/test_fe_config.py addons/l10n_cr_fe_crlibre/tests/test_account_move_mapping.py
git commit -m "feat(l10n_cr_fe): consecutivo fiscal real via ir.sequence por empresa"
```

---

## Task 5: Cliente API — usuario de servicio (`register_api_user`, `login_api_user`)

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`

**Interfaces:**
- Produces: `l10n_cr.fe.client.register_api_user(full_name, username, password) -> {'session_key': str, 'id_user': int}`
- Produces: `l10n_cr.fe.client.login_api_user(username, password) -> {'session_key': str, 'id_user': int}`

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`:
```python
    def test_register_api_user_returns_session(self):
        payload = {'status': 'ok', 'resp': {'sessionKey': 'sk123', 'userName': 'empresa1', 'idUser': 5}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.register_api_user('Empresa Uno', 'empresa1', 'pass123')
        self.assertEqual(result['session_key'], 'sk123')
        self.assertEqual(result['id_user'], 5)
        called_params = m.call_args.kwargs['params']
        self.assertEqual(called_params['w'], 'users')
        self.assertEqual(called_params['r'], 'users_register')
        self.assertEqual(called_params['userName'], 'empresa1')

    def test_register_api_user_already_exists_raises(self):
        payload = {'status': 'ok', 'resp': {'code': '-304', 'status': 'usuario ya existe'}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)):
            with self.assertRaises(CrlibreApiError):
                self.client.register_api_user('Empresa Uno', 'empresa1', 'pass123')

    def test_login_api_user_returns_session(self):
        payload = {'status': 'ok', 'resp': {'sessionKey': 'sk456', 'userName': 'empresa1', 'idUser': 5}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.login_api_user('empresa1', 'pass123')
        self.assertEqual(result['session_key'], 'sk456')
        called_params = m.call_args.kwargs['params']
        self.assertEqual(called_params['r'], 'users_log_me_in')
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`register_api_user`/`login_api_user` no existen).

- [ ] **Step 3: Implementar los métodos**

Agregar a `addons/l10n_cr_fe_crlibre/models/crlibre_client.py` (dentro de la clase `CrlibreFeClient`):
```python
    def register_api_user(self, full_name, username, password):
        resp = self._call('users', 'users_register', {
            'fullName': full_name,
            'userName': username,
            'email': '%s@l10n-cr-fe.local' % username,
            'about': 'Cuenta de servicio Odoo l10n_cr_fe_crlibre',
            'country': 'crc',
            'pwd': password,
        })
        if not isinstance(resp, dict) or not resp.get('sessionKey'):
            raise CrlibreApiError("Respuesta inesperada de 'users_register': %s" % resp)
        return {'session_key': resp['sessionKey'], 'id_user': resp.get('idUser')}

    def login_api_user(self, username, password):
        resp = self._call('users', 'users_log_me_in', {
            'userName': username,
            'pwd': password,
        })
        if not isinstance(resp, dict) or not resp.get('sessionKey'):
            raise CrlibreApiError("Respuesta inesperada de 'users_log_me_in': %s" % resp)
        return {'session_key': resp['sessionKey'], 'id_user': resp.get('idUser')}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

- [ ] **Step 5: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/crlibre_client.py addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py
git commit -m "feat(l10n_cr_fe): cliente para registro y login de usuario de servicio en la API"
```

---

## Task 6: Cliente API — subida de certificado y orquestación en `l10n_cr.fe.config`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`
- Modify: `addons/l10n_cr_fe_crlibre/models/fe_config.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_fe_config.py`

**Interfaces:**
- Consumes: `register_api_user`, `login_api_user` (Tarea 5).
- Produces: `l10n_cr.fe.client.upload_certificate(session_key, username, p12_bytes) -> {'download_code': str}`
- Produces: `l10n_cr.fe.config._l10n_cr_fe_ensure_certificate_uploaded(self) -> str` (idempotente: registra usuario si falta, sube certificado si falta `certificate_download_code`, devuelve el `download_code`).

- [ ] **Step 1: Escribir el test del cliente que falla**

Agregar a `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py` (agregar `MagicMock` a los imports si falta, ya está importado en el archivo actual):
```python
    def test_upload_certificate_returns_download_code(self):
        payload = {'status': 'ok', 'resp': {'idFile': 1, 'name': 'cert.p12', 'downloadCode': 'DC123'}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.upload_certificate('sk123', 'empresa1', b'contenido-p12')
        self.assertEqual(result['download_code'], 'DC123')
        called_params = m.call_args.kwargs['params']
        self.assertEqual(called_params['w'], 'fileUploader')
        self.assertEqual(called_params['r'], 'subir_certif')
        self.assertEqual(called_params['iam'], 'empresa1')
        self.assertEqual(called_params['sessionKey'], 'sk123')
        called_files = m.call_args.kwargs['files']
        self.assertIn('fileToUpload', called_files)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`upload_certificate` no existe).

- [ ] **Step 3: Implementar `_call_multipart` y `upload_certificate`**

Agregar a `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`, un nuevo método junto a `_call` (dentro de `CrlibreFeClient`):
```python
    def _call_multipart(self, w, r, params, files):
        query = dict(params or {})
        query['w'] = w
        query['r'] = r
        url = self._get_base_url() + '/api.php'
        try:
            resp = requests.post(url, params=query, files=files, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise CrlibreApiError("No se pudo conectar con la API: %s" % exc)
        if resp.status_code != 200:
            raise CrlibreApiError("La API respondió HTTP %s" % resp.status_code)
        try:
            data = resp.json()
        except ValueError:
            raise CrlibreApiError("La API devolvió una respuesta no-JSON.")
        if not isinstance(data, dict) or data.get('status') != 'ok':
            raise CrlibreApiError("La API respondió estado no-ok: %s" % data)
        return data.get('resp')

    def upload_certificate(self, session_key, username, p12_bytes):
        resp = self._call_multipart('fileUploader', 'subir_certif', {
            'iam': username,
            'sessionKey': session_key,
        }, files={'fileToUpload': ('certificado.p12', p12_bytes, 'application/x-pkcs12')})
        if not isinstance(resp, dict) or not resp.get('downloadCode'):
            raise CrlibreApiError("Respuesta inesperada de 'subir_certif': %s" % resp)
        return {'download_code': resp['downloadCode']}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASA (el resto puede seguir en rojo si aún no existe `_l10n_cr_fe_ensure_certificate_uploaded`; se corrige en el siguiente paso).

- [ ] **Step 5: Escribir el test de orquestación que falla**

Agregar a `addons/l10n_cr_fe_crlibre/tests/test_fe_config.py`:
```python
    def test_ensure_certificate_uploaded_registers_and_uploads(self):
        self.config.certificate_file = base64.b64encode(b'contenido-p12')
        self.config.certificate_filename = 'cert.p12'
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.register_api_user',
                   return_value={'session_key': 'sk1', 'id_user': 9}) as m_register, \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.upload_certificate',
                   return_value={'download_code': 'DC999'}) as m_upload:
            code = self.config._l10n_cr_fe_ensure_certificate_uploaded()
        self.assertEqual(code, 'DC999')
        self.assertEqual(self.config.certificate_download_code, 'DC999')
        self.assertTrue(self.config.crlibre_api_username)
        m_register.assert_called_once()
        m_upload.assert_called_once()

    def test_ensure_certificate_uploaded_is_idempotent(self):
        self.config.certificate_file = base64.b64encode(b'contenido-p12')
        self.config.certificate_filename = 'cert.p12'
        self.config.certificate_download_code = 'DC_YA_EXISTE'
        self.config.crlibre_api_username = 'ya_registrado'
        self.config.crlibre_api_password = 'x'
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.register_api_user') as m_register, \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.upload_certificate') as m_upload:
            code = self.config._l10n_cr_fe_ensure_certificate_uploaded()
        self.assertEqual(code, 'DC_YA_EXISTE')
        m_register.assert_not_called()
        m_upload.assert_not_called()
```
Agregar `import base64` y `from unittest.mock import patch` al principio de `test_fe_config.py`.

- [ ] **Step 6: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`_l10n_cr_fe_ensure_certificate_uploaded` no existe).

- [ ] **Step 7: Implementar la orquestación en `fe_config.py`**

Agregar a `addons/l10n_cr_fe_crlibre/models/fe_config.py` (imports adicionales `base64`, `uuid`, `UserError` ya está; agregar al inicio del archivo `import base64` y `import uuid`):
```python
    def _l10n_cr_fe_ensure_certificate_uploaded(self):
        self.ensure_one()
        if self.certificate_download_code:
            return self.certificate_download_code
        if not self.certificate_file:
            raise UserError(_("Debe cargar el certificado .p12 antes de generar comprobantes."))

        client = self.env['l10n_cr.fe.client']
        if not self.crlibre_api_username:
            username = 'odoo-%s-%s' % (self.company_id.id, uuid.uuid4().hex[:8])
            password = uuid.uuid4().hex
            client.register_api_user(self.company_id.name or username, username, password)
            self.crlibre_api_username = username
            self.crlibre_api_password = password

        login = client.login_api_user(self.crlibre_api_username, self.crlibre_api_password)
        upload = client.upload_certificate(
            login['session_key'], self.crlibre_api_username,
            base64.b64decode(self.certificate_file))
        self.certificate_download_code = upload['download_code']
        return self.certificate_download_code
```

- [ ] **Step 8: Correr el test y verificar que pasa**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

- [ ] **Step 9: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/crlibre_client.py addons/l10n_cr_fe_crlibre/models/fe_config.py \
        addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py addons/l10n_cr_fe_crlibre/tests/test_fe_config.py
git commit -m "feat(l10n_cr_fe): subida automatica del certificado p12 y obtencion de download_code"
```

---

## Task 7: Cliente API — token OAuth de Hacienda (`get_hacienda_token`)

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`
- Patch (fuera de este repo): `D:\API_Hacienda\api\contrib\token\mhToken.php`

**Interfaces:**
- Produces: `l10n_cr.fe.client.get_hacienda_token(username, password, environment) -> str` (el `access_token`).

**Nota importante (bug encontrado en la API, no en nuestro código):** `mhToken.php` llama dos veces `curl_setopt($curl, CURLOPT_HEADER, ...)`: primero con `true`, luego con un string en vez de `CURLOPT_HTTPHEADER`. El resultado es que la respuesta de Hacienda llega con las cabeceras HTTP crudas pegadas al body, y `json_decode()` falla silenciosamente (devuelve `null`). Esto es un bug pre-existente del proyecto AGPL, no una decisión de diseño — se corrige localmente como arreglo de infraestructura (mismo criterio que el fix del CRLF del entrypoint en el PoC), sin commitear el cambio en `d:\ERP`.

- [ ] **Step 1: Parchear `mhToken.php` (arreglo de infraestructura, en `D:\API_Hacienda`)**

Editar `D:\API_Hacienda\api\contrib\token\mhToken.php`, dentro de la función `token()`:

Antes:
```php
    curl_setopt($curl, CURLOPT_HEADER, true);
    curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($curl, CURLOPT_POST, true);
    curl_setopt($curl, CURLOPT_SSL_VERIFYHOST, false);
    curl_setopt($curl, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($curl, CURLOPT_HEADER, 'Content-Type: application/x-www-form-urlencoded');
```

Después:
```php
    curl_setopt($curl, CURLOPT_HEADER, false);
    curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($curl, CURLOPT_POST, true);
    curl_setopt($curl, CURLOPT_SSL_VERIFYHOST, false);
    curl_setopt($curl, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($curl, CURLOPT_HTTPHEADER, array('Content-Type: application/x-www-form-urlencoded'));
```

Luego reiniciar el contenedor de la API (nombre del contenedor según `docker compose ps` en `D:\API_Hacienda`, típicamente `crlibre-app`):
```bash
cd /d/API_Hacienda
docker compose restart
```

- [ ] **Step 2: Escribir los tests que fallan**

Agregar a `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`:
```python
    def test_get_hacienda_token_returns_access_token(self):
        payload = {'status': 'ok', 'resp': {
            'access_token': 'tok123', 'expires_in': 300, 'refresh_token': 'ref123'}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)) as m:
            token = self.client.get_hacienda_token('user@stag.comprobanteselectronicos.go.cr', 'pass', 'stag')
        self.assertEqual(token, 'tok123')
        called_params = m.call_args.kwargs['params']
        self.assertEqual(called_params['w'], 'token')
        self.assertEqual(called_params['r'], 'gettoken')
        self.assertEqual(called_params['client_id'], 'api-stag')
        self.assertIn('idp.comprobanteselectronicos.go.cr', called_params['url'])

    def test_get_hacienda_token_prod_uses_prod_client_id(self):
        payload = {'status': 'ok', 'resp': {'access_token': 'tokprod'}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)) as m:
            self.client.get_hacienda_token('user@prod...', 'pass', 'prod')
        self.assertEqual(m.call_args.kwargs['params']['client_id'], 'api-prod')

    def test_get_hacienda_token_missing_access_token_raises(self):
        payload = {'status': 'ok', 'resp': None}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)):
            with self.assertRaises(CrlibreApiError):
                self.client.get_hacienda_token('user', 'pass', 'stag')
```

- [ ] **Step 3: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`get_hacienda_token` no existe).

- [ ] **Step 4: Implementar el método**

Agregar a `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`:
```python
    _ENVIRONMENT_URLS = {
        'stag': ('https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token', 'api-stag'),
        'prod': ('https://idp.comprobanteselectronicos.go.cr/auth/realms/rut/protocol/openid-connect/token', 'api-prod'),
    }

    def get_hacienda_token(self, username, password, environment):
        idp_url, client_id = self._ENVIRONMENT_URLS[environment]
        resp = self._call('token', 'gettoken', {
            'url': idp_url,
            'grant_type': 'password',
            'client_id': client_id,
            'client_secret': '',
            'username': username,
            'password': password,
        })
        if not isinstance(resp, dict) or not resp.get('access_token'):
            raise CrlibreApiError("Respuesta inesperada de 'token/gettoken': %s" % resp)
        return resp['access_token']
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

- [ ] **Step 6: Commit (solo el lado Odoo; el parche de la API vive en su propio repo)**

```bash
git add addons/l10n_cr_fe_crlibre/models/crlibre_client.py addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py
git commit -m "feat(l10n_cr_fe): cliente para obtener token OAuth real de Hacienda"
```

---

## Task 8: Cliente API — firma XML (`sign_xml`)

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`

**Interfaces:**
- Produces: `l10n_cr.fe.client.sign_xml(download_code, pin, xml) -> str` (XML firmado, ya decodificado de base64).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`:
```python
    def test_sign_xml_decodes_base64(self):
        import base64
        xml_firmado = '<FacturaElectronica>firmado</FacturaElectronica>'
        payload = {'status': 'ok', 'resp': {'xmlFirmado': base64.b64encode(xml_firmado.encode()).decode()}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.sign_xml('DC123', '1234', '<FacturaElectronica>sin firmar</FacturaElectronica>')
        self.assertEqual(result, xml_firmado)
        called_params = m.call_args.kwargs['params']
        self.assertEqual(called_params['w'], 'firmarXML')
        self.assertEqual(called_params['r'], 'firmar')
        self.assertEqual(called_params['p12Url'], 'DC123')
        self.assertEqual(called_params['pinP12'], '1234')

    def test_sign_xml_missing_result_raises(self):
        payload = {'status': 'ok', 'resp': {}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)):
            with self.assertRaises(CrlibreApiError):
                self.client.sign_xml('DC123', '1234', '<xml/>')
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`sign_xml` no existe).

- [ ] **Step 3: Implementar el método**

Agregar a `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`:
```python
    def sign_xml(self, download_code, pin, xml):
        xml_b64 = base64.b64encode(xml.encode('utf-8')).decode('ascii')
        resp = self._call('firmarXML', 'firmar', {
            'p12Url': download_code,
            'pinP12': pin,
            'inXml': xml_b64,
        })
        if not isinstance(resp, dict) or not resp.get('xmlFirmado'):
            raise CrlibreApiError("Respuesta inesperada de 'firmarXML/firmar': %s" % resp)
        return base64.b64decode(resp['xmlFirmado']).decode('utf-8')
```

- [ ] **Step 4: Correr el test y verificar que pasa, luego commit**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

```bash
git add addons/l10n_cr_fe_crlibre/models/crlibre_client.py addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py
git commit -m "feat(l10n_cr_fe): cliente para firmar el XML con el certificado p12"
```

---

## Task 9: Cliente API — envío (`send_fe`) y consulta de estado (`consultar_estado`)

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/crlibre_client.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`

**Interfaces:**
- Produces: `l10n_cr.fe.client.send_fe(token, clave, fecha_iso, emisor_tipo, emisor_num, receptor_tipo, receptor_num, xml_firmado, environment) -> dict` con al menos `{'http_status': int, 'raw': list}`.
- Produces: `l10n_cr.fe.client.consultar_estado(token, clave, environment) -> dict` con al menos `{'ind_estado': str, 'respuesta_xml': str|None}` (o `ind_estado='desconocido'` si Hacienda aún no tiene resultado).

**Nota (riesgo ya identificado en el spec, §10):** el módulo `send` de la API antepone las cabeceras HTTP crudas al cuerpo de la respuesta (mismo patrón de `CURLOPT_HEADER=true` visto en `token`, pero aquí SÍ forma parte del diseño — el módulo devuelve `text` como lista de líneas, no JSON). El parseo de abajo separa las cabeceras del cuerpo buscando la primera línea en blanco; se valida y ajusta contra el sandbox real en la Tarea 15 si el formato real difiere.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py`:
```python
    def test_send_fe_parses_202_recibido(self):
        raw_lines = ['HTTP/1.1 202 Accepted', 'Content-Type: application/json', '', '']
        payload = {'status': 'ok', 'resp': {'Status': 202, 'text': raw_lines}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.send_fe(
                token='tok', clave='5' * 50, fecha_iso='2026-07-06T09:00:00-06:00',
                emisor_tipo='01', emisor_num='702320717',
                receptor_tipo='01', receptor_num='102340567',
                xml_firmado='<FacturaElectronica/>', environment='stag')
        self.assertEqual(result['http_status'], 202)
        called_params = m.call_args.kwargs['params']
        self.assertEqual(called_params['w'], 'send')
        self.assertEqual(called_params['r'], 'json')
        self.assertEqual(called_params['client_id'], 'api-stag')
        self.assertEqual(called_params['token'], 'tok')

    def test_send_fe_error_status_raises(self):
        payload = {'status': 'ok', 'resp': {'Status': 400, 'text': ['HTTP/1.1 400 Bad Request', '']}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)):
            with self.assertRaises(CrlibreApiError):
                self.client.send_fe(
                    token='tok', clave='5' * 50, fecha_iso='2026-07-06T09:00:00-06:00',
                    emisor_tipo='01', emisor_num='702320717',
                    receptor_tipo='01', receptor_num='102340567',
                    xml_firmado='<FacturaElectronica/>', environment='stag')

    def test_consultar_estado_aceptado(self):
        payload = {'status': 'ok', 'resp': {'ind-estado': 'aceptado', 'respuesta-xml': 'PGZvbz8+'}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.consultar_estado('tok', '5' * 50, 'stag')
        self.assertEqual(result['ind_estado'], 'aceptado')
        self.assertEqual(result['respuesta_xml'], 'PGZvbz8+')
        self.assertEqual(m.call_args.kwargs['params']['client_id'], 'api-stag')

    def test_consultar_estado_pendiente(self):
        payload = {'status': 'ok', 'resp': None}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)):
            result = self.client.consultar_estado('tok', '5' * 50, 'stag')
        self.assertEqual(result['ind_estado'], 'desconocido')
        self.assertIsNone(result['respuesta_xml'])
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`send_fe`/`consultar_estado` no existen).

- [ ] **Step 3: Implementar los métodos**

Agregar a `addons/l10n_cr_fe_crlibre/models/crlibre_client.py` (usa `_ENVIRONMENT_URLS` ya definido en la Tarea 7 solo para el `client_id`; se define aquí un mapa reducido dedicado):
```python
    _CLIENT_ID_BY_ENVIRONMENT = {'stag': 'api-stag', 'prod': 'api-prod'}

    def send_fe(self, token, clave, fecha_iso, emisor_tipo, emisor_num,
                receptor_tipo, receptor_num, xml_firmado, environment):
        resp = self._call('send', 'json', {
            'token': token,
            'clave': clave,
            'fecha': fecha_iso,
            'emi_tipoIdentificacion': emisor_tipo,
            'emi_numeroIdentificacion': emisor_num,
            'recp_tipoIdentificacion': receptor_tipo,
            'recp_numeroIdentificacion': receptor_num,
            'comprobanteXml': base64.b64encode(xml_firmado.encode('utf-8')).decode('ascii'),
            'client_id': self._CLIENT_ID_BY_ENVIRONMENT[environment],
        })
        if not isinstance(resp, dict) or 'Status' not in resp:
            raise CrlibreApiError("Respuesta inesperada de 'send/json': %s" % resp)
        http_status = resp['Status']
        if http_status not in (200, 202):
            raise CrlibreApiError("Hacienda rechazó el envío (HTTP %s): %s" % (http_status, resp.get('text')))
        return {'http_status': http_status, 'raw': resp.get('text') or []}

    def consultar_estado(self, token, clave, environment):
        resp = self._call('consultar', 'consultarCom', {
            'token': token,
            'clave': clave,
            'client_id': self._CLIENT_ID_BY_ENVIRONMENT[environment],
        })
        if not isinstance(resp, dict):
            return {'ind_estado': 'desconocido', 'respuesta_xml': None}
        return {
            'ind_estado': resp.get('ind-estado', 'desconocido'),
            'respuesta_xml': resp.get('respuesta-xml'),
        }
```

- [ ] **Step 4: Correr el test y verificar que pasa, luego commit**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

```bash
git add addons/l10n_cr_fe_crlibre/models/crlibre_client.py addons/l10n_cr_fe_crlibre/tests/test_crlibre_client.py
git commit -m "feat(l10n_cr_fe): cliente para envio a recepcion y consulta de estado"
```

---

## Task 10: Ampliar campos y estados de `account.move`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Modify: `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_generate_action.py`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`

**Interfaces:**
- Produces: `account.move.l10n_cr_fe_xml_firmado` (Text), `l10n_cr_fe_respuesta_xml` (Text), `l10n_cr_fe_motivo_rechazo` (Char).
- Modifica: `l10n_cr_fe_state` ahora tiene las opciones `draft, generado, enviado, aceptado, rechazado, error` (antes: `draft, generated, error`).

- [ ] **Step 1: Escribir el test que falla**

`addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py`:
```python
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountMoveFeFields(TransactionCase):

    def test_new_fe_fields_exist_with_defaults(self):
        partner = self.env['res.partner'].create({'name': 'Cliente FE Fields'})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
        })
        self.assertEqual(invoice.l10n_cr_fe_state, 'draft')
        self.assertFalse(invoice.l10n_cr_fe_xml_firmado)
        self.assertFalse(invoice.l10n_cr_fe_respuesta_xml)
        self.assertFalse(invoice.l10n_cr_fe_motivo_rechazo)

    def test_state_selection_includes_all_expected_values(self):
        field = self.env['account.move']._fields['l10n_cr_fe_state']
        keys = [key for key, _label in field.selection]
        self.assertEqual(
            keys, ['draft', 'generado', 'enviado', 'aceptado', 'rechazado', 'error'])
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (los campos nuevos no existen; `l10n_cr_fe_state` no tiene `'generado'`).

- [ ] **Step 3: Ampliar los campos**

En `addons/l10n_cr_fe_crlibre/models/account_move.py`, reemplazar el bloque de campos existente:
```python
    l10n_cr_fe_clave = fields.Char(string="Clave FE", readonly=True, copy=False)
    l10n_cr_fe_consecutivo = fields.Char(string="Consecutivo FE", readonly=True, copy=False)
    l10n_cr_fe_xml = fields.Text(string="XML FE", readonly=True, copy=False)
    l10n_cr_fe_xml_firmado = fields.Text(string="XML Firmado FE", readonly=True, copy=False)
    l10n_cr_fe_respuesta_xml = fields.Text(string="Respuesta Hacienda", readonly=True, copy=False)
    l10n_cr_fe_motivo_rechazo = fields.Char(string="Motivo de rechazo", readonly=True, copy=False)
    l10n_cr_fe_state = fields.Selection(
        selection=[
            ('draft', "Borrador"),
            ('generado', "Generado"),
            ('enviado', "Enviado"),
            ('aceptado', "Aceptado"),
            ('rechazado', "Rechazado"),
            ('error', "Error"),
        ],
        string="Estado FE", default='draft', readonly=True, copy=False)
```

En el método `action_l10n_cr_fe_generate` (todavía presente en esta tarea, se elimina en la Tarea 11), cambiar la línea `'l10n_cr_fe_state': 'generated',` por `'l10n_cr_fe_state': 'generado',`.

En `addons/l10n_cr_fe_crlibre/tests/test_generate_action.py`, cambiar `self.assertEqual(self.invoice.l10n_cr_fe_state, 'generated')` por `self.assertEqual(self.invoice.l10n_cr_fe_state, 'generado')`.

- [ ] **Step 4: Ampliar la vista**

En `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`, dentro de la página "Factura Electrónica CR", después de `<field name="l10n_cr_fe_consecutivo"/>`, agregar:
```xml
                        <field name="l10n_cr_fe_motivo_rechazo" invisible="l10n_cr_fe_state != 'rechazado'"/>
```
Y después de `<field name="l10n_cr_fe_xml"/>`, agregar:
```xml
                    <field name="l10n_cr_fe_xml_firmado"/>
                    <field name="l10n_cr_fe_respuesta_xml"/>
```

- [ ] **Step 5: Registrar el archivo de test nuevo**

`addons/l10n_cr_fe_crlibre/tests/__init__.py` (agregar):
```python
from . import test_account_move_fields
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --stop-after-init`
Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

- [ ] **Step 7: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/views/account_move_views.xml \
        addons/l10n_cr_fe_crlibre/tests/test_generate_action.py addons/l10n_cr_fe_crlibre/tests/test_account_move_fields.py \
        addons/l10n_cr_fe_crlibre/tests/__init__.py
git commit -m "feat(l10n_cr_fe): amplia campos y estados FE en account.move"
```

---

## Task 11: Orquestación completa — override de `action_post()`

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Modify: `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`
- Delete: `addons/l10n_cr_fe_crlibre/tests/test_generate_action.py`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_action_post_fe.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`

**Interfaces:**
- Consumes: `l10n_cr.fe.config._l10n_cr_fe_ensure_certificate_uploaded`, `get_clave`, `gen_xml_fe`, `get_hacienda_token`, `sign_xml`, `send_fe` (Tareas 1-9).
- Produces: `account.move._l10n_cr_fe_generate_and_send(self)` (orquestación completa, reutilizada por la Tarea 14); override de `action_post`.
- Elimina: `action_l10n_cr_fe_generate` y `_l10n_cr_fe_notify` (el botón manual del PoC deja de existir; el flujo ahora es automático).

- [ ] **Step 1: Escribir los tests que fallan**

Borrar `addons/l10n_cr_fe_crlibre/tests/test_generate_action.py`:
```bash
git rm addons/l10n_cr_fe_crlibre/tests/test_generate_action.py
```

Crear `addons/l10n_cr_fe_crlibre/tests/test_action_post_fe.py`:
```python
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client import CrlibreApiError


@tagged('post_install', '-at_install')
class TestActionPostFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.env.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas Demo SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de demostración',
            'email': 'demo@frutasdemo.cr',
            'hacienda_username': 'user@stag.comprobanteselectronicos.go.cr',
            'hacienda_password': 'secret',
            'certificate_pin': '1234',
            'certificate_download_code': 'DC_YA_SUBIDO',
        })
        partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        product = self.env['product.product'].create({
            'name': 'Producto demo', 'l10n_cr_fe_cabys': '0111101000000'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo',
            })],
        })

    def _patch_full_success(self):
        clave = '5' * 50
        return [
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                  return_value={'clave': clave, 'consecutivo': '0' * 20}),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_fe',
                  return_value='<FacturaElectronica>sin firmar</FacturaElectronica>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                  return_value='tok123'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.sign_xml',
                  return_value='<FacturaElectronica>firmada</FacturaElectronica>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.send_fe',
                  return_value={'http_status': 202, 'raw': []}),
        ]

    def test_action_post_success_sets_state_enviado(self):
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            self.invoice.action_post()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'enviado')
        self.assertEqual(self.invoice.l10n_cr_fe_clave, '5' * 50)
        self.assertIn('firmada', self.invoice.l10n_cr_fe_xml_firmado)

    def test_action_post_does_not_block_when_fe_fails(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                   side_effect=CrlibreApiError('boom')):
            self.invoice.action_post()
        self.assertEqual(self.invoice.state, 'posted')
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'error')

    def test_action_post_ignores_vendor_bills(self):
        partner = self.env['res.partner'].create({'name': 'Proveedor Demo'})
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, {'quantity': 1, 'price_unit': 100.0, 'name': 'Gasto'})],
        })
        bill.action_post()
        self.assertEqual(bill.l10n_cr_fe_state, 'draft')
```

`addons/l10n_cr_fe_crlibre/tests/__init__.py`: quitar `from . import test_generate_action` y agregar `from . import test_action_post_fe`.

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`action_post` no está sobreescrito; `_l10n_cr_fe_generate_and_send` no existe).

- [ ] **Step 3: Implementar la orquestación**

En `addons/l10n_cr_fe_crlibre/models/account_move.py`, quitar `action_l10n_cr_fe_generate` y `_l10n_cr_fe_notify` por completo, y agregar:
```python
    def _l10n_cr_fe_generate_and_send(self):
        self.ensure_one()
        if self.move_type != 'out_invoice':
            return
        if not self.partner_id:
            raise UserError(_("La factura no tiene cliente (receptor)."))

        config = self._l10n_cr_fe_get_config()
        client = self.env['l10n_cr.fe.client']
        try:
            download_code = config._l10n_cr_fe_ensure_certificate_uploaded()
            clave_params = self._l10n_cr_fe_build_clave_params()
            clave_res = client.get_clave(clave_params)
            detalles = self._l10n_cr_fe_build_detalles()
            genxml_params = self._l10n_cr_fe_build_genxml_params(
                clave_res['clave'], clave_res['consecutivo'], detalles)
            xml = client.gen_xml_fe(genxml_params)
            token = client.get_hacienda_token(
                config.hacienda_username, config.hacienda_password, config.environment)
            xml_firmado = client.sign_xml(download_code, config.certificate_pin, xml)
            fecha_iso = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y-%m-%dT%H:%M:%S-06:00')
            client.send_fe(
                token=token, clave=clave_res['clave'], fecha_iso=fecha_iso,
                emisor_tipo=config.identification_type, emisor_num=config.identification_number,
                receptor_tipo='01',
                receptor_num=(self.partner_id.vat or '').replace('-', '') or '000000000',
                xml_firmado=xml_firmado, environment=config.environment)
        except CrlibreApiError as exc:
            self.l10n_cr_fe_state = 'error'
            self.message_post(body=_("Error en el flujo de Factura Electrónica: %s") % exc)
            return

        self.write({
            'l10n_cr_fe_clave': clave_res['clave'],
            'l10n_cr_fe_consecutivo': clave_res['consecutivo'],
            'l10n_cr_fe_xml': xml,
            'l10n_cr_fe_xml_firmado': xml_firmado,
            'l10n_cr_fe_state': 'enviado',
        })
        self.message_post(body=_("Comprobante FE enviado a Hacienda. Clave: %s") % clave_res['clave'])

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.move_type == 'out_invoice':
                move._l10n_cr_fe_generate_and_send()
        return res
```

- [ ] **Step 4: Quitar el botón manual de la vista**

En `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`, dentro de `<xpath expr="//header" position="inside">`, eliminar el `<button name="action_l10n_cr_fe_generate" .../>` (se mantiene el `<field name="l10n_cr_fe_state" widget="statusbar" .../>`).

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --stop-after-init`
Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/views/account_move_views.xml \
        addons/l10n_cr_fe_crlibre/tests/test_action_post_fe.py addons/l10n_cr_fe_crlibre/tests/__init__.py
git commit -m "feat(l10n_cr_fe): orquestacion automatica del ciclo FE al confirmar la factura"
```

---

## Task 12: Botón "Consultar estado FE"

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Modify: `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_consultar_estado_fe.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`

**Interfaces:**
- Consumes: `get_hacienda_token`, `consultar_estado` (Tareas 7 y 9).
- Produces: `account.move.action_l10n_cr_fe_consultar_estado(self)`, `account.move._l10n_cr_fe_parse_motivo(self, respuesta_xml) -> str|False`.

- [ ] **Step 1: Escribir los tests que fallan**

`addons/l10n_cr_fe_crlibre/tests/test_consultar_estado_fe.py`:
```python
import base64
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestConsultarEstadoFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.env.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas Demo SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de demostración',
            'email': 'demo@frutasdemo.cr',
            'hacienda_username': 'user@stag.comprobanteselectronicos.go.cr',
            'hacienda_password': 'secret',
            'certificate_download_code': 'DC',
        })
        partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': partner.id,
            'l10n_cr_fe_clave': '5' * 50, 'l10n_cr_fe_state': 'enviado',
        })

    def test_consultar_estado_aceptado_updates_state(self):
        xml = '<MensajeHacienda><DetalleMensaje>Comprobante aceptado</DetalleMensaje></MensajeHacienda>'
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                   return_value='tok'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.consultar_estado',
                   return_value={'ind_estado': 'aceptado', 'respuesta_xml': base64.b64encode(xml.encode()).decode()}):
            self.invoice.action_l10n_cr_fe_consultar_estado()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'aceptado')
        self.assertIn('aceptado', self.invoice.l10n_cr_fe_respuesta_xml)

    def test_consultar_estado_rechazado_sets_motivo(self):
        xml = '<MensajeHacienda><DetalleMensaje>Cedula receptor invalida</DetalleMensaje></MensajeHacienda>'
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                   return_value='tok'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.consultar_estado',
                   return_value={'ind_estado': 'rechazado', 'respuesta_xml': base64.b64encode(xml.encode()).decode()}):
            self.invoice.action_l10n_cr_fe_consultar_estado()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'rechazado')
        self.assertEqual(self.invoice.l10n_cr_fe_motivo_rechazo, 'Cedula receptor invalida')

    def test_consultar_estado_pendiente_leaves_state_unchanged(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                   return_value='tok'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.consultar_estado',
                   return_value={'ind_estado': 'procesando', 'respuesta_xml': None}):
            self.invoice.action_l10n_cr_fe_consultar_estado()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'enviado')
```

`addons/l10n_cr_fe_crlibre/tests/__init__.py` (agregar): `from . import test_consultar_estado_fe`

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`action_l10n_cr_fe_consultar_estado` no existe).

- [ ] **Step 3: Implementar la acción**

Agregar a `addons/l10n_cr_fe_crlibre/models/account_move.py` (agregar `import base64` y `import xml.etree.ElementTree as ET` a los imports del archivo):
```python
    def _l10n_cr_fe_parse_motivo(self, respuesta_xml):
        if not respuesta_xml:
            return False
        try:
            root = ET.fromstring(respuesta_xml)
        except ET.ParseError:
            return respuesta_xml[:200]
        detalle = root.find('.//DetalleMensaje')
        return detalle.text if detalle is not None else respuesta_xml[:200]

    def action_l10n_cr_fe_consultar_estado(self):
        self.ensure_one()
        config = self._l10n_cr_fe_get_config()
        client = self.env['l10n_cr.fe.client']
        try:
            token = client.get_hacienda_token(
                config.hacienda_username, config.hacienda_password, config.environment)
            result = client.consultar_estado(token, self.l10n_cr_fe_clave, config.environment)
        except CrlibreApiError as exc:
            self.message_post(body=_("Error al consultar el estado FE: %s") % exc)
            return

        respuesta_xml = False
        if result.get('respuesta_xml'):
            respuesta_xml = base64.b64decode(result['respuesta_xml']).decode('utf-8')

        estado = result['ind_estado']
        if estado == 'aceptado':
            self.write({'l10n_cr_fe_state': 'aceptado', 'l10n_cr_fe_respuesta_xml': respuesta_xml})
            self.message_post(body=_("Hacienda aceptó el comprobante FE."))
        elif estado == 'rechazado':
            self.write({
                'l10n_cr_fe_state': 'rechazado',
                'l10n_cr_fe_respuesta_xml': respuesta_xml,
                'l10n_cr_fe_motivo_rechazo': self._l10n_cr_fe_parse_motivo(respuesta_xml) or _("Rechazado por Hacienda"),
            })
            self.message_post(body=_("Hacienda rechazó el comprobante FE."))
        else:
            self.message_post(body=_("Hacienda aún no tiene una respuesta definitiva (estado: %s).") % estado)
```

- [ ] **Step 4: Agregar el botón a la vista**

En `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`, dentro de `<xpath expr="//header" position="inside">`, agregar (antes del `<field name="l10n_cr_fe_state" .../>`):
```xml
                <button name="action_l10n_cr_fe_consultar_estado"
                        string="Consultar estado FE"
                        type="object" class="btn-secondary"
                        invisible="l10n_cr_fe_state != 'enviado'"/>
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --stop-after-init`
Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/views/account_move_views.xml \
        addons/l10n_cr_fe_crlibre/tests/test_consultar_estado_fe.py addons/l10n_cr_fe_crlibre/tests/__init__.py
git commit -m "feat(l10n_cr_fe): boton para consultar el estado FE ante Hacienda"
```

---

## Task 13: Correo de notificación al aceptar

**Files:**
- Create: `addons/l10n_cr_fe_crlibre/data/mail_template.xml`
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/test_consultar_estado_fe.py`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_acceptance_email.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`
- Modify: `addons/l10n_cr_fe_crlibre/__manifest__.py`

**Interfaces:**
- Produces: `account.move._l10n_cr_fe_send_acceptance_email(self)`.
- Modifica: `action_l10n_cr_fe_consultar_estado` llama a este método cuando `estado == 'aceptado'`.

- [ ] **Step 1: Escribir el test que falla**

`addons/l10n_cr_fe_crlibre/tests/test_acceptance_email.py`:
```python
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAcceptanceEmail(TransactionCase):

    def setUp(self):
        super().setUp()
        partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'email': 'cliente@demo.cr'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': partner.id,
            'l10n_cr_fe_clave': '5' * 50,
            'l10n_cr_fe_xml_firmado': '<FacturaElectronica>firmada</FacturaElectronica>',
            'l10n_cr_fe_respuesta_xml': '<MensajeHacienda>aceptado</MensajeHacienda>',
        })

    def test_send_acceptance_email_attaches_both_xmls(self):
        with patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail') as m_send:
            self.invoice._l10n_cr_fe_send_acceptance_email()
        m_send.assert_called_once()
        attachment_ids = m_send.call_args.kwargs['email_values']['attachment_ids'][0][2]
        self.assertEqual(len(attachment_ids), 2)

    def test_send_acceptance_email_skips_without_partner_email(self):
        self.invoice.partner_id.email = False
        with patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail') as m_send:
            self.invoice._l10n_cr_fe_send_acceptance_email()
        m_send.assert_not_called()
```

`addons/l10n_cr_fe_crlibre/tests/__init__.py` (agregar): `from . import test_acceptance_email`

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`_l10n_cr_fe_send_acceptance_email` no existe).

- [ ] **Step 3: Crear la plantilla de correo**

`addons/l10n_cr_fe_crlibre/data/mail_template.xml`:
```xml
<odoo>
    <record id="mail_template_l10n_cr_fe_aceptado" model="mail.template">
        <field name="name">FE CR: Comprobante aceptado</field>
        <field name="model_id" ref="account.model_account_move"/>
        <field name="subject">Su comprobante electrónico {{ object.l10n_cr_fe_clave }}</field>
        <field name="email_to">{{ object.partner_id.email }}</field>
        <field name="body_html" type="html">
            <p>Estimado(a) {{ object.partner_id.name }},</p>
            <p>Adjuntamos el comprobante electrónico y la respuesta de aceptación del Ministerio de Hacienda.</p>
        </field>
    </record>
</odoo>
```

- [ ] **Step 4: Implementar el método de envío**

Agregar a `addons/l10n_cr_fe_crlibre/models/account_move.py`:
```python
    def _l10n_cr_fe_send_acceptance_email(self):
        self.ensure_one()
        if not self.partner_id.email:
            return
        attachment_ids = []
        attachment_model = self.env['ir.attachment']
        if self.l10n_cr_fe_xml_firmado:
            attachment_ids.append(attachment_model.create({
                'name': 'comprobante_%s.xml' % (self.l10n_cr_fe_clave or self.id),
                'datas': base64.b64encode(self.l10n_cr_fe_xml_firmado.encode('utf-8')),
                'res_model': 'account.move', 'res_id': self.id,
            }).id)
        if self.l10n_cr_fe_respuesta_xml:
            attachment_ids.append(attachment_model.create({
                'name': 'respuesta_hacienda_%s.xml' % (self.l10n_cr_fe_clave or self.id),
                'datas': base64.b64encode(self.l10n_cr_fe_respuesta_xml.encode('utf-8')),
                'res_model': 'account.move', 'res_id': self.id,
            }).id)
        template = self.env.ref('l10n_cr_fe_crlibre.mail_template_l10n_cr_fe_aceptado')
        template.send_mail(self.id, force_send=True,
                            email_values={'attachment_ids': [(6, 0, attachment_ids)]})
```

En `action_l10n_cr_fe_consultar_estado`, en la rama `if estado == 'aceptado':`, agregar la llamada después del `self.write(...)`:
```python
            self.message_post(body=_("Hacienda aceptó el comprobante FE."))
            self._l10n_cr_fe_send_acceptance_email()
```
(reemplaza la línea `self.message_post(body=_("Hacienda aceptó el comprobante FE."))` existente por estas dos líneas).

- [ ] **Step 5: Registrar el data file**

`__manifest__.py`, agregar a `data` (después de `views/product_template_views.xml`):
```python
        'data/mail_template.xml',
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --stop-after-init`
Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN.

- [ ] **Step 7: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/data/mail_template.xml addons/l10n_cr_fe_crlibre/models/account_move.py \
        addons/l10n_cr_fe_crlibre/tests/test_acceptance_email.py addons/l10n_cr_fe_crlibre/tests/__init__.py \
        addons/l10n_cr_fe_crlibre/__manifest__.py
git commit -m "feat(l10n_cr_fe): notificacion por correo al cliente cuando Hacienda acepta"
```

---

## Task 14: Botón "Reintentar envío FE"

**Files:**
- Modify: `addons/l10n_cr_fe_crlibre/models/account_move.py`
- Modify: `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`
- Create: `addons/l10n_cr_fe_crlibre/tests/test_reintentar_fe.py`
- Modify: `addons/l10n_cr_fe_crlibre/tests/__init__.py`

**Interfaces:**
- Consumes: `_l10n_cr_fe_generate_and_send` (Tarea 11).
- Produces: `account.move.action_l10n_cr_fe_reintentar(self)`.

- [ ] **Step 1: Escribir los tests que fallan**

`addons/l10n_cr_fe_crlibre/tests/test_reintentar_fe.py`:
```python
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestReintentarFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.env.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas Demo SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de demostración',
            'email': 'demo@frutasdemo.cr',
            'hacienda_username': 'user@stag.comprobanteselectronicos.go.cr',
            'hacienda_password': 'secret',
            'certificate_pin': '1234',
            'certificate_download_code': 'DC',
        })
        partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        product = self.env['product.product'].create({
            'name': 'Producto demo', 'l10n_cr_fe_cabys': '0111101000000'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': partner.id,
            'l10n_cr_fe_clave': '1' * 50, 'l10n_cr_fe_state': 'rechazado',
            'l10n_cr_fe_motivo_rechazo': 'Cedula receptor invalida',
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo',
            })],
        })

    def test_reintentar_generates_new_clave_and_succeeds(self):
        nueva_clave = '9' * 50
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                   return_value={'clave': nueva_clave, 'consecutivo': '0' * 20}), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_fe',
                   return_value='<FacturaElectronica/>'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                   return_value='tok'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.sign_xml',
                   return_value='<FacturaElectronica firmada="1"/>'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.send_fe',
                   return_value={'http_status': 202, 'raw': []}):
            self.invoice.action_l10n_cr_fe_reintentar()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'enviado')
        self.assertEqual(self.invoice.l10n_cr_fe_clave, nueva_clave)
        self.assertNotEqual(self.invoice.l10n_cr_fe_clave, '1' * 50)
        self.assertFalse(self.invoice.l10n_cr_fe_motivo_rechazo)
```

`addons/l10n_cr_fe_crlibre/tests/__init__.py` (agregar): `from . import test_reintentar_fe`

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: FALLA (`action_l10n_cr_fe_reintentar` no existe).

- [ ] **Step 3: Implementar la acción**

Agregar a `addons/l10n_cr_fe_crlibre/models/account_move.py`:
```python
    def action_l10n_cr_fe_reintentar(self):
        self.ensure_one()
        self.write({
            'l10n_cr_fe_state': 'draft',
            'l10n_cr_fe_motivo_rechazo': False,
        })
        self._l10n_cr_fe_generate_and_send()
```

- [ ] **Step 4: Agregar el botón a la vista**

En `addons/l10n_cr_fe_crlibre/views/account_move_views.xml`, dentro de `<xpath expr="//header" position="inside">`, agregar (junto al botón de consultar estado):
```xml
                <button name="action_l10n_cr_fe_reintentar"
                        string="Reintentar envío FE"
                        type="object" class="btn-primary"
                        invisible="l10n_cr_fe_state != 'rechazado'"/>
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo -u l10n_cr_fe_crlibre --stop-after-init`
Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u l10n_cr_fe_crlibre --test-enable --test-tags /l10n_cr_fe_crlibre --stop-after-init`
Expected: PASAN — el suite completo debe reportar `0 failed, 0 error(s) of N tests`.

- [ ] **Step 6: Commit**

```bash
git add addons/l10n_cr_fe_crlibre/models/account_move.py addons/l10n_cr_fe_crlibre/views/account_move_views.xml \
        addons/l10n_cr_fe_crlibre/tests/test_reintentar_fe.py addons/l10n_cr_fe_crlibre/tests/__init__.py
git commit -m "feat(l10n_cr_fe): boton para reintentar el envio FE tras un rechazo"
```

---

## Task 15: Verificación manual end-to-end contra el sandbox real de Hacienda

Objetivo: confirmar que todo el pipeline (certificado → clave → XML → firma → token → envío → consulta → correo) funciona contra el **sandbox real** de Hacienda, con los datos tributarios que ya tienes (cédula `208400858`, usuario/contraseña `stag`, PIN, certificado `.p12`). No hay código nuevo; el deliverable es la confirmación y una nota de evidencia sin secretos.

**Files:**
- Create: `docs/superpowers/plans/notes/api-samples-fe-completa.md`

**⚠️ Todos los pasos con credenciales reales son EJECUCIÓN MANUAL DEL USUARIO — no le pegues las credenciales al asistente en el chat; ejecútalos tú mismo en tu terminal.**

- [ ] **Step 1: Confirmar los tres stacks arriba**

Run:
```bash
docker ps --format "{{.Names}} {{.Status}}" | grep -E "erp-odoo-1|crlibre-app|crlibre-mariadb"
```
Expected: los tres contenedores `Up`.

- [ ] **Step 2 (EJECUCIÓN MANUAL DEL USUARIO): Configurar la empresa en Odoo**

En `http://localhost:8069` → Contabilidad → Configuración → Factura Electrónica CR (o el menú creado en la Tarea 1):
1. Crear el registro para tu empresa: ambiente `stag`, cédula `208400858`, tipo de identificación `01` (física), razón social, actividad económica, ubicación, correo.
2. Subir tu certificado `.p12` real y su PIN.
3. Guardar. El `certificate_download_code` debe llenarse solo (dispara `_l10n_cr_fe_ensure_certificate_uploaded` la primera vez que se necesite — si tu flujo de guardado no lo dispara automáticamente todavía, ejecuta manualmente desde el shell de Odoo: `env['l10n_cr.fe.config'].search([], limit=1)._l10n_cr_fe_ensure_certificate_uploaded()`).
4. En "Credenciales y certificado", ingresar tu usuario/contraseña reales de `stag` (`cpf-02-0840-0858@stag.comprobanteselectronicos.go.cr`).

- [ ] **Step 3: Configurar un producto con CABYS real**

Crear o editar un producto de prueba y asignarle un código CABYS real de 13 dígitos (ej. `0111101000000` para frutas frescas, o el que corresponda a tu actividad).

- [ ] **Step 4 (EJECUCIÓN MANUAL DEL USUARIO): Crear y confirmar una factura de prueba**

1. Contabilidad → Clientes → Facturas → Nueva.
2. Cliente con cédula (VAT) numérica válida, una línea con el producto de la Tarea 3.
3. Confirmar (Publicar). Esto dispara `action_post` → todo el flujo automático.
4. Verificar en el chatter: debe aparecer "Comprobante FE enviado a Hacienda. Clave: ...", y el estado FE debe quedar en **Enviado**.

Si queda en **Error**, revisar el chatter para el detalle exacto (fallo de conectividad, credenciales, o algún envelope distinto al documentado en este plan — ver nota de riesgos abajo).

- [ ] **Step 5: Consultar el estado**

Esperar 1-2 minutos (Hacienda procesa en segundo plano) y presionar **"Consultar estado FE"**. Repetir cada pocos minutos hasta que el estado cambie a **Aceptado** o **Rechazado**.

- [ ] **Step 6: Verificar la notificación por correo**

Si el estado queda **Aceptado**, confirmar en Ajustes → Técnico → Correos (o en el log de Odoo si no hay servidor SMTP configurado) que se generó un correo hacia el cliente de la factura, con dos adjuntos XML.

- [ ] **Step 7: Documentar la evidencia (sin secretos)**

Escribir en `docs/superpowers/plans/notes/api-samples-fe-completa.md`:
- La clave de 50 dígitos generada y el consecutivo de 20 dígitos.
- El estado final (aceptado/rechazado) y, si fue rechazado, el motivo (sin datos tributarios sensibles).
- Cualquier ajuste que haya sido necesario hacer al parseo de `send_fe`/`consultar_estado` si el formato real difirió de lo documentado en las Tareas 9 y 12 (ver "Riesgos abiertos" del spec, §10).
- **No** incluir usuario, contraseña, PIN, ni el contenido del certificado.

```bash
cd /d/ERP
git add docs/superpowers/plans/notes/api-samples-fe-completa.md
git commit -m "docs(l10n_cr_fe): evidencia del ciclo completo FE contra el sandbox real de Hacienda"
```

---

## Notas de cierre

- **Fuera de alcance** (ver spec §9): ambiente de producción real, Notas de Crédito/Débito, Tiquete Electrónico, mensajes de confirmación receptor, múltiples sucursales/terminales, catálogo CABYS completo, representación gráfica/PDF, cache/refresh de tokens OAuth, cifrado en BD de credenciales/PIN, consulta de estado por cron.
- **Riesgos a validar en la Tarea 15** (ya documentados en el spec y en las tareas 7, 9 y 12): formato exacto de la respuesta de `send`/`consultar` contra el sandbox real (el parseo de `text`/`ind-estado`/`respuesta-xml` está basado en lectura del código fuente de la API y en el contrato público de Hacienda, no en una respuesta real capturada); si difiere, ajustar `send_fe`/`consultar_estado`/`_l10n_cr_fe_parse_motivo` en consecuencia.
- **Bug de infraestructura documentado:** `mhToken.php` requiere el parche de la Tarea 7 (uso incorrecto de `CURLOPT_HEADER`) para que el token OAuth funcione; vive en `D:\API_Hacienda`, fuera de este repo.

