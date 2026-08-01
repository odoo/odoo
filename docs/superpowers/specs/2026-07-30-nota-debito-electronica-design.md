# Nota de Débito Electrónica (ND) desde una Factura Electrónica

- **Fecha:** 2026-07-30
- **Estado:** Aprobado (diseño)
- **Alcance:** Permitir crear y enviar a Hacienda una Nota de Débito Electrónica (v4.4, tipoDocumento `ND`) desde una Factura Electrónica de venta ya aceptada, para agregar un cargo o aumentar el monto de la factura original.

---

## 1. Contexto

Una Nota de Débito es el opuesto de la Nota de Crédito ya construida en `l10n_cr_fe_crlibre`: se usa cuando hay que **aumentar** el monto de una factura ya emitida (se facturó de menos, hay que cobrar un cargo adicional — p. ej. un cargo financiero por mora — o corregir un error a favor de la empresa). Referencia siempre el documento original, igual que la Nota de Crédito.

Se investigó el código real de la API_Hacienda (CRLibre, checkout local en `D:\API_Hacienda`) antes de diseñar, con el mismo método usado para NC/TE/MR:

- `clave.php` confirma el catálogo de `tipoDocumento`: `FE`→`01`, **`ND`→`02`**, `NC`→`03`, `TE`→`04`, `CCE`→`05`, `CPCE`→`06`, `RCE`→`07`. Cada uno tiene su propio consecutivo independiente, mismo mecanismo ya construido.
- `genXML/module.php` expone `gen_xml_nd` (acción `genXMLND`) con una lista de parámetros **estructuralmente idéntica** a `gen_xml_nc` — mismos campos de emisor/receptor/totales/detalles, y `informacion_referencia` también **obligatorio** (a diferencia de FE, donde es opcional).
- `send/module.php` solo expone tres acciones de envío: la genérica `json`/`send` (usada hoy por `client.send_fe()` para FE/NC/TE), `sendMensaje` (dedicada a Mensaje Receptor) y `sendTE` (dedicada a Tiquete). **No existe un `sendND` dedicado** — la Nota de Débito se envía con la misma acción genérica que ya usa `send_fe()`, sin necesidad de un método nuevo en el cliente para el envío (solo para la generación del XML).

Del lado de Odoo, el módulo core `account_debit_note` (no instalado hasta ahora en este proyecto) ya trae el wizard nativo "Add Debit Note". A diferencia de la Nota de Crédito — que en Odoo es su propio `move_type='out_refund'` — la Nota de Débito que genera ese wizard es un `account.move` normal con `move_type` igual al de la factura original (`out_invoice` en el caso que nos interesa) y un campo nativo `debit_origin_id` apuntando al documento original. Esto es la diferencia estructural clave frente al diseño de NC: no se puede distinguir una ND de una Factura normal por `move_type`, hay que usar `debit_origin_id`.

## 2. Diseño

### 2.1 Nuevo tipo de documento, resuelto por `debit_origin_id`, no por `move_type`

```python
L10N_CR_FE_TIPO_DOCUMENTO_ND = {'clave': 'ND', 'consecutivo_codigo': '02', 'gen_xml_action': 'gen_xml_nd'}
```

`_l10n_cr_fe_get_tipo_documento_info()` (ya generalizado durante Tiquete Electrónico y Mensaje Receptor) gana una rama nueva, evaluada **antes** que el flag de Tiquete (`l10n_cr_fe_es_tiquete`) porque una ND siempre nace del wizard dedicado, nunca del flujo de Tiquete:

```python
if self.move_type == 'out_invoice' and self.debit_origin_id:
    return L10N_CR_FE_TIPO_DOCUMENTO_ND
if self.move_type == 'out_invoice' and self.l10n_cr_fe_es_tiquete:
    return L10N_CR_FE_TIPO_DOCUMENTO_TE
...
```

El consecutivo (`02`) es independiente de los de FE/NC/TE/MR — mismo mecanismo de secuencias por tipo de documento ya construido, sin cambios en `fe_config.py`.

