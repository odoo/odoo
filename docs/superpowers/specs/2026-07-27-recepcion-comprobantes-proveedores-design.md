# Recepción y aceptación de comprobantes electrónicos de proveedores

- **Fecha:** 2026-07-27
- **Estado:** Aprobado (diseño)
- **Alcance:** Permitir subir manualmente el XML de una factura electrónica recibida de un proveedor, revisarla, y responder a Hacienda con el Mensaje Receptor correspondiente (aceptación total, aceptación parcial o rechazo) — creando/actualizando la factura de proveedor en Odoo como parte del mismo flujo.

---

## 1. Contexto

Cuando un proveedor emite una Factura Electrónica (FE) a esta empresa, Hacienda espera que el receptor responda con un documento propio: el **Mensaje Receptor**, indicando si acepta el comprobante por completo, lo acepta parcialmente (por diferencias en productos, cantidades, precios o montos) o lo rechaza. No es un simple clic de "aprobar" — es un comprobante electrónico más, con su propia clave, consecutivo, firma digital y envío a Hacienda, igual que Factura, Nota de Crédito y Tiquete Electrónico ya construidos en `l10n_cr_fe_crlibre`.

Hoy este módulo es 100% del lado emisor — nunca toca `move_type='in_invoice'` (facturas de proveedor). Este es el primer trabajo del lado receptor.

Se investigó el código real de la API_Hacienda (CRLibre) antes de diseñar, siguiendo el mismo método usado para NC y TE:

- `genXMLMr()` ya existe en la API, expuesta como acción `gen_xml_mr` (`module.php:34`), con una estructura de parámetros propia (no es igual a `genXMLFE`/`genXMLNC`/`genXMLTE`): no tiene líneas de detalle, es un mensaje agregado — clave del documento original, cédula del emisor, fecha de emisión del documento original, el mensaje (1/2/3), un detalle de mensaje opcional, monto total de impuesto, código de actividad, monto total de factura, cédula del receptor (nosotros) y el consecutivo propio del mensaje.
- `clave.php` confirma que cada decisión es un **tipo de documento distinto**, cada uno con su propio código de consecutivo: `CCE` (Confirmación de Comprobante Electrónico, código `05`) = aceptación total, `CPCE` (Confirmación Parcial, código `06`) = aceptación parcial, `RCE` (Rechazo de Comprobante Electrónico, código `07`) = rechazo.
- El endpoint de consulta (`consultar.php`) y el de envío (`send.php`) **solo permiten consultar/enviar por una clave que ya conoces** — no existe una forma de "listar" comprobantes recibidos. Por reglamento, el proveedor debe mandar el XML por correo; no hay otra vía de descubrimiento automático desde la API de Hacienda.
- `send()` (el endpoint que ya usamos vía `client.send_fe()`) es genérico — no distingue tipo de documento. Se reutiliza sin cambios para enviar el Mensaje Receptor.

## 2. Diseño

### 2.1 Nuevos campos en `account.move` (relevantes solo para `move_type == 'in_invoice'`)

```python
l10n_cr_fe_mr_decision = fields.Selection(
    selection=[
        ('aceptado', "Aceptado"),
        ('aceptado_parcial', "Aceptado parcialmente"),
        ('rechazado', "Rechazado"),
    ],
    string="Decisión sobre la factura del proveedor", copy=False)
l10n_cr_fe_mr_motivo = fields.Char(string="Motivo (Mensaje Receptor)", copy=False)
l10n_cr_fe_proveedor_clave = fields.Char(string="Clave de la factura del proveedor", readonly=True, copy=False)
l10n_cr_fe_proveedor_fecha_emision = fields.Char(string="Fecha de emisión (proveedor)", readonly=True, copy=False)
```

Los campos ya existentes (`l10n_cr_fe_clave`, `l10n_cr_fe_consecutivo`, `l10n_cr_fe_state`, `l10n_cr_fe_xml`, `l10n_cr_fe_xml_firmado`, `l10n_cr_fe_respuesta_xml`) se **reutilizan sin cambios de esquema** — para un `in_invoice`, representan el Mensaje Receptor que **nosotros** enviamos, no la factura del proveedor (cuya clave/fecha originales viven en los dos campos nuevos de arriba). Mismo patrón que ya usa Nota de Crédito: su propia clave vive en esos campos comunes; la clave del documento que referencia vive aparte.

