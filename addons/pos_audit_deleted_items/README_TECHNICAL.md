# Documentación Técnica - Auditoría de Eliminaciones en POS

**Módulo:** `pos_audit_deleted_items`
**Versión:** 16.0.1.0.0
**Desarrollado por:** Jbnegoc SPA
**Licencia:** LGPL-3
**Compatible con:** Odoo 16.0 Community Edition

---

## Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Arquitectura del Módulo](#arquitectura-del-módulo)
3. [Modelos de Datos](#modelos-de-datos)
4. [Flujo de Funcionamiento](#flujo-de-funcionamiento)
5. [Implementación Frontend (JavaScript)](#implementación-frontend-javascript)
6. [Seguridad y Permisos](#seguridad-y-permisos)
7. [Vistas y Menús](#vistas-y-menús)
8. [Integración con POS](#integración-con-pos)
9. [Consideraciones Técnicas](#consideraciones-técnicas)
10. [API y Métodos Personalizados](#api-y-métodos-personalizados)
11. [Troubleshooting](#troubleshooting)

---

## Descripción General

Este módulo implementa un sistema de auditoría completo para rastrear todas las eliminaciones de productos en el Punto de Venta de Odoo. Está diseñado para funcionar tanto con POS estándar como con POS Restaurant.

### Características Principales

- ✅ Control granular por usuario de auditoría habilitada/deshabilitada
- ✅ Popup interactivo en tiempo real al eliminar productos
- ✅ Justificaciones predeterminadas configurables
- ✅ Registro detallado con trazabilidad completa
- ✅ Control de permisos para eliminar registros de auditoría
- ✅ Compatible con modo offline del POS
- ✅ Sincronización automática con el backend

---

## Arquitectura del Módulo

### Estructura de Directorios

```
pos_audit_deleted_items/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── res_users.py              # Extensión de usuarios
│   ├── pos_deletion_reason.py    # Justificaciones predeterminadas
│   ├── pos_audit_deleted.py      # Modelo principal de auditoría
│   └── pos_order.py              # Extensión de órdenes POS
├── static/
│   └── src/
│       ├── js/
│       │   └── pos_audit.js      # Lógica JavaScript del POS
│       └── xml/
│           └── pos_audit.xml     # Templates QWeb
├── views/
│   ├── res_users_view.xml        # Vista de usuarios extendida
│   ├── pos_deletion_reason_view.xml # Vista de justificaciones
│   ├── pos_audit_deleted_view.xml   # Vista de reportes
│   └── menu.xml                  # Estructura de menús
├── security/
│   ├── security.xml              # Grupos y reglas de seguridad
│   └── ir.model.access.csv       # Control de acceso a modelos
└── data/
    └── pos_deletion_reason_data.xml # Datos iniciales
```

### Dependencias

```python
'depends': [
    'point_of_sale',      # Módulo base del POS (obligatorio)
    'pos_restaurant',     # Módulo de restaurante (opcional)
]
```

**Nota:** El módulo funciona sin `pos_restaurant`, pero si está instalado, también registrará la mesa asociada.

---

## Modelos de Datos

### 1. `res.users` (Extensión)

**Archivo:** `models/res_users.py`

Extiende el modelo de usuarios para agregar campos de control de auditoría.

#### Campos Agregados

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pos_audit_enabled` | Boolean | Activa/desactiva auditoría para el usuario |
| `pos_audit_can_delete` | Boolean | Permite eliminar registros de auditoría |

#### Métodos Personalizados

```python
@api.model
def get_pos_audit_settings(self, user_id):
    """
    Obtiene configuración de auditoría de un usuario.

    :param user_id: ID del usuario
    :return: dict con 'audit_enabled' y 'can_delete'
    """
```

**Uso desde frontend:**
```javascript
rpc.query({
    model: 'res.users',
    method: 'get_pos_audit_settings',
    args: [user_id],
})
```

---

### 2. `pos.deletion.reason`

**Archivo:** `models/pos_deletion_reason.py`

Modelo para almacenar justificaciones predeterminadas.

#### Campos

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `name` | Char | Sí | Texto de la justificación |
| `sequence` | Integer | No | Orden de aparición (default: 10) |
| `active` | Boolean | No | Activo/Inactivo (default: True) |
| `description` | Text | No | Descripción interna |

#### Restricciones

- El nombre debe tener al menos 3 caracteres (`_check_name`)
- Los registros se ordenan por `sequence` y `name`

#### Justificaciones Predeterminadas

Se crean 10 justificaciones iniciales:

1. Cliente cambió de opinión
2. Error al ingresar el pedido
3. Producto no disponible en cocina
4. Producto defectuoso o en mal estado
5. Cliente canceló el pedido completo
6. Tiempo de espera excesivo
7. Modificación de la orden por alergias
8. Duplicado por error
9. Precio incorrecto - ajuste necesario
10. Cortesía de la casa

---

### 3. `pos.audit.deleted`

**Archivo:** `models/pos_audit_deleted.py`

Modelo principal que almacena todos los registros de auditoría.

#### Campos

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `display_name` | Char | - | Nombre computado del registro |
| `pos_order_id` | Many2one('pos.order') | No | Referencia al pedido |
| `pos_order_name` | Char | Sí | Número del pedido |
| `pos_session_id` | Many2one('pos.session') | No | Sesión POS |
| `product_id` | Many2one('product.product') | Sí | Producto eliminado |
| `product_name` | Char | Sí | Nombre del producto |
| `product_code` | Char | No | Código de referencia interna |
| `qty_deleted` | Float | Sí | Cantidad eliminada |
| `price_unit` | Float | No | Precio unitario |
| `price_subtotal` | Float | - | Subtotal (computado) |
| `user_id` | Many2one('res.users') | Sí | Usuario que eliminó |
| `user_name` | Char | Sí | Nombre del usuario |
| `deletion_datetime` | Datetime | Sí | Fecha y hora exacta |
| `deletion_reason` | Text | Sí | Justificación completa |
| `deletion_reason_summary` | Char | - | Resumen (computado) |
| `pos_config_id` | Many2one('pos.config') | No | Punto de venta |
| `table_id` | Many2one('restaurant.table') | No | Mesa (si es restaurante) |
| `company_id` | Many2one('res.company') | Sí | Compañía |

#### Campos Computados

##### `display_name`

```python
@api.depends('product_name', 'pos_order_name', 'deletion_datetime')
def _compute_display_name(self):
    """
    Formato: "Producto - Pedido - Fecha"
    Ejemplo: "Café Americano - Order 00003-001-0001 - 2026-01-15 14:30"
    """
```

##### `price_subtotal`

```python
@api.depends('qty_deleted', 'price_unit')
def _compute_price_subtotal(self):
    """
    Calcula: qty_deleted × price_unit
    """
```

##### `deletion_reason_summary`

```python
@api.depends('deletion_reason')
def _compute_deletion_reason_summary(self):
    """
    Toma primeros 50 caracteres de la justificación para vista de lista
    """
```

#### Métodos Personalizados

##### `create_deletion_record(vals)`

```python
@api.model
def create_deletion_record(self, vals):
    """
    Crea un registro de eliminación desde el frontend.

    Campos requeridos en vals:
    - pos_order_name: str
    - product_id: int
    - qty_deleted: float
    - user_id: int
    - deletion_reason: str

    Campos opcionales:
    - price_unit: float
    - table_id: int
    - pos_session_id: int
    - pos_config_id: int

    :return: ID del registro creado
    """
```

##### `unlink()` (Sobrescrito)

```python
def unlink(self):
    """
    Solo usuarios con pos_audit_can_delete pueden eliminar.
    Lanza UserError si no tiene permiso.
    """
```

##### `action_view_order()`

```python
def action_view_order(self):
    """
    Abre el formulario del pedido relacionado.
    """
```

##### `action_view_product()`

```python
def action_view_product(self):
    """
    Abre el formulario del producto relacionado.
    """
```

---

### 4. `pos.order` (Extensión)

**Archivo:** `models/pos_order.py`

Extiende el modelo de órdenes POS para integrar la auditoría.

#### Campos Agregados

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `deleted_items_count` | Integer (computado) | Cantidad de items eliminados |
| `audit_deleted_ids` | One2many('pos.audit.deleted', 'pos_order_id') | Registros de auditoría |

#### Métodos Personalizados

##### `action_view_deleted_items()`

```python
def action_view_deleted_items(self):
    """
    Abre vista de productos eliminados filtrada para este pedido.
    """
```

##### `create_audit_records_from_ui(order_id, audit_items)`

```python
@api.model
def create_audit_records_from_ui(self, order_id, audit_items):
    """
    Crea múltiples registros de auditoría desde el frontend.

    :param order_id: ID del pedido
    :param audit_items: lista de dict con datos de eliminaciones
    :return: lista de IDs creados

    Ejemplo de audit_items:
    [
        {
            'product_id': 123,
            'qty_deleted': 2.0,
            'price_unit': 5.50,
            'user_id': 2,
            'deletion_reason': 'Cliente cambió de opinión',
            'deletion_datetime': '2026-01-15T14:30:00',
            'table_id': 5,  # opcional
        },
        ...
    ]
    """
```

---

## Flujo de Funcionamiento

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Usuario elimina producto en POS (disminuye cantidad o borra)│
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. JavaScript intercepta la acción en set_quantity()            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Verifica si auditoría está habilitada para el usuario        │
│    - Si NO: procede normal (sin auditoría)                      │
│    - Si SÍ: continúa al paso 4                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Muestra popup "DeletionReasonPopup"                          │
│    - Información del producto                                   │
│    - Cantidad eliminada                                         │
│    - Botones de justificaciones predeterminadas                 │
│    - Textarea para justificación personalizada                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
        ┌───────────────┐       ┌─────────────┐
        │ Usuario       │       │ Usuario     │
        │ CONFIRMA      │       │ CANCELA     │
        │ (con razón)   │       │             │
        └───────┬───────┘       └──────┬──────┘
                │                      │
                │                      ▼
                │              ┌──────────────────┐
                │              │ No hace nada     │
                │              │ (no elimina)     │
                │              └──────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Registra eliminación en order.audit_deleted_items (array)    │
│    Datos almacenados:                                           │
│    - product_id, product_name                                   │
│    - qty_deleted, price_unit                                    │
│    - user_id, deletion_reason                                   │
│    - deletion_datetime                                          │
│    - table_id (si existe)                                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Procede con la eliminación normal (set_quantity)             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. Usuario finaliza la orden y paga                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. POS sincroniza orden con backend (push_order)                │
│    - export_as_JSON incluye audit_deleted_items                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. Backend crea pos.order y retorna ID                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 10. JavaScript llama create_audit_records_from_ui()             │
│     con order_id y audit_deleted_items                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 11. Backend crea registros en pos.audit.deleted                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 12. Registros disponibles en:                                   │
│     Punto de Ventas / Reportes / Productos Eliminados           │
└─────────────────────────────────────────────────────────────────┘
```

### Escenarios de Uso

#### Escenario 1: Disminución de Cantidad

```
Estado inicial: Línea con cantidad 5
Usuario cambia cantidad a 3
Resultado: Se eliminan 2 unidades → solicita justificación
```

#### Escenario 2: Eliminación Completa

```
Estado inicial: Línea con cantidad 3
Usuario presiona botón eliminar (X)
Resultado: Se eliminan 3 unidades → solicita justificación
```

#### Escenario 3: Incremento de Cantidad (NO audita)

```
Estado inicial: Línea con cantidad 3
Usuario cambia cantidad a 5
Resultado: Se agregan 2 unidades → NO solicita justificación
```

#### Escenario 4: Usuario sin Auditoría Habilitada

```
Usuario con pos_audit_enabled = False
Cualquier eliminación procede normal sin popup
```

---

## Implementación Frontend (JavaScript)

**Archivo:** `static/src/js/pos_audit.js`

### Extensión de PosModel

```javascript
models.PosModel = models.PosModel.extend({
    initialize: function(session, attributes) {
        // Cargar modelo pos.deletion.reason
        models.load_models({
            model: 'pos.deletion.reason',
            fields: ['name', 'sequence', 'active'],
            domain: [['active', '=', true]],
            loaded: function(self, deletion_reasons) {
                self.deletion_reasons = deletion_reasons;
            },
        });

        // Cargar campos adicionales de res.users
        models.load_fields('res.users', [
            'pos_audit_enabled',
            'pos_audit_can_delete'
        ]);
    },

    is_audit_enabled: function() {
        var user = this.get_cashier() || this.user;
        return user && user.pos_audit_enabled;
    },
});
```

### Extensión de Order

```javascript
models.Order = models.Order.extend({
    initialize: function(attributes, options) {
        // Array temporal para items eliminados
        this.audit_deleted_items = [];
    },

    add_deleted_item_audit: function(product, qty_deleted, price_unit, reason) {
        // Agrega item al array temporal
        var audit_item = {
            product_id: product.id,
            qty_deleted: Math.abs(qty_deleted),
            price_unit: price_unit,
            user_id: (this.pos.get_cashier() || this.pos.user).id,
            deletion_reason: reason,
            deletion_datetime: new Date().toISOString(),
        };

        if (this.table) {
            audit_item.table_id = this.table.id;
        }

        this.audit_deleted_items.push(audit_item);
    },

    export_as_JSON: function() {
        var json = _super_order.export_as_JSON.call(this);

        // Incluir items eliminados
        if (this.audit_deleted_items.length > 0) {
            json.audit_deleted_items = this.audit_deleted_items;
        }

        return json;
    },
});
```

### Extensión de Orderline

```javascript
models.Orderline = models.Orderline.extend({
    set_quantity: function(quantity) {
        if (!this.pos.is_audit_enabled()) {
            // Sin auditoría, procede normal
            return _super_orderline.set_quantity.call(this, quantity);
        }

        var old_quantity = this.quantity || 0;
        var is_deletion = false;
        var qty_deleted = 0;

        // Detectar eliminación
        if (quantity === 'remove') {
            is_deletion = true;
            qty_deleted = old_quantity;
        } else {
            var new_quantity = parseFloat(quantity) || 0;
            if (new_quantity < old_quantity && old_quantity > 0) {
                is_deletion = true;
                qty_deleted = old_quantity - new_quantity;
            }
        }

        if (is_deletion && qty_deleted > 0) {
            // Mostrar popup
            this.pos.gui.show_popup('deletion-reason-popup', {
                orderline: this,
                quantity: quantity,
                qty_deleted: qty_deleted,
                callback: function(reason) {
                    if (reason) {
                        // Registrar auditoría
                        self.order.add_deleted_item_audit(
                            self.product,
                            qty_deleted,
                            self.get_unit_price(),
                            reason
                        );

                        // Proceder con eliminación
                        _super_orderline.set_quantity.call(self, quantity);
                    }
                }
            });
        } else {
            return _super_orderline.set_quantity.call(this, quantity);
        }
    },
});
```

### Popup de Justificación

```javascript
var DeletionReasonPopup = PopupWidget.extend({
    template: 'DeletionReasonPopup',

    events: {
        'click .reason-button': 'click_reason',
        'click .confirm': 'click_confirm',
        'click .cancel': 'click_cancel',
    },

    click_reason: function(event) {
        // Agrega razón predeterminada al textarea
        var reason = $(event.currentTarget).data('reason');
        var $textarea = this.$('textarea[name="deletion_reason"]');
        var current_text = $textarea.val().trim();

        if (current_text) {
            $textarea.val(current_text + '\n' + reason);
        } else {
            $textarea.val(reason);
        }
    },

    click_confirm: function() {
        var reason = this.$('textarea[name="deletion_reason"]').val().trim();

        // Validaciones
        if (!reason || reason.length < 5) {
            // Mostrar error
            return;
        }

        // Llamar callback con la razón
        if (this.callback) {
            this.callback(reason);
        }

        this.gui.close_popup();
    },
});

gui.define_popup({name:'deletion-reason-popup', widget: DeletionReasonPopup});
```

### Sincronización con Backend

```javascript
models.PosModel.prototype.push_order = function(order, opts) {
    var pushed = _super_posmodel_push_order.call(this, order, opts);

    if (order.audit_deleted_items && order.audit_deleted_items.length > 0) {
        pushed.then(function(server_ids) {
            if (server_ids && server_ids.length > 0) {
                var order_server_id = server_ids[0].id;

                // Guardar registros de auditoría
                rpc.query({
                    model: 'pos.order',
                    method: 'create_audit_records_from_ui',
                    args: [order_server_id, order.audit_deleted_items],
                });
            }
        });
    }

    return pushed;
};
```

---

## Seguridad y Permisos

### Grupos de Seguridad

**Archivo:** `security/security.xml`

#### 1. `group_pos_audit_delete`

Grupo personalizado que permite eliminar registros de auditoría.

```xml
<record id="group_pos_audit_delete" model="res.groups">
    <field name="name">Auditoría POS: Eliminar Registros</field>
    <field name="category_id" ref="module_category_pos_audit"/>
</record>
```

**Uso:** Asignar este grupo solo a gerentes o supervisores.

### Reglas de Registro (Record Rules)

#### Lectura (Todos los usuarios POS)

```xml
<record id="pos_audit_deleted_rule_read" model="ir.rule">
    <field name="name">POS Audit Deleted: Read Access</field>
    <field name="model_id" ref="model_pos_audit_deleted"/>
    <field name="groups" eval="[(4, ref('point_of_sale.group_pos_user'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="False"/>
    <field name="perm_create" eval="False"/>
    <field name="perm_unlink" eval="False"/>
</record>
```

#### Escritura/Creación (Managers)

```xml
<record id="pos_audit_deleted_rule_create" model="ir.rule">
    <field name="name">POS Audit Deleted: Create Access</field>
    <field name="model_id" ref="model_pos_audit_deleted"/>
    <field name="groups" eval="[(4, ref('point_of_sale.group_pos_manager'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_unlink" eval="False"/>
</record>
```

#### Eliminación (Solo usuarios autorizados)

```xml
<record id="pos_audit_deleted_rule_unlink" model="ir.rule">
    <field name="name">POS Audit Deleted: Delete Access</field>
    <field name="model_id" ref="model_pos_audit_deleted"/>
    <field name="groups" eval="[(4, ref('group_pos_audit_delete'))]"/>
    <field name="perm_unlink" eval="True"/>
</record>
```

### Acceso a Modelos (ir.model.access.csv)

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_pos_audit_deleted_user,pos.audit.deleted user,model_pos_audit_deleted,point_of_sale.group_pos_user,1,0,0,0
access_pos_audit_deleted_manager,pos.audit.deleted manager,model_pos_audit_deleted,point_of_sale.group_pos_manager,1,1,1,0
access_pos_audit_deleted_deleter,pos.audit.deleted deleter,model_pos_audit_deleted,group_pos_audit_delete,1,1,1,1
```

### Doble Capa de Seguridad para Eliminación

1. **Regla de Registro:** Solo usuarios en `group_pos_audit_delete`
2. **Validación en `unlink()`:** Verifica `user.pos_audit_can_delete`

```python
def unlink(self):
    if not self.env.user.pos_audit_can_delete:
        raise UserError(_('No tiene permisos para eliminar registros de auditoría.'))
    return super(PosAuditDeleted, self).unlink()
```

---

## Vistas y Menús

### Estructura de Menús

```
Punto de Ventas (point_of_sale.menu_point_root)
├── Reportes (point_of_sale.menu_point_rep)
│   └── Productos Eliminados [NUEVO]
│       → Acción: pos_audit_deleted_action
│       → Grupos: pos_manager, group_pos_audit_delete
│
└── Configuración (point_of_sale.menu_point_config_product)
    └── Justificaciones de Eliminaciones [NUEVO]
        → Acción: pos_deletion_reason_action
        → Grupos: pos_manager
```

### Vistas Principales

#### 1. Vista de Productos Eliminados (pos.audit.deleted)

**Modos de Vista:** tree, form, pivot, graph

##### Vista de Lista (tree)

- Decoraciones visuales:
  - `decoration-danger`: qty_deleted > 5 (rojo)
  - `decoration-warning`: qty_deleted > 2 (amarillo)
- Campos visibles por defecto:
  - Fecha/Hora
  - Pedido
  - Producto
  - Cantidad
  - Usuario
  - Justificación (resumen)
- Suma automática del subtotal
- Búsqueda predeterminada: "Este Mes"

##### Vista de Formulario (form)

- Botones de acción:
  - "Ver Pedido" (si pos_order_id existe)
  - "Ver Producto"
- Información organizada en grupos:
  - Información del Pedido
  - Información de la Eliminación
  - Producto Eliminado
  - Cantidad y Precio
- Notebook con:
  - Justificación Completa (textarea)
  - Información Técnica (solo admins)

##### Vista Pivot

- Análisis por usuario y fecha
- Medidas: cantidad eliminada, subtotal

##### Vista Gráfico

- Tipo: Barras
- Agrupación: por usuario
- Medida: cantidad eliminada

#### 2. Vista de Justificaciones (pos.deletion.reason)

**Modos de Vista:** tree (editable), form

- Lista editable en línea (editable="bottom")
- Campo handle para reordenar (sequence)
- Widget boolean_toggle para activo/inactivo

#### 3. Vista de Usuarios Extendida (res.users)

Extensión de `base.view_users_form`:

```xml
<xpath expr="//page[@name='access_rights']//group[@name='application_accesses']" position="inside">
    <group string="Auditoría POS" name="pos_audit_group">
        <field name="pos_audit_enabled" widget="boolean_toggle"/>
        <field name="pos_audit_can_delete" widget="boolean_toggle"/>
    </group>
</xpath>
```

**Ubicación:** Configuración / Usuarios / [Usuario] / Pestaña "Permisos / Accesos"

---

## Integración con POS

### Carga de Datos en Inicialización

El módulo se carga cuando el POS inicia:

1. Carga justificaciones predeterminadas activas
2. Carga campos adicionales de usuarios (pos_audit_enabled, pos_audit_can_delete)
3. Los datos quedan disponibles offline

### Compatibilidad con POS Restaurant

Si `pos_restaurant` está instalado:

- Se registra el `table_id` en auditoría
- Funciona con la gestión de mesas
- Compatible con órdenes en múltiples mesas

```javascript
if (this.table) {
    audit_item.table_id = this.table.id;
}
```

### Modo Offline

El módulo funciona completamente offline:

1. Justificaciones se cargan al inicio
2. Eliminaciones se almacenan en el objeto Order
3. Sincronización automática al finalizar la orden

---

## Consideraciones Técnicas

### Rendimiento

- **Carga inicial:** Mínima (solo justificaciones activas)
- **Operación en POS:** Sin impacto (validación en memoria)
- **Sincronización:** Asíncrona, no bloquea el flujo

### Límites y Restricciones

- Justificación mínima: 5 caracteres
- Nombre de justificación: mínimo 3 caracteres
- Sin límite de cantidad de registros de auditoría

### Compatibilidad

- ✅ Odoo 16.0 Community
- ✅ Odoo 16.0 Enterprise
- ✅ POS estándar y POS Restaurant
- ✅ Multi-compañía (con reglas de dominio)
- ✅ Multi-moneda (usa campos monetary)

### Base de Datos

**Recomendación:** Implementar limpieza periódica de registros antiguos.

```python
# Ejemplo de acción programada para limpiar registros > 6 meses
@api.model
def _cron_clean_old_audit_records(self):
    date_limit = fields.Datetime.now() - timedelta(days=180)
    old_records = self.search([('deletion_datetime', '<', date_limit)])
    old_records.unlink()
```

---

## API y Métodos Personalizados

### RPC desde Frontend

#### Obtener configuración de usuario

```javascript
rpc.query({
    model: 'res.users',
    method: 'get_pos_audit_settings',
    args: [user_id],
}).then(function(result) {
    console.log(result.audit_enabled);
    console.log(result.can_delete);
});
```

#### Crear registros de auditoría

```javascript
rpc.query({
    model: 'pos.order',
    method: 'create_audit_records_from_ui',
    args: [order_id, audit_items_array],
}).then(function(created_ids) {
    console.log('Created:', created_ids);
});
```

### XML-RPC / JSON-RPC desde Backend

```python
# Crear registro de auditoría programáticamente
audit_model = self.env['pos.audit.deleted']
vals = {
    'pos_order_name': 'Order 00001',
    'product_id': product.id,
    'qty_deleted': 2.0,
    'user_id': user.id,
    'deletion_reason': 'Razón de prueba',
    'price_unit': 10.00,
}
record_id = audit_model.create_deletion_record(vals)
```

---

## Troubleshooting

### Problema: El popup no aparece

**Diagnóstico:**
1. Verificar que el usuario tenga `pos_audit_enabled = True`
2. Abrir consola del navegador y buscar errores
3. Verificar que el módulo esté correctamente instalado

**Solución:**
```bash
# Reiniciar Odoo con actualización de módulo
./odoo-bin -c odoo.conf -u pos_audit_deleted_items -d database_name
```

### Problema: Los registros no se guardan en el backend

**Diagnóstico:**
1. Verificar logs de Odoo
2. Verificar permisos del usuario
3. Comprobar que la orden se sincronizó correctamente

**Verificación en consola JavaScript:**
```javascript
// Ver si los items están en la orden
var order = pos.get_order();
console.log(order.audit_deleted_items);
```

### Problema: Error al eliminar registros

**Causa:** Usuario no tiene `pos_audit_can_delete = True`

**Solución:**
1. Ir a Configuración / Usuarios
2. Editar usuario
3. Pestaña "Permisos / Accesos"
4. Activar "Puede Eliminar Auditorías POS"
5. Agregar a grupo "Auditoría POS: Eliminar Registros"

### Problema: Justificaciones no aparecen en el popup

**Diagnóstico:**
1. Verificar que existan registros en `pos.deletion.reason` con `active = True`
2. Reiniciar sesión del POS
3. Verificar consola del navegador

**Verificación:**
```javascript
console.log(pos.deletion_reasons);
// Debe mostrar array con justificaciones
```

### Logs Útiles

El módulo genera logs en consola JavaScript:

```
POS Audit: Loaded X deletion reasons
POS Audit: Added deletion record {...}
POS Audit: Saved X deletion records to backend
POS Audit Deleted Items: Module loaded successfully
```

---

## Mantenimiento y Soporte

### Actualización del Módulo

```bash
# Actualizar módulo
./odoo-bin -c odoo.conf -u pos_audit_deleted_items -d database_name

# Si hay cambios en archivos estáticos (JS/XML)
# Limpiar cache del navegador o usar Ctrl+F5
```

### Backup de Datos

Antes de eliminar registros masivamente, hacer backup:

```bash
# Exportar registros de auditoría
# Punto de Ventas / Reportes / Productos Eliminados
# Clic en Acción / Exportar
```

### Contacto

**Desarrollador:** Jbnegoc SPA
**Email:** info@jbnegoc.cl
**Soporte:** https://www.jbnegoc.cl/soporte

---

## Historial de Versiones

### v16.0.1.0.0 (2026-01-15)

- ✅ Versión inicial
- ✅ Auditoría completa de eliminaciones
- ✅ Popup interactivo con justificaciones
- ✅ Integración con POS y POS Restaurant
- ✅ Control granular de permisos por usuario
- ✅ Reportes y análisis

---

**Fin de Documentación Técnica**

© 2026 Jbnegoc SPA - Todos los derechos reservados