### 2.2 Cliente HTTP: `gen_xml_nd`

Nuevo método en `crlibre_client.py`, mismo patrón que `gen_xml_nc` (mismo shape de parámetros verificado contra la API real):

```python
def gen_xml_nd(self, params):
    resp = self._call('genXML', 'gen_xml_nd', params)
    if not isinstance(resp, dict) or not resp.get('xml'):
        raise CrlibreApiError("Respuesta inesperada de 'gen_xml_nd': %s" % resp)
    return base64.b64decode(resp['xml']).decode('utf-8')
```

No se necesita ningún método nuevo para el envío — reutiliza `client.send_fe()` sin cambios (confirmado que ND usa la acción genérica `send`/`json`, igual que FE/NC).

### 2.3 Campos nuevos en `account.move`

Se reutilizan sin cambios los campos genéricos ya construidos para NC (no son específicos de NC pese a algunos nombres): `l10n_cr_fe_codigo_referencia` y `l10n_cr_fe_razon`. Se agrega un campo nuevo y separado para el motivo de negocio, porque las opciones de una ND no son las mismas que las de una NC (p. ej. "Devolución de mercancía" no aplica a un aumento de monto):

```python
L10N_CR_FE_MOTIVO_ND = [
    ('correccion_monto', "Corrección de monto, precio, cantidad o descuento"),
    ('cargo_financiero', "Cargo financiero (intereses, cargos por mora)"),
    ('referencia_otro_documento', "Referencia a otro documento"),
    ('otros', "Otros"),
]

L10N_CR_FE_MOTIVO_CODIGO_MAP_ND = {
    'correccion_monto': '02',
    'cargo_financiero': '10',   # "10 - Nota de débito financiera" del catálogo Hacienda, pensado para este caso
    'referencia_otro_documento': '04',
    'otros': '99',
}
```

```python
l10n_cr_fe_motivo_nd = fields.Selection(
    L10N_CR_FE_MOTIVO_ND, string="Motivo de la nota de débito", copy=False)
```

`l10n_cr_fe_codigo_referencia` y `l10n_cr_fe_razon` (ya existentes) se reutilizan tal cual — mismo criterio que ya siguen para NC: uno es el código oficial resultante (editable solo por `group_fe_admin`), el otro es la razón en texto libre que se manda a Hacienda.

### 2.4 `InformacionReferencia` en `_l10n_cr_fe_build_genxml_params`

El método ya arma `informacion_referencia` para NC usando `self.reversed_entry_id`. Gana una rama equivalente para ND usando `self.debit_origin_id`:

```python
if self.move_type == 'out_refund':
    original = self.reversed_entry_id
    ...
elif self.debit_origin_id:
    original = self.debit_origin_id
    params['informacion_referencia'] = json.dumps([{
        'tipoDoc': '01',  # Factura electrónica (catálogo TipoDocReferenciaType)
        'numero': original.l10n_cr_fe_clave,
        'fechaEmision': original.l10n_cr_fe_fecha_emision,
        'codigo': self.l10n_cr_fe_codigo_referencia,
        'razon': self.l10n_cr_fe_razon or '',
    }])
```

### 2.5 Validación en `_l10n_cr_fe_generate_and_send`

Mismo patrón que ya existe para `out_refund`: antes de generar/enviar, si el tipo de documento resuelto es ND, se valida que la factura original (`debit_origin_id`) exista, esté `l10n_cr_fe_state == 'aceptado'`, y no sea un Tiquete Electrónico (misma restricción que ya aplica a NC — corregir un Tiquete no está soportado todavía). Si algo de esto falla, `UserError` claro, sin enviar nada. Cualquier error de la API dejará `l10n_cr_fe_state = 'error'` con detalle en el chatter — mismo comportamiento ya establecido para FE/NC/TE/MR, nunca bloquea la confirmación contable del asiento.

### 2.6 Dependencia nueva: módulo `account_debit_note`