`l10n_cr_fe_mr_motivo` es obligatorio cuando `l10n_cr_fe_mr_decision` es `aceptado_parcial` o `rechazado` — mismo criterio para ambos, por consistencia.

### 2.2 Tipo de documento resuelto por decisión, no por un flag fijo

Constante nueva a nivel de módulo:

```python
L10N_CR_FE_TIPO_DOCUMENTO_MR = {
    'aceptado': {'clave': 'CCE', 'consecutivo_codigo': '05', 'gen_xml_action': 'gen_xml_mr'},
    'aceptado_parcial': {'clave': 'CPCE', 'consecutivo_codigo': '06', 'gen_xml_action': 'gen_xml_mr'},
    'rechazado': {'clave': 'RCE', 'consecutivo_codigo': '07', 'gen_xml_action': 'gen_xml_mr'},
}
```

`_l10n_cr_fe_get_tipo_documento_info()` (ya existente, construido durante Tiquete Electrónico) se extiende: cuando `move_type == 'in_invoice'`, resuelve por `l10n_cr_fe_mr_decision` contra este diccionario, en vez de por un booleano. Las tres decisiones comparten el mismo `gen_xml_action` (`gen_xml_mr`) — la diferencia entre ellas la lleva el parámetro `mensaje` (1/2/3) dentro del XML, no el método del cliente.

El consecutivo de cada una de las tres (`05`/`06`/`07`) es independiente entre sí y de los de FE/NC/TE — mismo mecanismo de secuencias por tipo de documento ya construido, sin cambios.

### 2.3 Cliente HTTP: `gen_xml_mr`

Nuevo método en `crlibre_client.py`, con la misma estructura de manejo de error que los existentes, pero pasando los parámetros propios del Mensaje Receptor (no el mismo shape que `gen_xml_fe`/`nc`/`te`):

```python
def gen_xml_mr(self, params):
    resp = self._call('genXML', 'gen_xml_mr', params)
    if not isinstance(resp, dict) or not resp.get('xml'):
        raise CrlibreApiError("Respuesta inesperada de 'gen_xml_mr': %s" % resp)
    return base64.b64decode(resp['xml']).decode('utf-8')
```

### 2.3-bis Corrección verificada durante la escritura del plan: el envío usa una acción distinta

Al preparar el plan de implementación se investigó `send.php`/`module.php` con el mismo rigor usado para `gen_xml_mr` — y se encontró que el envío del Mensaje Receptor **no reutiliza la acción genérica `send`/`json`** que usa `client.send_fe()` (la que sí sirve, sin cambios, para FE/NC/TE). Existe una acción dedicada `sendMensaje` (`send.php:53`, función `sendMensaje()`), con un parámetro adicional **obligatorio** que la acción genérica no tiene: `consecutivoReceptor` (el consecutivo propio del Mensaje Receptor, el mismo valor que ya va dentro del XML como `<NumeroConsecutivoReceptor>`). Además, a diferencia de la acción genérica (donde `recp_tipoIdentificacion`/`recp_numeroIdentificacion` son opcionales), en `sendMensaje` son **obligatorios** — y aquí sí tienen valor real: el "receptor" de la acción de envío es el **proveedor** (emisor de la factura original), tomado de `self.partner_id` del `in_invoice`, exactamente como ya se arma `receptor_tipo`/`receptor_num` para una Factura normal.

Esto obliga a un método nuevo en el cliente, en vez de reutilizar `send_fe`:

```python
def send_mr(self, token, clave, fecha_iso, emisor_tipo, emisor_num,
            receptor_tipo, receptor_num, consecutivo_receptor, xml_firmado, environment):
    resp = self._call('send', 'sendMensaje', {
        'token': token,
        'clave': clave,
        'fecha': fecha_iso,
        'emi_tipoIdentificacion': emisor_tipo,
        'emi_numeroIdentificacion': emisor_num,
        'recp_tipoIdentificacion': receptor_tipo,
        'recp_numeroIdentificacion': receptor_num,
        'consecutivoReceptor': consecutivo_receptor,
        'comprobanteXml': base64.b64encode(xml_firmado.encode('utf-8')).decode('ascii'),
        'client_id': self._CLIENT_ID_BY_ENVIRONMENT[environment],
    })
    if not isinstance(resp, dict) or 'httpStatus' not in resp:
        raise CrlibreApiError("Respuesta inesperada de 'send/sendMensaje': %s" % resp)
    http_status = resp['httpStatus']
    if http_status not in (200, 202):
        raise CrlibreApiError("Hacienda rechazó el envío (HTTP %s): %s" % (http_status, resp.get('text')))
    return {'http_status': http_status, 'raw': resp.get('text') or []}
```

