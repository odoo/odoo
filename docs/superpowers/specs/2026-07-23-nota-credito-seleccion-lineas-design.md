# Selección de líneas al crear una Nota de Crédito parcial

- **Fecha:** 2026-07-23
- **Estado:** Aprobado (diseño)
- **Alcance:** En el asistente de Nota de Crédito (`account.move.reversal`, extendido por `l10n_cr_fe_crlibre`), permitir elegir qué líneas de producto de la factura original entran en la nota de crédito, en vez de copiar siempre las 50 líneas y obligar a borrar manualmente las que no aplican.

---

## 1. Contexto

El asistente nativo de Odoo para crear una nota de crédito ("Revertir") siempre copia **todas** las líneas de la factura original a la nota de crédito resultante, con la misma cantidad. Cuando el motivo es corregir solo algunos productos de una factura grande (p. ej. 3 de 50), el usuario debe borrar manualmente, una por una, las líneas que no necesita — no hay selección múltiple en la tabla editable de líneas de factura (confirmado en pruebas manuales: esa tabla no tiene checkboxes, solo un ícono de papelera por fila al pasar el mouse).

Esto ya generó confusión adicional en pruebas manuales: al dejar sin tocar una línea que no necesitaba corrección, esa línea se acredita por completo (en vez de no acreditarse), invirtiendo el resultado esperado (ver casos de prueba de `INV/2026/00005` y `INV/2026/00010`). La regla operativa ya establecida con el usuario es: **la cantidad en una línea de nota de crédito representa cuánto se acredita/quita, no cuánto debe quedar**. Esta mejora no cambia esa regla — solo evita que las líneas que no se van a tocar queden ahí por accidente.

## 2. Diseño

### 2.1 Nuevo campo en el wizard: `l10n_cr_fe_line_ids`

En `l10n_cr_fe_crlibre/wizards/account_move_reversal.py`:

```python
l10n_cr_fe_line_ids = fields.Many2many(
    'account.move.line', string="Líneas a corregir",
    domain="[('move_id', 'in', move_ids), ('display_type', '=', 'product')]")
```

- Dominio limitado a líneas de producto (`display_type = 'product'`, confirmado contra `account.move.line` en este Odoo 19 — no es `False` como en versiones más viejas) de la factura que se está reversando — excluye secciones, notas y líneas de impuesto.
- Vacío por defecto (el usuario marca activamente lo que va a corregir).
- Visible en la vista del wizard **solo cuando** `l10n_cr_fe_motivo` es distinto de `anulacion_total` (mismo patrón `invisible=` que ya usan los campos condicionales existentes del wizard). Para `anulacion_total` el campo se oculta y no se usa — ese motivo sigue generando el espejo completo automático, sin cambios.
- Se muestra en modo lista no editable (checkboxes nativos de selección de Odoo, el mismo patrón que usan los selectores estándar de registros existentes — distinto de la tabla editable de líneas de factura, que no los tiene), con columnas Producto / Cantidad / Precio / Importe, para que el usuario identifique rápido qué marcar en una factura larga. **Riesgo a verificar en la primera tarea de implementación**: confirmar en el navegador que el widget efectivamente renderiza checkboxes para este campo Many2many en modo lista dentro del wizard; si Odoo no los muestra por defecto en este contexto, ajustar el `widget`/atributos de la vista hasta lograrlo antes de continuar con el resto del plan.

### 2.2 Filtrado tras la reversión

**Punto de intercepción: `refund_moves()`, no `reverse_moves()`.** Se investigó el código nativo (`account/wizard/account_move_reversal.py`): el botón "Revertir" llama a `refund_moves()` → `self.reverse_moves(is_modify=False)`, y en ese camino `self.new_move_ids` sí queda apuntando a la nota de crédito recién creada. El botón "Revertir y crear factura" llama a `modify_moves()` → `self.reverse_moves(is_modify=True)`, que además crea una **factura nueva de reemplazo** y reasigna `self.new_move_ids` a esa factura, no a la nota de crédito — mezclar esta lógica ahí filtraría por accidente la factura de reemplazo en vez de la nota de crédito. Por eso el checklist y su filtrado solo se enganchan a `refund_moves()`; `modify_moves()` queda sin tocar (ver sección 3).

Override de `refund_moves()` en el wizard:

1. Si el motivo es distinto de `anulacion_total` y `l10n_cr_fe_line_ids` está vacío: `UserError` antes de crear nada — "Selecciona al menos un producto a corregir" — evita generar una nota de crédito vacía por descuido.
2. Llama a `super().refund_moves()` — sin cambios, crea el espejo completo como hoy (usa el mecanismo nativo `account.move._reverse_moves()`, que internamente usa `move.copy()` y preserva el orden de las líneas).
3. Si el motivo es distinto de `anulacion_total` y `l10n_cr_fe_line_ids` tiene valores: en la nota de crédito recién creada (`self.new_move_ids`), identifica sus líneas de producto que **no** corresponden a una línea seleccionada (comparando por posición, ya que `copy()` preserva el orden 1:1 entre la factura original y su reverso) y las elimina (`unlink()`).

### 2.3 Alcance de la selección

- Solo aplica a líneas de producto. Las secciones/notas de la factura original nunca se copian a través de este mecanismo (no son corregibles por sí mismas).
- No cambia nada del flujo para `anulacion_total`: sigue siendo mirror completo automático, sin checklist.
- No cambia la cantidad con la que aparece cada línea seleccionada en la nota de crédito resultante — llega con la cantidad original de la factura, igual que hoy; el usuario la edita manualmente hacia el valor a acreditar (comportamiento ya aprendido, sin cambios).

## 3. Fuera de alcance

- No se toca la tabla editable de líneas dentro del formulario de la nota de crédito ya creada — sigue sin selección múltiple nativa (limitación de Odoo, no de este módulo).
- No se añade una forma de pre-cargar la cantidad a acreditar (p. ej. en cero) desde el checklist — el usuario sigue editándola manualmente después de marcar las líneas.
- No aplica a reversiones de asientos contables genéricos ni facturas de proveedor — el campo nuevo solo es relevante cuando `l10n_cr_fe_motivo` está visible (factura `out_invoice` con `l10n_cr_fe_clave`, según la lógica ya existente de `l10n_cr_fe_applicable`).
- El botón "Revertir y crear factura" (`modify_moves()`) no se toca — el checklist y su filtrado solo aplican al botón "Revertir" (`refund_moves()`), según lo explicado en 2.2. Si más adelante se necesita el mismo comportamiento ahí, es un cambio aparte.

## 4. Verificación

- Motivo `correccion_monto`, factura con 3 líneas, se marcan 2 en el checklist → la nota de crédito resultante tiene solo esas 2 líneas, con la cantidad original de cada una.
- Motivo `anulacion_total` → el checklist no aparece; la nota de crédito sigue siendo el espejo completo (regresión del comportamiento actual).
- Motivo `correccion_monto` sin marcar ninguna línea → `UserError` claro, no se crea ninguna nota de crédito.
- Motivo `devolucion_mercancia` / `referencia_otro_documento` / `otros` con selección parcial → mismo comportamiento que `correccion_monto` (el checklist aplica a todos los motivos parciales, no solo a corrección de monto).
