# Nota de Crédito Electrónica (FE) desde una factura

- **Fecha:** 2026-07-22
- **Estado:** Aprobado (diseño)
- **Alcance:** Permitir crear una Nota de Crédito Electrónica en Odoo a partir de una Factura Electrónica (FE) ya aceptada por Hacienda, para corregir devoluciones, productos dañados, descuentos o errores en el monto facturado. Cubre solo `l10n_cr_fe_crlibre` (no toca Tiquete Electrónico, que queda fuera de alcance — ver sección 6).

---

## 1. Contexto

El módulo `l10n_cr_fe_crlibre` hoy solo genera y envía Factura Electrónica (`out_invoice`) a Hacienda vía la API_Hacienda (CRLibre). Las notas de crédito (`out_refund`) se pueden crear y confirmar en Odoo normalmente, pero nunca se convierten en un comprobante electrónico — Hacienda nunca se entera de que existen. Esto es un hueco real: si hay que corregir una factura ya aceptada (devolución, error de monto, descuento posterior), no hay forma de hacerlo de manera fiscalmente válida desde el sistema.

Investigado contra el XSD real de Hacienda (`NotaCreditoElectronica_V4.4.xsd`) y la API_Hacienda (`genXML.php`, función `genXMLNC`, acción `gen_xml_nc`): el flujo de una NC es estructuralmente casi idéntico al de una FE (mismo detalle de líneas, mismo resumen de totales, misma firma/envío/consulta), con dos diferencias:

1. `tipoDocumento` es `NC` en vez de `FE` (código `03` en la clave, según `clave.php`).
2. Lleva un bloque adicional `InformacionReferencia` que apunta de vuelta al documento que corrige (clave, fecha de emisión, código de motivo, razón).

También se confirmó (vía `xs:enumeration` real del XSD, no solo el comentario) el catálogo completo de "Código de referencia" v4.4: `01` Anula documento de referencia, `02` Corrige texto/monto de documento de referencia, `04` Referencia a otro documento, `05` Sustituye comprobante provisional, `06` Devolución de mercancía, `07` Sustituye comprobante electrónico, `08` Factura Endosada, `09` Nota de crédito financiera, `10` Nota de débito financiera, `11` Proveedor No Domiciliado, `12` Crédito por exoneración posterior a facturación, `99` Otros.

Odoo ya tiene un asistente nativo para crear notas de crédito desde una factura (`account.move.reversal`, botón "Añadir nota de crédito"). Varias localizaciones oficiales (`l10n_sa`, `l10n_es_edi_facturae`, `l10n_hu_edi`, etc.) lo extienden con su propio campo de motivo — es el patrón estándar y el que sigue este diseño, en vez de construir un asistente nuevo desde cero.

## 2. Diseño

### 2.1 Generalizar el flujo existente por `move_type`

Los siguientes puntos de `account_move.py`, hoy exclusivos de `out_invoice`, se generalizan a `out_invoice` y `out_refund`:

- `action_post()`: dispara `_l10n_cr_fe_generate_and_send()` para ambos tipos.
- `_l10n_cr_fe_generate_and_send()`: ya no retorna temprano si `move_type != 'out_invoice'`.
- `_l10n_cr_fe_build_clave_params()`: el `tipoDocumento` se deriva del `move_type` (`out_invoice` → `'FE'`, `out_refund` → `'NC'`) en vez de estar fijo en `'FE'`.
- Vistas (`account_move_views.xml`): los `invisible="move_type != 'out_invoice'"` pasan a `invisible="move_type not in ('out_invoice', 'out_refund')"` — aplica a la pestaña "Factura Electrónica CR", el statusbar y los botones "Consultar estado FE" / "Reintentar envío FE".

`_l10n_cr_fe_build_detalles()` y `_l10n_cr_fe_build_resumen_totals()` se reutilizan sin cambios — operan sobre `invoice_line_ids`, que ya están correctamente pobladas en una nota de crédito por el propio mecanismo de reversión de Odoo.

### 2.2 Nuevo método del cliente HTTP: `gen_xml_nc`

En `crlibre_client.py`, un método nuevo paralelo a `gen_xml_fe`:

