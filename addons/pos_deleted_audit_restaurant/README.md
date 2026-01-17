# Auditoria Eliminados Pos Restaurante

Módulo desarrollado por **Jbnegoc SPA** (https://jbnegoc.com) con derechos reservados.

## Dependencias

- Odoo 16 Community
- Módulos base: `point_of_sale`

No requiere dependencias adicionales de Python.

## Instalación

1. Copiar el módulo `pos_deleted_audit_restaurant` dentro del directorio `addons` de Odoo.
2. Actualizar la lista de aplicaciones.
3. Instalar el módulo **Auditoria Eliminados Pos Restaurante** desde Apps.

## Configuración funcional (paso a paso)

1. Ir a **Ajustes → Usuarios y compañías → Usuarios**.
2. Abrir el usuario que debe operar en el POS.
3. En la pestaña **Permisos / Accesos**, dentro del grupo **Auditoría Eliminados POS**:
   - Activar **Solicitar justificación al eliminar en POS** para mostrar el cuadro de justificación.
   - Activar **Acceso y eliminación de auditorías POS** para habilitar el reporte y permitir borrar registros.
4. Ir a **Punto de Venta → Configuración → Justificaciones de Eliminaciones** y crear las razones predeterminadas.

## Operación (usuarios finales)

- Al reducir la cantidad o eliminar una línea en el POS, se abrirá el popup **Justificación**.
- El usuario puede seleccionar una justificación predefinida o escribir la razón manualmente.
- Al confirmar, se registra la auditoría y el pedido se actualiza.
- El reporte **Punto de Venta → Reportes → Productos Eliminados** muestra:
  - Número de pedido
  - Producto
  - Cantidad eliminada
  - Usuario
  - Fecha y hora
  - Resumen de justificación (en lista)
- En el formulario del registro se ve la justificación completa.
- Usuarios con **Acceso y eliminación de auditorías POS** pueden borrar registros en masa o de forma individual.

## Documentación técnica

### Modelos

- `pos.deleted.justification`
  - `name` (Char, requerido): texto de la justificación.
  - `description` (Text): descripción adicional.
  - `active` (Boolean): control de vigencia.

- `pos.deleted.product.audit`
  - `order_name` (Char, requerido): número de pedido.
  - `product_id` (Many2one, requerido): producto eliminado.
  - `removed_qty` (Float, requerido): cantidad eliminada.
  - `user_id` (Many2one, requerido): usuario que elimina.
  - `deletion_datetime` (Datetime, requerido): fecha/hora de eliminación.
  - `justification` (Text, requerido): detalle de la justificación.
  - `justification_summary` (Char, calculado): resumen para vista lista.

### Seguridad

- Grupo `Auditoría Eliminados POS` controla el acceso al reporte y la posibilidad de eliminar registros.
- El método `unlink` del modelo de auditoría valida el campo de usuario para bloquear eliminaciones no autorizadas.
- Las justificaciones pueden ser gestionadas por usuarios POS Manager; los usuarios POS solo pueden leerlas.

### Integración POS

- Se cargan las justificaciones activas en el frontend mediante `models.load_models`.
- Se agrega un popup personalizado (`PosDeletedJustificationPopupWidget`) para capturar la justificación.
- Se intercepta `Orderline.set_quantity`:
  - Si la cantidad disminuye o se elimina, se solicita justificación.
  - Al confirmar, se registra el evento con `create_from_ui` en `pos.deleted.product.audit`.

### Archivos clave

- Backend:
  - `models/pos_deleted_justification.py`
  - `models/pos_deleted_product_audit.py`
  - `models/res_users.py`
- Frontend:
  - `static/src/js/pos_deleted_audit.js`
  - `static/src/xml/pos_deleted_audit.xml`
- Vistas:
  - `views/pos_deleted_justification_views.xml`
  - `views/pos_deleted_product_audit_views.xml`
  - `views/res_users_views.xml`