**Corrección posterior (verificada contra la colección Postman oficial de CRLibre, request "Envio Mensaje Receptor"):** la afirmación original de este párrafo era incorrecta. `clave` en el sobre de `sendMensaje` **no** es una clave nueva generada para el Mensaje Receptor — es `l10n_cr_fe_proveedor_clave`, la clave de la **factura original del proveedor** que se está confirmando/rechazando (se decodificó el `clave` de un request real de referencia y su `tipoDoc` interno resultó `01`, Factura Electrónica, no `05`/`06`/`07`). De igual forma, `fecha_iso` es la fecha de emisión del documento original (`l10n_cr_fe_proveedor_fecha_emision`), no el momento en que procesamos la respuesta. El consecutivo propio del Mensaje Receptor (obtenido vía `get_clave` con tipoDocumento `CCE`/`CPCE`/`RCE`) sigue siendo necesario, pero solo para llenar `consecutivoReceptor` — no para el campo `clave` del sobre. El `emisor`/`receptor` del sobre siguen la misma convención que el cuerpo del XML (ver `_l10n_cr_fe_build_mr_params`): `emisor` = el proveedor (`self.partner_id`), `receptor` = esta empresa (`config`).

(Nota aparte, no accionable en este proyecto: existe también una tercera acción `sendTE` dedicada a Tiquete Electrónico, con su propio listado de parámetros — nuestra implementación de TE ya construida usa la acción genérica `send`/`json` en su lugar, y fue verificada manualmente como aceptada por Hacienda en sandbox. Funciona; no se toca.)

### 2.4 Asistente: cargar factura de proveedor

Un wizard nuevo (`l10n_cr.fe.proveedor.upload`, `TransientModel`) donde el usuario sube el archivo XML recibido por correo. Al procesarlo:

1. Parsea el XML: datos del emisor (para ubicar o crear el `res.partner` proveedor por cédula), `Clave` y `FechaEmision` del documento original, y las líneas de `DetalleServicio`.
2. Para cada línea: busca un `product.product` existente por `l10n_cr_fe_cabys` igual al `CodigoCABYS` de la línea.
   - Si lo encuentra: arma la línea completa (cantidad, precio, impuesto según la tarifa del XML).
   - Si no lo encuentra: la línea queda marcada para que el usuario complete el producto a mano — no se crean productos nuevos automáticamente (evita duplicados/basura en el catálogo).
3. Crea un `account.move` en borrador (`move_type='in_invoice'`), con `l10n_cr_fe_proveedor_clave`/`l10n_cr_fe_proveedor_fecha_emision` poblados desde el XML, listo para revisión.

### 2.5 Decisión del usuario

Sobre esa factura de proveedor en borrador:

- **Aceptar total**: confirma la factura tal cual llegó del XML. `l10n_cr_fe_mr_decision = 'aceptado'`.
- **Aceptar parcial**: el usuario edita cantidades o quita líneas del borrador antes de confirmar — mismo mecanismo de selección/edición ya construido para Nota de Crédito parcial. `l10n_cr_fe_mr_motivo` es obligatorio. El monto total y el monto de impuesto que se reportan a Hacienda en el Mensaje Receptor salen de lo que quede en la factura tras el ajuste (Hacienda no recibe el detalle línea por línea de esta decisión — el `genXMLMr` real solo lleva un monto total agregado).
- **Rechazar**: `l10n_cr_fe_mr_decision = 'rechazado'`, `l10n_cr_fe_mr_motivo` obligatorio, no se contabiliza el `in_invoice` (queda cancelado/sin confirmar).

Al confirmar cualquiera de las tres, se dispara el envío del Mensaje Receptor (mismo patrón que `_l10n_cr_fe_generate_and_send`, generalizado con una rama para `move_type == 'in_invoice'`): construir params → `get_clave` (con el `consecutivo_codigo` de la decisión) → `gen_xml_mr` → firmar → `send_mr` (ver 2.3-bis — no `send_fe`) → guardar clave/estado.