Se agrega `'account_debit_note'` a los `depends` del manifest. Este módulo core de Odoo ya trae:
- El wizard `account.debit.note` con el botón "Debit Note" en el formulario de factura (visible para cualquier factura posteada, no solo `out_invoice` — no se oculta para otros casos, simplemente esos otros casos no disparan envío a Hacienda porque `_l10n_cr_fe_get_tipo_documento_info()` solo reconoce ND cuando el origen es `out_invoice`).
- El campo `debit_origin_id` en `account.move`, ya visible en el formulario nativo.
- Un botón estadístico "Debit Notes" mostrando las ND generadas desde una factura.

No se modifica nada de este módulo — solo se extiende su wizard.

### 2.7 Wizard: extender `account.debit.note`

Mismo patrón que la extensión ya construida de `account.move.reversal` para NC:

```python
class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    l10n_cr_fe_applicable = fields.Boolean(compute='_compute_l10n_cr_fe_applicable')
    l10n_cr_fe_is_admin = fields.Boolean(compute='_compute_l10n_cr_fe_is_admin')
    l10n_cr_fe_motivo_nd = fields.Selection(L10N_CR_FE_MOTIVO_ND, string="Motivo de la nota de débito")
    l10n_cr_fe_codigo_referencia = fields.Selection(
        L10N_CR_FE_CODIGO_REFERENCIA, string="Código de referencia Hacienda",
        compute='_compute_l10n_cr_fe_codigo_referencia', store=True, readonly=False)

    @api.depends('move_ids')
    def _compute_l10n_cr_fe_applicable(self):
        for wizard in self:
            wizard.l10n_cr_fe_applicable = bool(
                wizard.move_ids and len(wizard.move_ids) == 1
                and wizard.move_ids.move_type == 'out_invoice'
                and wizard.move_ids.l10n_cr_fe_clave)

    def _compute_l10n_cr_fe_is_admin(self):
        is_admin = self.env.user.has_group('l10n_cr_fe_crlibre.group_fe_admin')
        for wizard in self:
            wizard.l10n_cr_fe_is_admin = is_admin

    @api.depends('l10n_cr_fe_motivo_nd')
    def _compute_l10n_cr_fe_codigo_referencia(self):
        for wizard in self:
            wizard.l10n_cr_fe_codigo_referencia = L10N_CR_FE_MOTIVO_CODIGO_MAP_ND.get(wizard.l10n_cr_fe_motivo_nd)

    def _prepare_default_values(self, move):
        return {
            **super()._prepare_default_values(move),
            'l10n_cr_fe_motivo_nd': self.l10n_cr_fe_motivo_nd,
            'l10n_cr_fe_codigo_referencia': self.l10n_cr_fe_codigo_referencia,
            'l10n_cr_fe_razon': self.reason,
        }
```

`l10n_cr_fe_motivo_nd` es obligatorio en la vista cuando `l10n_cr_fe_applicable` es verdadero — mismo criterio que NC.

**Copiar líneas:** se deja el default nativo del wizard (`copy_lines=False`) sin tocar — la ND nace en blanco para que el usuario agregue el cargo nuevo. El checkbox "Copiar líneas" sigue disponible tal cual lo trae Odoo, por si se necesita partir de las líneas originales.

**Fuera de alcance de este wizard:** no se restringe el botón nativo "Debit Note" a que solo aparezca sobre facturas `out_invoice` aceptadas — se deja visible tal cual lo trae `account_debit_note` (cualquier factura posteada, incluyendo Notas de Crédito `out_refund`: el wizard nativo reescribe ese origen a un `account.move` con `move_type='out_invoice'` antes de crearlo, ver `_prepare_default_values` en `addons/account_debit_note/wizard/account_debit_note.py`). Si el usuario lo usa sobre un origen no soportado (factura de proveedor, nota de crédito), `_l10n_cr_fe_generate_and_send()` rechaza el envío en su bloque de validación (mismo lugar que ya valida `aceptado`/Tiquete) en cuanto detecta que `debit_origin_id.move_type != 'out_invoice'`, con un `UserError` claro — no se envía nada a Hacienda con datos de referencia incorrectos.

