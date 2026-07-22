# Renombrar/ocultar menús de apps: Clientes, Preventas, Punto de Venta

- **Fecha:** 2026-07-20
- **Estado:** Aprobado (diseño)
- **Alcance:** Tres ajustes de etiquetado/visibilidad sobre menús raíz nativos de Odoo — "Contactos" → "Clientes", "Ventas" → "Preventas", y ocultar "Punto de Venta" — sin tocar ningún módulo de Odoo directamente.

---

## 1. Contexto

Estos tres cambios son puramente de nomenclatura/visibilidad de la interfaz, para que el ERP hable en los términos que usa esta empresa:

- **"Contactos" → "Clientes":** las personas que usan el sistema piensan en "clientes", no en "contactos" (el término genérico de Odoo).
- **"Ventas" → "Preventas":** lo que se registra ahí son pedidos que después alimentan la consolidación de compra — es una preventa, no una venta cerrada en el sentido tradicional.
- **Ocultar "Punto de Venta":** no lo usan (venden por pedido, no por mostrador) y no quieren que aparezca como opción en el sistema por ahora.

Investigado contra el código de este Odoo: los tres son menús raíz (`ir.ui.menu` sin padre) definidos en módulos nativos (`contacts`, `sale`, `point_of_sale`). Sobreescribir su `name` (o su `active` para ocultar) desde un addon propio es la forma estándar y soportada de personalizarlos sin tocar esos módulos.

## 2. Diseño

### 2.1 Addon nuevo `distribuidora_config`

Un addon chico, separado de `distribuidora_ventas`, dedicado a este tipo de ajustes de etiquetado/visibilidad de la interfaz — no es lógica de negocio de ventas, y da un lugar claro para futuros ajustes similares sin mezclar responsabilidades.

- Depende de `contacts`, `sale` y `point_of_sale` (los tres módulos dueños de los menús que se tocan).

### 2.2 Renombrar menús

Un archivo de datos XML que sobreescribe el campo `name` de dos registros existentes, referenciándolos por su ID externo completo (técnica estándar de Odoo para personalizar un registro de otro módulo sin modificarlo):

| Menú | ID externo | Nombre nuevo |
|---|---|---|
| Contactos | `contacts.menu_contacts` | Clientes |
| Ventas | `sale.sale_menu_root` | Preventas |

### 2.3 Ocultar "Punto de Venta"

Mismo mecanismo, sobreescribiendo el campo `active` a `False` en `point_of_sale.menu_point_root`. Esto oculta el menú (y por lo tanto el acceso a la app) sin desinstalar el módulo — reversible con solo cambiar el campo de vuelta, sin perder datos ni configuración.

## 3. Fuera de alcance

- Renombrar submenús internos dentro de cada app (ej. el submenú "Contacts" que vive dentro de la propia app de Contactos) — solo se toca el nombre del menú raíz, que es lo que se ve en el selector de apps y en el breadcrumb.
- Desinstalar el módulo `point_of_sale` — se oculta, no se elimina.
- El descuento en facturación (punto 2 del pedido original) — no requiere código, se resuelve activando un ajuste nativo de Odoo (Ventas → Configuración → Ajustes → Precios → "Otorgar descuentos en las líneas del pedido de venta"), fuera del alcance de este spec.

## 4. Verificación

- Confirmar que el selector de apps muestra "Clientes" en vez de "Contactos", y "Preventas" en vez de "Ventas".
- Confirmar que "Punto de Venta" ya no aparece en el selector de apps.
- Confirmar que las funciones internas de cada app (contactos, pedidos, etc.) siguen funcionando igual — el cambio es solo de nombre/visibilidad, no de comportamiento.
