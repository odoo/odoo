# Tiquete Electrónico desde una factura de consumidor final

- **Fecha:** 2026-07-27
- **Estado:** Aprobado (diseño)
- **Alcance:** Permitir emitir un Tiquete Electrónico (v4.4) desde `l10n_cr_fe_crlibre` cuando la venta es a un consumidor final que no necesita factura, reutilizando el flujo de generación/envío FE ya existente para `out_invoice`. No cubre corregir un Tiquete con Nota de Crédito ni integración con el módulo POS de Odoo (ver sección 3).

---

## 1. Contexto

El módulo hoy despacha dos tipos de comprobante por `move_type` de Odoo: `out_invoice` → Factura Electrónica (FE, `tipoDocumento=01`), `out_refund` → Nota de Crédito (NC, `tipoDocumento=03`), vía el diccionario `L10N_CR_FE_TIPO_DOCUMENTO` en `account_move.py`. Un Tiquete Electrónico (TE) es, para efectos de Hacienda, un tercer tipo de comprobante (`tipoDocumento=04`) — pero en Odoo sigue siendo un `account.move` con `move_type='out_invoice'` (una venta normal), no un `move_type` distinto. La única diferencia real de negocio es que el comprobante es para alguien que no necesita identificarse fiscalmente (consumidor final).

Se investigó el código real de la API_Hacienda (CRLibre, `D:\API_Hacienda\api\contrib\genXML\genXML.php` y `xmlGenerator.php`) para confirmar el soporte existente antes de diseñar, siguiendo el mismo método que se usó para Nota de Crédito:

- `genXMLTE()` ya existe en la API, expuesta como acción `gen_xml_te` (`module.php:274-275`), con exactamente la misma estructura de parámetros que `genXMLFE()`/`genXMLNC()` (emisor, receptor, detalles, totales, `informacion_referencia`).
- `clave.php` confirma el código de tipoDocumento para el endpoint de clave: `'TE' => '04'`.
- El bloque `<Receptor>` en el XML se controla con un parámetro `omitir_receptor`: si es `'true'`, el bloque completo se omite; si no, se incluye pero el sub-bloque `<Identificacion>` (tipo/número de cédula) solo se agrega si esos campos vienen no vacíos — es decir, la API ya soporta un receptor sin identificar.

También se confirmó que `point_of_sale` está instalado en este ambiente, pero su menú fue ocultado intencionalmente en un trabajo anterior de este mismo proyecto (`feat/config-menus-clientes-preventas-pos`, `.superpowers/sdd/progress.md`) — el negocio no opera con el POS nativo de Odoo, así que el Tiquete se emite desde Facturación igual que la Factura y la Nota de Crédito hoy, no desde POS.

## 2. Diseño

### 2.1 Campo disparador: `l10n_cr_fe_es_tiquete`

Nuevo campo Boolean en `account.move`:

```python
l10n_cr_fe_es_tiquete = fields.Boolean(
    string="Consumidor final (Tiquete Electrónico)",
    help="Si está marcado, este comprobante se emite ante Hacienda como Tiquete "
         "Electrónico (sin identificar al receptor) en vez de Factura Electrónica.")
```

Visible en la pestaña "Factura Electrónica CR" del formulario, solo para `move_type == 'out_invoice'` (mismo patrón `invisible=` que ya usan los campos condicionales de esa pestaña). El usuario lo marca manualmente antes de confirmar la factura — no hay detección automática por cliente, decisión ya tomada durante el diseño.

### 2.2 Generalizar la resolución de tipo de documento

`L10N_CR_FE_TIPO_DOCUMENTO` está indexado por `move_type`, lo cual ya no alcanza porque Tiquete y Factura comparten `move_type='out_invoice'`. Se agrega una constante nueva a nivel de módulo:

```python
L10N_CR_FE_TIPO_DOCUMENTO_TE = {'clave': 'TE', 'consecutivo_codigo': '04', 'gen_xml_action': 'gen_xml_te'}
```

Y un método nuevo en `account.move` que centraliza la decisión, reemplazando los 3 usos directos de `L10N_CR_FE_TIPO_DOCUMENTO[self.move_type]` / `self.move_type in L10N_CR_FE_TIPO_DOCUMENTO`:

```python
def _l10n_cr_fe_get_tipo_documento_info(self):
    self.ensure_one()
    if self.move_type == 'out_invoice' and self.l10n_cr_fe_es_tiquete:
        return L10N_CR_FE_TIPO_DOCUMENTO_TE
    return L10N_CR_FE_TIPO_DOCUMENTO.get(self.move_type)
```

- `_l10n_cr_fe_build_clave_params()`: `tipo_doc = self._l10n_cr_fe_get_tipo_documento_info()` en vez del acceso directo al diccionario.
- `_l10n_cr_fe_generate_and_send()`: la comprobación de entrada (`if self.move_type not in L10N_CR_FE_TIPO_DOCUMENTO: return`) se mantiene igual — un Tiquete sigue siendo `out_invoice`, que ya está en el diccionario, así que el trigger de `action_post()` no cambia. Solo el `gen_xml_action = L10N_CR_FE_TIPO_DOCUMENTO[self.move_type]['gen_xml_action']` pasa a usar `self._l10n_cr_fe_get_tipo_documento_info()['gen_xml_action']`.