**Corrección posterior:** este párrafo afirmaba originalmente que no hacía falta restringir el botón porque `_l10n_cr_fe_get_tipo_documento_info()` "solo reconoce ND cuando el origen es `out_invoice`" — esa afirmación era incorrecta. El wizard nativo de `account_debit_note` reescribe un origen `out_refund` (Nota de Crédito) a `move_type='out_invoice'` antes de crear la ND, así que el método de dispatch la reconocía igual que una ND legítima desde Factura, y el envío se armaba con `'tipoDoc': '01'` (Factura Electrónica) codificado, aunque el origen real fuera una Nota de Crédito (código real `03`) — una revisión posterior encontró que esto se enviaría silenciosamente a Hacienda con datos de referencia falsos. Se agregó una validación explícita en `_l10n_cr_fe_generate_and_send()` que revisa `debit_origin_id.move_type` y bloquea con `UserError` antes de generar o enviar cualquier XML.

### 2.8 Vistas

- Nuevo archivo `views/account_debit_note_views.xml`, extendiendo `view_account_debit_note` (vista nativa del wizard) para insertar los campos nuevos antes de `reason` — mismo patrón que `account_move_reversal_views.xml`.
- `account_move_views.xml`: la pestaña "Factura Electrónica CR" ya muestra motivo/código de referencia/razón cuando `move_type == 'out_refund'`. Se amplía la condición de visibilidad de `l10n_cr_fe_codigo_referencia`/`l10n_cr_fe_razon` a `move_type == 'out_refund' or debit_origin_id`, y se agrega `l10n_cr_fe_motivo_nd` (visible solo si `debit_origin_id`).
- Botones "Consultar estado FE"/"Reintentar envío FE" y el statusbar de `l10n_cr_fe_state`: no necesitan cambios — ya son visibles para `move_type in ('out_invoice', 'out_refund')`, y una ND es `out_invoice`, así que ya quedan cubiertos.

## 3. Fuera de alcance (documentado para retomar en el futuro)

- **Cancelar una Nota de Crédito con una Nota de Débito**: `account_debit_note` lo soporta nativamente (permite generar una ND desde una NC), pero esta iteración lo deja fuera — se restringe a solo facturas de venta (`out_invoice`) aceptadas como origen.
- **Notas de Débito sobre facturas de proveedor** (`in_invoice`): sería un flujo inverso — recibir una ND que un proveedor nos envía — análogo a Mensaje Receptor pero para otro tipo de documento. No es lo que se pidió (crear una ND propia desde una factura de venta) y queda fuera.
- **FEC (Factura Electrónica de Compra) y FEE (Factura Electrónica de Exportación)**: mencionadas en la investigación de la API (`genXMLFec`, `genXMLFee` ya existen del lado de CRLibre) pero no son parte de este diseño — candidatos a proyectos futuros independientes.

## 4. Verificación

- Crear una Nota de Débito desde una Factura de venta aceptada, con motivo "Cargo financiero", agregando una línea de cargo nueva → se envía con `tipoDocumento=ND` (código `02`), consecutivo propio empezando en 1, `InformacionReferencia` apuntando a la clave/fecha de la factura original, y el `out_invoice` resultante queda confirmado con la línea agregada.
- Intentar crear/enviar una ND desde una factura que todavía no está `aceptado` por Hacienda → bloqueado con `UserError` claro.
- Intentar crear/enviar una ND desde un Tiquete Electrónico → bloqueado, mismo criterio que NC.
- Confirmar que "Consultar estado FE" y "Reintentar" funcionan igual sobre estos registros.
- Confirmar que los consecutivos de ND (`02`) son independientes de los de FE/NC/TE/MR.
- Confirmar en sandbox real que Hacienda acepta el documento (verificación manual, fuera de los tests automatizados, igual que se hizo con NC/TE).
