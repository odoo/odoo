# Ocultar CRM del menú de apps — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ocultar el menú raíz de CRM del selector de apps de Odoo para todos los usuarios, sin desinstalar el módulo.

**Architecture:** Un `<record>` en `addons/distribuidora_config/data/menu_overrides.xml` que pone `active=False` sobre `crm.crm_menu_root` — mismo patrón ya usado ahí para `point_of_sale.menu_point_root`. Sin modelo ni lógica Python nueva.

**Tech Stack:** Odoo 19 `ir.ui.menu`, XML data files, `TransactionCase`.

## Global Constraints

- El módulo `crm` sigue instalado — solo se oculta la navegación, no se desinstala ni se tocan sus vistas o permisos (spec §3, §4).
- Debe agregarse `'crm'` a `depends` en el manifest de `distribuidora_config`, porque el addon referenciará el xmlid `crm.crm_menu_root` (spec §3).
- Rama de trabajo: `feat/ocultar-crm-menu` (ya activa en el repo, partió de `19.0` actualizado).

---

### Task 1: Ocultar crm.crm_menu_root

**Files:**
- Modify: `addons/distribuidora_config/__manifest__.py`
- Modify: `addons/distribuidora_config/data/menu_overrides.xml`
- Test: `addons/distribuidora_config/tests/test_menu_overrides.py`

**Interfaces:**
- Consumes: xmlid existente `crm.crm_menu_root` (definido en `addons/crm/views/crm_menu_views.xml:10`).
- Produces: nada que otras tareas consuman — es la única tarea de este plan.

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de la clase `TestMenuOverrides` en `addons/distribuidora_config/tests/test_menu_overrides.py`:

```python
    def test_crm_menu_is_hidden(self):
        menu = self.env.ref('crm.crm_menu_root')
        self.assertFalse(menu.active)
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_config --test-enable --test-tags /distribuidora_config --stop-after-init`

Expected: FAIL — `AssertionError: True is not false` (el menú de CRM sigue activo por defecto).

- [ ] **Step 3: Agregar la dependencia al manifest**

En `addons/distribuidora_config/__manifest__.py`, cambiar:

```python
    'depends': ['contacts', 'sale_management', 'point_of_sale'],
```

por:

```python
    'depends': ['contacts', 'sale_management', 'point_of_sale', 'crm'],
```

- [ ] **Step 4: Ocultar el menú de CRM**

En `addons/distribuidora_config/data/menu_overrides.xml`, agregar el registro después del de `point_of_sale.menu_point_root`:

```xml
    <record id="crm.crm_menu_root" model="ir.ui.menu">
        <field name="active">False</field>
    </record>
```

El archivo completo queda así:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="point_of_sale.menu_point_root" model="ir.ui.menu">
        <field name="active">False</field>
    </record>

    <record id="crm.crm_menu_root" model="ir.ui.menu">
        <field name="active">False</field>
    </record>

    <menuitem id="menu_productos_root"
        name="Productos"
        action="sale.product_template_action"
        web_icon="product,static/description/icon.png"
        groups="sales_team.group_sale_salesman"
        sequence="32"/>

    <!--
        El nombre de contacts.menu_contacts y sale.sale_menu_root se
        renombra vía _distribuidora_config_apply_menu_names en vez de un
        <field name="name"> directo, porque "name" es un campo traducible:
        escribirlo aquí solo tocaría el idioma de referencia (en_US), no
        el idioma real de los usuarios (es_CR). El método recorre todos
        los idiomas instalados. Se ejecuta en cada -u de este addon, no
        solo en la instalación inicial.
    -->
    <function model="ir.ui.menu" name="_distribuidora_config_apply_menu_names" eval="[]"/>
</odoo>
```

- [ ] **Step 5: Correr el test y confirmar que pasa**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_config --test-enable --test-tags /distribuidora_config --stop-after-init`

Expected: `0 failed, 0 error(s)` — incluyendo `test_crm_menu_is_hidden` en la lista de tests corridos (deberían ser 7 tests en total: los 6 existentes más este).

- [ ] **Step 6: Commit**

```bash
git add addons/distribuidora_config/__manifest__.py addons/distribuidora_config/data/menu_overrides.xml addons/distribuidora_config/tests/test_menu_overrides.py
git commit -m "feat(distribuidora_config): ocultar CRM del menu de apps"
```

---

## Verificación manual (a cargo del usuario)

Después de actualizar el addon en el entorno real: abrir el switcher de apps (ícono de grid) y confirmar que "CRM" ya no aparece en la lista.
