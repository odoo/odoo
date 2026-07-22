# Ocultar CRM del menú de apps

- **Fecha:** 2026-07-22
- **Estado:** Aprobado (diseño)
- **Alcance:** Ocultar el menú raíz de CRM del selector de aplicaciones de Odoo, para todos los usuarios. El módulo `crm` sigue instalado.

---

## 1. Contexto

El usuario pidió que "CRM" ya no aparezca en el selector de apps — no lo usan para su operación. Ya existe un precedente idéntico en este mismo addon (`distribuidora_config`): el menú raíz de Punto de Venta se oculta con `active=False` sobre `point_of_sale.menu_point_root`, dejando el módulo instalado (por si hay datos o configuración que dependan de él), solo invisible en la navegación. Se confirmó con el usuario aplicar el mismo tratamiento a CRM en vez de desinstalar el módulo.

## 2. Objetivo y definición de "hecho"

Que el ícono "CRM" ya no aparezca en el selector de apps para ningún usuario.

**Éxito =** al abrir el selector de apps, "CRM" no aparece en la lista; el módulo `crm` sigue instalado y funcional para quien acceda a sus vistas por otra vía (URL directa, developer mode, etc.) — solo se oculta el acceso de navegación normal.

## 3. Diseño

En `addons/distribuidora_config/data/menu_overrides.xml`, agregar:

```xml
<record id="crm.crm_menu_root" model="ir.ui.menu">
    <field name="active">False</field>
</record>
```

Mismo patrón que el registro existente para `point_of_sale.menu_point_root` en el mismo archivo.

**Manifest:** agregar `'crm'` a `depends` en `addons/distribuidora_config/__manifest__.py`. Hoy el addon no lo declara aunque `crm` ya está instalado en este entorno — sin la dependencia explícita, instalar `distribuidora_config` en un entorno sin `crm` fallaría al resolver el xmlid `crm.crm_menu_root`.

**No se toca** el módulo `crm` en sí, ni sus vistas, ni sus permisos — solo la visibilidad de su menú raíz.

## 4. Fuera de alcance

- Desinstalar el módulo `crm` — se descartó explícitamente; se prefiere ocultar y mantener los datos/configuración disponibles.
- Revocar permisos o grupos de CRM — un usuario que acceda por otra vía conserva su acceso; solo cambia la navegación.

## 5. Estrategia de pruebas

- Test que confirma que `crm.crm_menu_root.active` es `False` tras instalar/actualizar el addon, siguiendo el mismo patrón que `test_point_of_sale_menu_is_hidden`.
