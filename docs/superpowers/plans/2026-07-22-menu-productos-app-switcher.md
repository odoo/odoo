# Menú "Productos" en el switcher de apps — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar "Productos" como app propia en el menú de aplicaciones de Odoo, reutilizando el catálogo de productos que ya existe dentro de Preventas.

**Architecture:** Un `menuitem` raíz nuevo en `addons/distribuidora_config/data/menu_overrides.xml`, sin modelo ni acción nueva — reutiliza `sale.product_template_action` (la misma vista que usa hoy "Preventas → Productos").

**Tech Stack:** Odoo 19 `ir.ui.menu`, XML data files, `TransactionCase`.

## Global Constraints

- No se crea ninguna vista ni acción de productos nueva — se reutiliza `sale.product_template_action` tal cual (spec §3).
- El grupo de acceso es `sales_team.group_sale_salesman` — el mismo que ya protege "Productos" dentro de Preventas; nadie gana ni pierde acceso (spec §3).
- El `sequence` debe ser `32`, para quedar entre el root de Preventas (`sale.sale_menu_root`, sequence 30) y el de Tableros (`spreadsheet_dashboard.spreadsheet_dashboard_menu_root`, sequence 37) (spec §3).
- No se toca el menú "Productos" existente dentro de Preventas (spec §4).
- Rama de trabajo: `feat/config-menus-clientes-preventas-pos` (ya activa en el repo).

---

### Task 1: Menuitem raíz "Productos"

**Files:**
- Modify: `addons/distribuidora_config/data/menu_overrides.xml`
- Test: `addons/distribuidora_config/tests/test_menu_overrides.py`

**Interfaces:**
- Consumes: acción existente `sale.product_template_action` (definida en `addons/sale/views/product_views.xml:91`), grupo existente `sales_team.group_sale_salesman`.
- Produces: `ir.ui.menu` con id externo `distribuidora_config.menu_productos_root`. Ningún otro archivo de este plan depende de él (es la única tarea).

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de la clase `TestMenuOverrides` en `addons/distribuidora_config/tests/test_menu_overrides.py`:

```python
    def test_productos_menu_is_root_app_pointing_to_sale_catalog(self):
        menu = self.env.ref('distribuidora_config.menu_productos_root')
        self.assertFalse(menu.parent_id, "debe ser un menu raiz para aparecer en el switcher de apps")
        self.assertEqual(menu.action, 'ir.actions.act_window,%d' % self.env.ref('sale.product_template_action').id)
        self.assertEqual(menu.sequence, 32)
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_config --test-enable --test-tags /distribuidora_config --stop-after-init`

Expected: FAIL — `ValueError: External ID not found in the system: distribuidora_config.menu_productos_root`

- [ ] **Step 3: Agregar el menuitem**

En `addons/distribuidora_config/data/menu_overrides.xml`, agregar antes del `<function .../>` final (después del bloque `point_of_sale.menu_point_root`, antes del comentario de renombrado):

```xml
    <menuitem id="menu_productos_root"
        name="Productos"
        action="sale.product_template_action"
        web_icon="product,static/description/icon.png"
        groups="sales_team.group_sale_salesman"
        sequence="32"/>

```

El archivo completo queda así:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="point_of_sale.menu_point_root" model="ir.ui.menu">
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

- [ ] **Step 4: Correr el test y confirmar que pasa**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_config --test-enable --test-tags /distribuidora_config --stop-after-init`

Expected: `0 failed, 0 error(s)` — incluyendo `test_productos_menu_is_root_app_pointing_to_sale_catalog` en la lista de tests corridos.

- [ ] **Step 5: Commit**

```bash
git add addons/distribuidora_config/data/menu_overrides.xml addons/distribuidora_config/tests/test_menu_overrides.py
git commit -m "feat(distribuidora_config): agregar menu raiz Productos al switcher de apps"
```

---

## Verificación manual (a cargo del usuario)

Después de mergear/actualizar el addon en el entorno real: abrir el switcher de apps (ícono de grid) y confirmar que "Productos" aparece entre "Preventas" y "Tableros", con su propio ícono, y que al hacer clic muestra el catálogo de productos.