```python
def gen_xml_nc(self, params):
    resp = self._call('genXML', 'gen_xml_nc', params)
    if not isinstance(resp, dict) or not resp.get('xml'):
        raise CrlibreApiError("Respuesta inesperada de 'gen_xml_nc': %s" % resp)
    return base64.b64decode(resp['xml']).decode('utf-8')
```

`_l10n_cr_fe_generate_and_send()` elige entre `client.gen_xml_fe` y `client.gen_xml_nc` según el `move_type`.

### 2.3 Campo nuevo: fecha de emisión persistida

Hoy `_l10n_cr_fe_build_genxml_params()` calcula `fecha_emision` al vuelo y la descarta. Para que una nota de crédito pueda referenciar la fecha de emisión exacta de la factura original, se agrega:

- `l10n_cr_fe_fecha_emision` (Char, readonly) en `account.move` — se guarda en `_l10n_cr_fe_generate_and_send()` junto con la clave y el consecutivo, para **cualquier** comprobante (factura o nota de crédito), no solo para las que luego se corrigen.

### 2.4 Motivo y código de referencia

**Mapeo de negocio → código oficial** (constante a nivel de módulo, análoga a `L10N_CR_FE_TARIFA_IVA_CODES`):

| Motivo (`l10n_cr_fe_motivo`) | Código Hacienda (`l10n_cr_fe_codigo_referencia`) |
|---|---|
| `anulacion_total` — Anulación total | `01` |
| `correccion_monto` — Corrección de monto, precio, cantidad o descuento | `02` |
| `devolucion_mercancia` — Devolución de mercancía | `06` |
| `referencia_otro_documento` — Referencia a otro documento | `04` |
| `otros` — Otros | `99` |

**En el asistente `account.move.reversal`** (`_inherit`, archivo nuevo `wizards/account_move_reversal.py` en `l10n_cr_fe_crlibre`):

- `l10n_cr_fe_motivo` (Selection, los 5 valores de arriba): visible para todos los usuarios.
- `l10n_cr_fe_codigo_referencia` (Selection, catálogo completo de 12 códigos oficiales): se computa desde `l10n_cr_fe_motivo` vía la tabla; **de solo lectura salvo para el grupo `l10n_cr_fe_crlibre.group_fe_admin`**, que puede sobreescribirlo con cualquiera de los 12 códigos oficiales (cubre casos raros: factura endosada, proveedor no domiciliado, etc., que no tienen un motivo de negocio "amigable" propio).
- `_prepare_default_reversal()` extendido para copiar ambos campos a los valores por defecto de la nueva nota de crédito (mismo patrón que `l10n_sa`).
- Estos dos campos solo son relevantes/visibles en el wizard cuando se está reversando una factura `out_invoice` con `l10n_cr_fe_clave` (es decir, una Factura Electrónica ya procesada); si se usa el mismo asistente para reversar un asiento contable genérico, una factura de proveedor, o una factura de una empresa sin configuración de FE, los campos quedan ocultos y no se exige nada — el resto de esta lógica no aplica a esos casos.

**En `account.move`**: `l10n_cr_fe_motivo`, `l10n_cr_fe_codigo_referencia` (mismas selections) y `l10n_cr_fe_razon` (Char — reusa el texto del campo nativo `reason` del wizard, ya que ese texto hoy solo termina embebido dentro de `ref` como "Reversal of: X, reason"; se guarda aparte para mandarlo limpio como `<Razon>`).

### 2.5 Bloque `InformacionReferencia`

En `_l10n_cr_fe_build_genxml_params()`, solo cuando `move_type == 'out_refund'`:

```python
original = self.reversed_entry_id
informacion_referencia = [{
    'tipoDoc': '01',  # Factura electrónica (catálogo TipoDocReferenciaType)
    'numero': original.l10n_cr_fe_clave,
    'fechaEmision': original.l10n_cr_fe_fecha_emision,
    'codigo': self.l10n_cr_fe_codigo_referencia,
    'razon': self.l10n_cr_fe_razon or '',
}]
```

Odoo ya deja disponible `reversed_entry_id` (Many2one nativo, poblado automáticamente por `_reverse_moves()`) para llegar a la factura original — no hace falta ningún campo de enlace propio.

