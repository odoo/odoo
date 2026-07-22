# Menú "Productos" en el switcher de apps

- **Fecha:** 2026-07-22
- **Estado:** Aprobado (diseño)
- **Alcance:** Agregar "Productos" como app propia en el menú de aplicaciones (el dropdown que se abre con el ícono de grid), reutilizando el catálogo de productos que ya existe dentro de Preventas.

---

## 1. Contexto

El menú de aplicaciones de Odoo (el dropdown con el ícono de grid, visible en cualquier pantalla) se arma a partir de los `ir.ui.menu` raíz (sin padre) que tienen `web_icon` y a los que el usuario tiene acceso. Hoy "Productos" no aparece ahí: solo existe como submenú dentro de Preventas (`sale.product_menu_catalog` → `sale.product_template_action`).

El usuario pidió agregar "Productos" a esa lista, para no tener que entrar a Preventas cada vez que solo necesita gestionar el catálogo.

Este cambio vive en `distribuidora_config`, el addon donde ya están los otros ajustes de menú de esta empresa (renombrar Contactos→Clientes, Ventas→Preventas; ocultar Punto de Venta), sobre la rama `feat/config-menus-clientes-preventas-pos`.

## 2. Objetivo y definición de "hecho"

Que al abrir el menú de aplicaciones aparezca "Productos" como opción propia, entre "Preventas" y "Tableros", y que al hacer clic muestre el mismo catálogo de productos que ya se usa dentro de Preventas.

**Éxito =** el ítem "Productos" aparece en el dropdown de apps en la posición esperada, con su propio ícono, y abre la lista de productos con los mismos permisos y datos que "Preventas → Productos".

## 3. Diseño

Un nuevo `menuitem` raíz en `addons/distribuidora_config/data/menu_overrides.xml`:

```xml
<menuitem id="menu_productos_root"
    name="Productos"
    action="sale.product_template_action"
    web_icon="product,static/description/icon.png"
    groups="sales_team.group_sale_salesman"
    sequence="32"/>
```

- **Acción:** reutiliza `sale.product_template_action` (la misma vista/acción que usa hoy "Preventas → Productos"). No se crea ninguna vista ni acción nueva.
- **Ícono:** `product,static/description/icon.png` — el ícono nativo del módulo `product`, distinto al de Preventas para que se distinga visualmente en la barra de apps.
- **Posición:** `sequence="32"`, entre el root de Preventas (`sale.sale_menu_root`, sequence 30) y el de Tableros (`spreadsheet_dashboard.spreadsheet_dashboard_menu_root`, sequence 37).
- **Permisos:** `groups="sales_team.group_sale_salesman"`, el mismo grupo que ya protege "Productos" dentro de Preventas (`sale.product_menu_catalog`). No se amplía ni reduce quién puede ver productos — solo se agrega un acceso directo para quien ya podía verlos.

No se modifica el menú "Productos" existente dentro de Preventas; sigue igual, sin cambios.

## 4. Fuera de alcance

- Cualquier vista o acción nueva de productos — se reutiliza `sale.product_template_action` tal cual.
- Cambios de permisos — nadie gana ni pierde acceso a productos por este cambio.
- El menú "Productos" dentro de Preventas — no se toca.

## 5. Estrategia de pruebas

- Test que confirma que `distribuidora_config.menu_productos_root` existe, no tiene `parent_id` (o sea que es raíz / aparece como app), apunta a `sale.product_template_action` y tiene `sequence == 32`.
