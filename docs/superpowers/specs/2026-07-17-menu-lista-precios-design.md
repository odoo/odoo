# Acceso directo a "Lista de precios" desde el menú de apps

- **Fecha:** 2026-07-17
- **Estado:** Aprobado (diseño)
- **Alcance:** Agregar un ítem de nivel superior llamado "Lista de precios" al menú desplegable de aplicaciones de Odoo (donde hoy aparecen Ventas, Compras, Inventario, etc.), que abre directamente la pantalla nativa de listas de precios.

---

## 1. Contexto

Las listas de precios por cliente (Fase 1) son el corazón de cómo esta empresa factura — cada cliente tiene la suya, con precios negociados producto por producto. Hoy, para llegar a esa pantalla hay que entrar a Ventas → Configuración → Listas de precios, varios clics escondidos en un menú de configuración. Dado lo seguido que se usa, tiene sentido que sea un acceso directo de un clic.

## 2. Diseño

Se agrega un `ir.ui.menu` sin padre (mismo nivel que Ventas, Compras, Inventario) llamado "Lista de precios", apuntando a la acción nativa `product.product_pricelist_action2` — la misma pantalla (vista lista/kanban/formulario) que ya usa Ventas → Configuración → Listas de precios hoy. No se crea ninguna vista, acción ni lógica nueva: es puramente un acceso directo a algo que ya existe.

Vive en el addon `distribuidora_ventas` (donde ya está la lógica de precio por cliente de la Fase 1), como un archivo de datos XML nuevo.

## 3. Fuera de alcance

- Cualquier vista, acción o campo nuevo — se reutiliza `product.product_pricelist_action2` tal cual.
- Ícono personalizado para el menú — queda con el ícono genérico por defecto de Odoo.

## 4. Verificación

- Confirmar que el menú "Lista de precios" aparece en el desplegable de apps.
- Confirmar que al hacer clic, abre la lista de listas de precios existentes (las mismas que se ven hoy desde Ventas → Configuración → Listas de precios).