El consecutivo (`config._l10n_cr_fe_next_consecutivo('04')`) reutiliza sin cambios el mecanismo ya construido para NC — cada tipo de documento tiene su propio correlativo independiente, y como Tiquete es un tipo nuevo sin historial previo, arranca en 1 sin riesgo de colisión (a diferencia del bug de FE que se corrigió recientemente).

### 2.3 Receptor omitido y sin exigir cédula

En `_l10n_cr_fe_build_genxml_params()`:

- El `UserError` actual que exige `self.partner_id.vat` se salta cuando `self.l10n_cr_fe_es_tiquete` es `True`.
- En vez de los campos `receptor_nombre`/`receptor_tipo_identif`/`receptor_num_identif`, se agrega `'omitir_receptor': 'true'` al diccionario de parámetros — sin importar qué contacto tenga elegido la factura en Odoo, Hacienda no recibe ningún dato del receptor (decisión ya tomada: se omite completo, no solo la cédula).

En `_l10n_cr_fe_generate_and_send()`, la llamada a `client.send_fe(...)` deja de leer `self.partner_id.l10n_cr_fe_identification_type`/`self.partner_id.vat.replace(...)` cuando es Tiquete (evita un `AttributeError` si el partner no tiene `vat` cargado) y manda cadenas vacías para `receptor_tipo`/`receptor_num` en su lugar.

### 2.4 Cliente HTTP: `gen_xml_te`

En `crlibre_client.py`, método nuevo idéntico en forma a los existentes:

```python
def gen_xml_te(self, params):
    resp = self._call('genXML', 'gen_xml_te', params)
    if not isinstance(resp, dict) or not resp.get('xml'):
        raise CrlibreApiError("Respuesta inesperada de 'gen_xml_te': %s" % resp)
    return base64.b64decode(resp['xml']).decode('utf-8')
```

### 2.5 Candado: Nota de Crédito sobre un Tiquete no está soportada todavía

Corregir un Tiquete con NC queda fuera de esta iteración (confirmado). El asistente de "Revertir" hoy no distingue Tiquete de Factura — cualquier `out_invoice` con `l10n_cr_fe_clave` se marca "aplicable" (`l10n_cr_fe_applicable` en el wizard). Para no generar silenciosamente una NC incorrecta (el bloque `InformacionReferencia` está fijo hoy en `tipoDoc: '01'`, que sería inválido si el original fue un Tiquete), se agrega una validación explícita en `_l10n_cr_fe_generate_and_send()`, mismo lugar y mismo patrón que el candado ya existente de "factura original debe estar aceptada":

```python
if self.move_type == 'out_refund':
    original = self.reversed_entry_id
    if original.l10n_cr_fe_es_tiquete:
        raise UserError(_(
            "No se puede generar una nota de crédito sobre un Tiquete Electrónico "
            "todavía — esta corrección no está soportada."))
```

Este `UserError` ya es capturado por el `except (CrlibreApiError, UserError)` existente — la nota de crédito queda creada en Odoo con `l10n_cr_fe_state = 'error'` y mensaje claro en el chatter, sin bloquear el asiento contable, exactamente igual que los demás candados de este flujo.

### 2.6 Vista

En `views/account_move_views.xml`, dentro de la pestaña "Factura Electrónica CR", se agrega `l10n_cr_fe_es_tiquete` con `invisible="move_type != 'out_invoice'"`, posicionado antes de los demás campos de esa pestaña (es la decisión que determina cómo se interpreta el resto).

## 3. Fuera de alcance

- **Nota de Crédito sobre un Tiquete**: confirmado con el usuario, queda para un proyecto aparte. Esta iteración solo agrega el candado defensivo (2.5) para que el intento falle con un mensaje claro en vez de generar un documento inválido.
- **Integración con el módulo POS de Odoo**: el Tiquete se emite desde Facturación (mismo flujo que FE/NC), no desde POS — el negocio no usa el POS nativo (menú oculto intencionalmente en trabajo previo).
- **"Consumidor final por defecto" a nivel de contacto**: no hay campo en `res.partner` para pre-marcar esto; el toggle es manual por factura, cada vez.
- **Límite de monto que fuerce Tiquete vs Factura**: no existe esa regla en el catálogo v4.4 de Hacienda: no se inventa una validación de negocio que Hacienda no exige.
- **Correo de aceptación / Consultar estado FE / Reintentar**: no requieren cambios — ya operan sobre `l10n_cr_fe_clave`/`l10n_cr_fe_state` sin importar el tipo de documento subyacente, igual que se confirmó para NC.

## 4. Verificación

- Marcar una factura nueva como "Consumidor final (Tiquete Electrónico)", con un cliente sin cédula cargada, y confirmarla → no debe pedir cédula, debe generarse con `tipoDocumento=TE` y consecutivo propio empezando en 1.
- Confirmar que el XML generado (o la clave) no contiene bloque `Receptor`.
- Confirmar una factura normal (sin el checkbox marcado) sigue exigiendo cédula y generándose como FE, sin regresión.
- Intentar "Revertir" (crear NC) sobre una factura marcada como Tiquete y ya aceptada → debe fallar con el mensaje del candado 2.5, quedando en estado Error sin bloquear el asiento contable.
- Confirmar que el consecutivo de Tiquete es independiente del de Factura y Nota de Crédito (tres secuencias separadas, verificable en `ir.sequence`).