### 2.6 Reutilización de vistas/acciones existentes

Los botones "Consultar estado FE" y "Reintentar envío FE", y el statusbar de `l10n_cr_fe_state`, se generalizan para mostrarse también cuando `move_type == 'in_invoice'` — mismo criterio `invisible=` ya usado para incluir `out_refund`.

**Corrección posterior (verificada contra el sandbox real):** "Consultar estado FE" sí necesitó lógica nueva, no fue una generalización directa. Se probó manualmente contra Hacienda y se confirmó que el Mensaje Receptor se rastrea por la clave de la **factura original del proveedor** (`l10n_cr_fe_proveedor_clave`), no por la clave propia que este módulo genera para el consecutivo del Mensaje Receptor (`l10n_cr_fe_clave`) — consistente con el sobre de `sendMensaje` (ver 2.3-bis). `action_l10n_cr_fe_consultar_estado` elige la clave correcta según `move_type` antes de consultar.

## 3. Fuera de alcance (documentado para retomar en el futuro)

- **Lectura automática de un buzón de correo**: esta iteración es solo subida manual del XML recibido por correo. Leer un buzón (IMAP/alias) y extraer automáticamente los XML adjuntos de proveedores queda como una fase futura separada — no requiere rediseñar nada de lo construido aquí, solo agregar una fuente alterna de entrada al mismo flujo de creación del `in_invoice` en borrador.
- **Comparación automática contra una Orden de Compra**: esta iteración depende de que el usuario revise el XML a ojo y decida. Comparar automáticamente contra un `purchase.order` (cantidad/precio esperado vs. recibido) para sugerir la decisión o marcar diferencias automáticamente es una mejora futura — este negocio ya tiene el módulo `purchase` instalado y en uso (`distribuidora_compras`), así que la integración es viable cuando se quiera retomar.
- **Recordatorios/alertas de plazo por vencer**: Hacienda da un plazo para responder un comprobante recibido; si no se responde, el sistema puede terminar dándolo por aceptado. Esta iteración no incluye ningún mecanismo de aviso (actividad de Odoo, cron, cálculo de días hábiles) para comprobantes pendientes cerca del vencimiento — es una pieza aparte, independiente del resto de este diseño.
- **Correo automático de confirmación al proveedor**: a diferencia del correo de aceptación que se le manda al cliente cuando Hacienda acepta una FE/NC/TE, aquí no hay un destinatario natural equivalente (quien cierra el ciclo es Hacienda notificando al emisor, no un correo nuestro) — no se construye ningún envío de correo como parte de este flujo.
- **Nota de Débito Electrónica (ND) y otros tipos de comprobante especiales (FEC, FEE)**: mencionados en la investigación de la API (`genXMLND`, `genXMLFec`, `genXMLFee` ya existen del lado de CRLibre) pero no son parte de este diseño — quedan como candidatos a proyectos futuros independientes, siguiendo el mismo patrón de extensión ya establecido.

## 4. Verificación

- Subir un XML de factura de proveedor de prueba con productos que ya tienen CABYS cargado → se crea el `in_invoice` en borrador con las líneas armadas automáticamente y los montos correctos.
- Subir un XML con un CABYS que no corresponde a ningún producto existente → la línea queda marcada para completar a mano, sin crear un producto nuevo solo.
- Aceptar total una factura de proveedor → se envía el Mensaje Receptor con `tipoDocumento=CCE` (código `05`), consecutivo propio empezando en 1, y el `in_invoice` queda confirmado con las líneas del XML.
- Aceptar parcial, quitando o ajustando alguna línea, con motivo → se envía con `tipoDocumento=CPCE` (`06`), el monto reportado a Hacienda corresponde a lo ajustado, y el `in_invoice` se confirma solo con esas líneas.
- Rechazar con motivo → se envía con `tipoDocumento=RCE` (`07`), y el `in_invoice` no queda contabilizado.
- Confirmar que "Consultar estado FE" y "Reintentar" funcionan igual sobre estos registros de `in_invoice`.
- Confirmar que los tres consecutivos (`05`/`06`/`07`) son independientes entre sí y de los de FE/NC/TE.
