# Renombrar/ocultar menús (Clientes, Preventas, POS) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** El selector de apps de Odoo muestra "Clientes" en vez de "Contactos", "Preventas" en vez de "Ventas", y ya no muestra "Punto de Venta".

**Architecture:** Addon nuevo `distribuidora_config`, con un único archivo de datos XML que sobreescribe tres campos (`name` en dos menús raíz, `active` en uno) de registros nativos existentes, referenciándolos por su ID externo completo. No se modifica ningún módulo de Odoo directamente.

**Tech Stack:** Odoo 19, datos XML, `odoo.tests.common.TransactionCase`.

## Global Constraints

- Imports ordenados: future → stdlib → third-party → odoo → odoo.addons (lo aplica `ruff`) — aplica al archivo de test.
- Tests con `@tagged('post_install', '-at_install')`, `TransactionCase`.
- No se modifica ningún archivo dentro de `addons/contacts/`, `addons/sale/` ni `addons/point_of_sale/` — todo el cambio vive en el addon nuevo, sobreescribiendo registros por ID externo (spec §2.2, §2.3).
- Ocultar "Punto de Venta" es reversible (`active = False`), no se desinstala el módulo (spec §3).
- No se renombra ningún submenú interno de cada app, solo los menús raíz (spec §3).

---

## Task 1: Addon con las tres sobreescrituras y sus tests

**Files:**
- Create: `addons/distribuidora_config/__init__.py`
- Create: `addons/distribuidora_config/__manifest__.py`
- Create: `addons/distribuidora_config/data/menu_overrides.xml`
- Create: `addons/distribuidora_config/tests/__init__.py`
- Create: `addons/distribuidora_config/tests/test_menu_overrides.py`

**Interfaces:**
- Consumes: `contacts.menu_contacts`, `sale.sale_menu_root`, `point_of_sale.menu_point_root` (registros `ir.ui.menu` nativos, ya existentes en los módulos de dependencia).
- Produces: ninguna interfaz nueva — task única del plan.

- [ ] **Step 1: Escribir los tests que fallan (los menús nativos todavía tienen sus valores originales)**

```python
# addons/distribuidora_config/tests/test_menu_overrides.py
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMenuOverrides(TransactionCase):

    def test_contacts_menu_renamed_to_clientes(self):
        menu = self.env.ref('contacts.menu_contacts')
        self.assertEqual(menu.name, 'Clientes')

    def test_sale_menu_renamed_to_preventas(self):
        menu = self.env.ref('sale.sale_menu_root')
        self.assertEqual(menu.name, 'Preventas')

    def test_point_of_sale_menu_is_hidden(self):
        menu = self.env.ref('point_of_sale.menu_point_root')
        self.assertFalse(menu.active)
```

```python
# addons/distribuidora_config/tests/__init__.py
from . import test_menu_overrides
```

- [ ] **Step 2: Crear el manifest y el `__init__.py` raíz (sin el data file todavía)**

```python
# addons/distribuidora_config/__manifest__.py
{
    'name': "Distribuidora - Configuracion",
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': "Renombrar y ocultar menus nativos para esta empresa",
    'author': "Distribuidora",
    'depends': ['contacts', 'sale', 'point_of_sale'],
    'data': [],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
```

```python
# addons/distribuidora_config/__init__.py
```

- [ ] **Step 3: Instalar el módulo y correr los tests para confirmar que fallan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -i distribuidora_config --test-enable --test-tags /distribuidora_config --stop-after-init`

Expected: FAIL — los tres tests fallan por `AssertionError` (`'Contacts' != 'Clientes'`, `'Sales' != 'Preventas'`, `assertFalse` sobre un menú que sigue activo). No deben fallar por "External ID not found" — los tres registros ya existen de forma nativa, solo tienen otros valores.

- [ ] **Step 4: Crear el archivo de sobreescrituras**

```xml
<!-- addons/distribuidora_config/data/menu_overrides.xml -->
<odoo>
    <record id="contacts.menu_contacts" model="ir.ui.menu">
        <field name="name">Clientes</field>
    </record>

    <record id="sale.sale_menu_root" model="ir.ui.menu">
        <field name="name">Preventas</field>
    </record>

    <record id="point_of_sale.menu_point_root" model="ir.ui.menu">
        <field name="active">False</field>
    </record>
</odoo>
```

- [ ] **Step 5: Registrar el archivo en el manifest**

```python
# addons/distribuidora_config/__manifest__.py
    'data': [
        'data/menu_overrides.xml',
    ],
```

- [ ] **Step 6: Actualizar el módulo y correr los tests para confirmar que pasan**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_config --test-enable --test-tags /distribuidora_config --stop-after-init`

Expected: PASS — `0 failed, 0 error(s) of 3 tests`.

- [ ] **Step 7: Commit**

```bash
git add addons/distribuidora_config/__init__.py addons/distribuidora_config/__manifest__.py \
        addons/distribuidora_config/data/menu_overrides.xml \
        addons/distribuidora_config/tests/__init__.py addons/distribuidora_config/tests/test_menu_overrides.py
git commit -m "feat(distribuidora_config): renombrar Contactos/Ventas y ocultar Punto de Venta"
```

---

## Task 2: Verificación manual

**Files:** ninguno (verificación manual, sin cambios de código).

- [ ] **Step 1: Actualizar el módulo y reiniciar el servidor web**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_config --stop-after-init`

Luego: `docker restart erp-odoo-1` (el servidor de `localhost:8069` no recarga menús en caliente).

- [ ] **Step 2: Confirmar en la UI**

En `http://localhost:8069`, abrir el selector de apps → confirmar que aparece "Clientes" (no "Contactos") y "Preventas" (no "Ventas"), y que "Punto de Venta" ya no aparece en la lista. Entrar a "Clientes" y a "Preventas" → confirmar que ambas apps funcionan igual que antes, solo cambió el nombre.