### 2.6 Corrección: consecutivo independiente por tipo de documento

Hallazgo durante el diseño: `_l10n_cr_fe_next_consecutivo()` usa hoy **una sola secuencia por empresa** (`l10n_cr_fe.consecutivo.fe.<company_id>`), compartida entre todos los tipos de documento. Hacienda exige que cada tipo de documento (Factura=`01`, Nota de Crédito=`03`, etc.) tenga su **propio correlativo independiente**, empezando en 1.

**Fix**: el código de secuencia pasa a incluir el tipo de documento:

```python
def _l10n_cr_fe_next_consecutivo(self, tipo_documento_codigo):
    code = 'l10n_cr_fe.consecutivo.%s.%s' % (tipo_documento_codigo, self.company_id.id)
    ...
```

`_l10n_cr_fe_build_clave_params()` pasa el código correspondiente (`'01'` para FE, `'03'` para NC) al llamar este método. Esto es una corrección de comportamiento para el módulo existente, necesaria antes de que exista la primera nota de crédito real (si no, su numeración se mezclaría con la de facturas).

### 2.7 Validación: factura original debe estar Aceptada

Antes de intentar enviar la NC a Hacienda (dentro de `_l10n_cr_fe_generate_and_send()`, no en el wizard — para no bloquear el asiento contable de Odoo):

```python
if self.move_type == 'out_refund':
    original = self.reversed_entry_id
    if not original or original.l10n_cr_fe_state != 'aceptado':
        raise UserError(_(
            "No se puede generar la nota de crédito: la factura original aún "
            "no ha sido aceptada por Hacienda."))
```

Este `UserError` ya es capturado por el `except (CrlibreApiError, UserError)` existente en `_l10n_cr_fe_generate_and_send()` — la nota de crédito queda creada/confirmada en Odoo con `l10n_cr_fe_state = 'error'` y un mensaje claro en el chatter, exactamente igual que hoy pasa si falta CABYS o certificado.

### 2.8 Correo de aceptación y reintento

`_l10n_cr_fe_send_acceptance_email()`, `action_l10n_cr_fe_consultar_estado()` y `action_l10n_cr_fe_reintentar()` no necesitan cambios de lógica — ya operan sobre `l10n_cr_fe_clave`/`l10n_cr_fe_state` sin importar el `move_type`. Solo las vistas (sección 2.1) necesitan dejar de ocultarlos para `out_refund`.

## 3. Fuera de alcance

- **Tiquete Electrónico (TE)**: se confirmó explícitamente con el usuario que queda para un proyecto separado más adelante (emitir TE para consumidor final sin factura). Esta nota de crédito solo referencia Facturas (FE).
- Notas de crédito parciales con UI dedicada: se resuelve con el flujo estándar de Odoo (el asistente nativo crea el reverso completo; el usuario ajusta las líneas del borrador antes de confirmar, igual que ya hace para cualquier nota de crédito hoy).
- Nota de Débito (ND) — mismo patrón que NC pero no fue pedido; se podría añadir después reusando la misma generalización de `tipoDocumento`.
- Migración retroactiva de facturas ya aceptadas antes de este cambio que no tengan `l10n_cr_fe_fecha_emision` guardada — quedarán sin esa fecha; si alguna necesita una NC, habrá que completarla manualmente (caso raro, dato no sensible).

## 4. Verificación

- Crear una factura, confirmarla, esperar aceptación de Hacienda (sandbox).
- Desde esa factura, usar "Añadir nota de crédito", elegir un motivo, confirmar.
- Confirmar que el envío a Hacienda se dispara solo, con `tipoDocumento=NC` y el bloque `InformacionReferencia` apuntando a la factura original.
- Confirmar que el consecutivo de la nota de crédito empieza en 1, independiente del de facturas.
- Confirmar que "Consultar estado FE" y "Reintentar" funcionan igual sobre la nota de crédito.
- Confirmar que se manda el correo de aceptación al cliente cuando Hacienda acepta la NC.
- Intentar crear una NC contra una factura no aceptada → debe quedar en estado `Error` con mensaje claro, sin bloquear la confirmación contable en Odoo.
