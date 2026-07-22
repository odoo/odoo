# Acceso directo a "Lista de precios" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un ítem de menú de nivel superior ("Lista de precios", junto a Ventas/Compras/Inventario en el desplegable de apps) que abre directamente la pantalla nativa de listas de precios.

**Architecture:** Un solo archivo de datos XML nuevo en `distribuidora_ventas`, con un `ir.ui.menu` sin padre apuntando a la acción nativa `product.product_pricelist_action2`. Sin modelos, vistas ni lógica nueva.

**Tech Stack:** Odoo 19, vistas XML, `odoo.tests.common.TransactionCase`.

## Global Constraints

- Imports ordenados: future → stdlib → third-party → odoo → odoo.addons (lo aplica `ruff`) — aplica solo al archivo de test, ya que el resto de esta task es XML.
- Tests con `@tagged('post_install', '-at_install')`, `TransactionCase`, igual que el resto del addon.
- Se reutiliza `product.product_pricelist_action2` tal cual — no se crea ninguna acción, vista o campo nuevo (spec §3).
- El menú se restringe con `groups="product.group_product_pricelist"`, igual que el menú nativo equivalente en `addons/sale/views/sale_menus.xml:65-69` — así solo aparece si la funcionalidad de listas de precios está activada (Ventas → Configuración → Ajustes), consistente con el resto de Odoo.

---

## Task 1: Menú de nivel superior "Lista de precios"

**Files:**
- Create: `addons/distribuidora_ventas/views/pricelist_menu.xml`
- Create: `addons/distribuidora_ventas/tests/test_pricelist_menu.py`
- Modify: `addons/distribuidora_ventas/__manifest__.py`
- Modify: `addons/distribuidora_ventas/tests/__init__.py`

**Interfaces:**
- Consumes: `product.product_pricelist_action2` (acción nativa de Odoo, ya existente en `addons/product/views/product_pricelist_views.xml:96`).
- Produces: `ir.ui.menu` con XML ID `distribuidora_ventas.menu_lista_precios_root`.

- [ ] **Step 1: Escribir el test que falla (el menú todavía no existe)**

```python
# addons/distribuidora_ventas/tests/test_pricelist_menu.py
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestListaPreciosMenu(TransactionCase):

    def test_menu_is_top_level_and_points_to_pricelist_action(self):
        menu = self.env.ref('distribuidora_ventas.menu_lista_precios_root')
        self.assertFalse(menu.parent_id)
        self.assertEqual(menu.action.res_model, 'product.pricelist')
```

```python
# addons/distribuidora_ventas/tests/__init__.py
from . import test_partner_categories
from . import test_customer_pricelist
from . import test_invoice_from_order_quantity
from . import test_sale_order_accepts_any_delivery_date
from . import test_sale_order_form_hides_commitment_date
from . import test_pricelist_menu
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --test-enable --test-tags /distribuidora_ventas --stop-after-init`

Expected: FAIL — `ValueError: External ID not found in the system: distribuidora_ventas.menu_lista_precios_root`.

- [ ] **Step 3: Crear el menú**

```xml
<!-- addons/distribuidora_ventas/views/pricelist_menu.xml -->
<odoo>
    <menuitem id="menu_lista_precios_root"
              name="Lista de precios"
              action="product.product_pricelist_action2"
              groups="product.group_product_pricelist"
              sequence="140"/>
</odoo>
```

- [ ] **Step 4: Registrar el archivo en el manifest**

```python
# addons/distribuidora_ventas/__manifest__.py
    'data': [
        'data/res_partner_category_data.xml',
        'views/sale_order_views.xml',
        'views/pricelist_menu.xml',
    ],
```

- [ ] **Step 5: Actualizar el módulo y correr el test para confirmar que pasa**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --test-enable --test-tags /distribuidora_ventas --stop-after-init`

Expected: PASS — `0 failed, 0 error(s) of 8 tests` (7 anteriores + 1 nuevo).

- [ ] **Step 6: Commit**

```bash
git add addons/distribuidora_ventas/views/pricelist_menu.xml \
        addons/distribuidora_ventas/__manifest__.py \
        addons/distribuidora_ventas/tests/__init__.py \
        addons/distribuidora_ventas/tests/test_pricelist_menu.py
git commit -m "feat(distribuidora_ventas): agregar acceso directo a lista de precios en menu de apps"
```

---

## Task 2: Verificación manual

**Files:** ninguno (verificación manual, sin cambios de código).

- [ ] **Step 1: Actualizar el módulo y reiniciar el servidor web**

Run: `MSYS_NO_PATHCONV=1 docker exec erp-odoo-1 odoo -d odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8099 --gevent-port=8101 -u distribuidora_ventas --stop-after-init`

Luego: `docker restart erp-odoo-1` (el servidor de `localhost:8069` no recarga menús/vistas en caliente).

- [ ] **Step 2: Confirmar en la UI**

En `http://localhost:8069`, abrir el desplegable de apps (ícono de grilla arriba a la izquierda) → confirmar que aparece "Lista de precios" al mismo nivel que Ventas/Compras/Inventario → hacer clic → confirmar que abre la misma pantalla de listas de precios que hoy se ve desde Ventas → Configuración → Listas de precios.
