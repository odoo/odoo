# Lectura automática de un buzón de correo (XML de proveedores)

- **Fecha:** 2026-07-29
- **Estado:** Aprobado (diseño)
- **Alcance:** Automatizar la entrada del XML de facturas de proveedores a Odoo, leyendo un buzón de correo dedicado (Gmail/Google Workspace, vía OAuth2) en vez de exigir la subida manual del asistente en cada caso. No cambia nada del flujo de revisión/decisión (Aceptar total/parcial/Rechazar) ya construido — solo automatiza el paso de "meter el XML a Odoo".

---

## 1. Contexto

Hoy, para recibir y aceptar la factura electrónica de un proveedor, el usuario tiene que: recibir el XML por correo, descargarlo a su computadora, y subirlo a mano con el asistente `l10n_cr.fe.proveedor.upload`. El cliente reporta que este proceso manual es "muy cansino" y quiere que, si el proveedor ya manda el XML por correo (como exige el reglamento de Hacienda — no hay otra vía de descubrimiento automático), Odoo lo detecte solo.

Se investigó el código nativo de Odoo antes de diseñar: existe un modelo `fetchmail.server` (vive en el módulo `mail`, no es un módulo aparte en esta versión) que ya sabe conectarse a un buzón IMAP/POP y revisarlo por cron (`mail.ir_cron_mail_gateway_action`), con manejo de errores, reintentos y desactivación automática tras fallos repetidos — no hay que programar un poller desde cero. Además, el módulo `google_gmail` (también nativo) extiende `fetchmail.server` con autenticación OAuth2 para Gmail/Google Workspace (`server_type='gmail'`), necesaria porque Gmail no permite login IMAP con usuario/contraseña simple para la mayoría de cuentas.

Se decidió durante el diseño (ver sección 5) usar un **buzón dedicado exclusivamente a proveedores** — no el correo general de la empresa — precisamente porque `fetchmail.server` revisa toda la carpeta INBOX y marca como leído (`\Seen`) cada correo que procesa, sin distinguir cuáles son facturas. Sobre el correo general de la empresa, esto interferiría con el uso diario de esa bandeja por el resto del personal.

## 2. Prerrequisito externo (fuera del alcance de este proyecto)

Antes de poder configurar el `fetchmail.server`, alguien con acceso administrativo a Google Cloud Console debe, **fuera de Odoo**:
1. Crear un proyecto en Google Cloud Console y habilitar la API de Gmail.
2. Crear credenciales OAuth2 (Client ID/Secret) con el redirect URI que pida Odoo.
3. Pegar ese Client ID/Secret en Odoo (Ajustes generales → sección de correo).
4. Crear/tener ya la cuenta de correo dedicada (ej. `facturas@tuempresa.cr`) como una cuenta de Gmail o Google Workspace real.

Este proyecto **no incluye** hacer esa configuración (requiere credenciales y acceso que no están disponibles durante el desarrollo) — solo construye el código que consume el `fetchmail.server` una vez que ese registro exista y esté conectado. Un quinto paso, posterior a los cuatro anteriores — crear el registro `fetchmail.server` en sí (con `server_type='gmail'`, `object_id` apuntando a nuestro modelo nuevo) y darle clic a "Conectar cuenta de Gmail" — también es configuración de datos, no código: se documenta como instrucción de despliegue, no como tarea de implementación.

## 3. Diseño

### 3.1 Modelo nuevo: `l10n_cr.fe.proveedor.email`

Actúa como bandeja de auditoría — el destino (`object_id`) del `fetchmail.server`. Hereda `mail.thread` (requisito de Odoo para poder recibir correo entrante vía `message_new`; además guarda el correo original y sus adjuntos en el chatter del registro, gratis).

```python
class L10nCrFeProveedorEmail(models.Model):
    _name = 'l10n_cr.fe.proveedor.email'
    _inherit = ['mail.thread']
    _description = "Correo entrante de proveedor (XML de factura electrónica)"
    _order = 'id desc'

    email_from = fields.Char(string="Remitente", readonly=True)
    date = fields.Datetime(string="Fecha de recepción", readonly=True)
    state = fields.Selection([
        ('procesado', "Factura creada"),
        ('duplicado', "Ya existía (Clave duplicada)"),
        ('sin_xml_valido', "Sin XML válido"),
    ], string="Estado", readonly=True)
    move_id = fields.Many2one('account.move', string="Factura de proveedor", readonly=True)
    error_message = fields.Text(string="Motivo", readonly=True)
```

No se expone ningún botón de "crear"/"editar" manual — estos registros solo los crea el mailgateway. Los usuarios de contabilidad (`account.group_account_invoice`) tienen acceso de solo lectura; `account.group_account_manager` tiene CRUD completo (para poder limpiar registros viejos), mismo patrón de dos niveles que ya usa `l10n_cr.fe.config`.

### 3.2 Refactor: extraer el parseo del XML a un método compartido

Hoy toda la lógica de parseo (`_find_text`, `_find_product`, `_find_tax`, armar líneas, resolver partner, totales de `ResumenFactura`) vive dentro del wizard `l10n_cr.fe.proveedor.upload` (`wizards/proveedor_upload.py`). Se extrae a un método nuevo en `account.move` (donde ya vive el resto de la lógica `_l10n_cr_fe_*` de este módulo):

```python
@api.model
def _l10n_cr_fe_build_vals_from_proveedor_xml(self, xml_bytes):
    """Parsea un XML de factura de proveedor (schema Hacienda v4.4) y devuelve
    el dict de creación para un account.move en_invoice — clave/fecha/montos
    del proveedor, partner resuelto/creado, y líneas armadas con match de
    CABYS/impuesto. Levanta UserError si el XML no tiene los datos mínimos
    (Clave/Emisor). Usado tanto por el asistente manual como por el flujo
    automático de correo — misma lógica, un solo lugar."""
```

El wizard pasa a ser una capa fina: llama a este método, crea el `account.move`, y abre su formulario. El nuevo flujo de correo (sección 3.3) llama exactamente al mismo método.

### 3.3 Hook de procesamiento en `l10n_cr.fe.proveedor.email`

```python
def _message_post_after_hook(self, new_message, message_values):
    res = super()._message_post_after_hook(new_message, message_values)
    self._l10n_cr_fe_procesar_adjuntos(new_message)
    return res

def _l10n_cr_fe_procesar_adjuntos(self, message):
    self.ensure_one()
    for attachment in message.attachment_ids.filtered(lambda a: a.name.lower().endswith('.xml')):
        try:
            vals = self.env['account.move']._l10n_cr_fe_build_vals_from_proveedor_xml(
                base64.b64decode(attachment.datas))
        except UserError:
            continue  # no es un XML de factura válido -- se prueba el siguiente adjunto
        clave = vals['l10n_cr_fe_proveedor_clave']
        existing = self.env['account.move'].search([('l10n_cr_fe_proveedor_clave', '=', clave)], limit=1)
        if existing:
            self.write({'state': 'duplicado', 'move_id': existing.id})
        else:
            move = self.env['account.move'].create(vals)
            self.write({'state': 'procesado', 'move_id': move.id})
        return
    self.write({'state': 'sin_xml_valido', 'error_message': _("El correo no traía ningún adjunto XML de factura electrónica válido.")})
```

`email_from`/`date` se llenan desde `message_new` (heredado de `mail.thread`, ya trae esos datos del correo entrante — solo hace falta mapearlos a estos dos campos con un pequeño override).

### 3.4 Vista y menú

Una vista de lista simple (`email_from`, `date`, `state`, `move_id`) bajo un nuevo menú "Bandeja de facturas de proveedores" (junto al menú existente "Cargar factura de proveedor (FE)"), para auditar qué llegó y qué pasó con cada correo. Clic en la fila abre el formulario (con el chatter mostrando el correo original y sus adjuntos).

### 3.5 El asistente manual se mantiene

`l10n_cr.fe.proveedor.upload` sigue existiendo tal cual, como vía alterna para XML recibidos por otro canal (WhatsApp, USB, etc.) — esta feature es un canal de entrada adicional al mismo flujo de creación de `in_invoice`, no un reemplazo.

## 4. Manejo de errores

- **Fallo de conexión al buzón** (token OAuth vencido, servidor caído): lo maneja `fetchmail.server` nativamente — reintentos, `error_date`/`error_message`, autodesactivación tras fallos repetidos. No se construye nada nuevo para esto.
- **XML mal formado o sin `Clave`/`Emisor`**: `_l10n_cr_fe_build_vals_from_proveedor_xml` levanta `UserError` (mismo criterio que ya usa el asistente hoy); el hook lo captura y prueba el siguiente adjunto si hay más de uno, o marca `sin_xml_valido` si ninguno sirvió.
- **Clave duplicada**: se detecta por búsqueda directa antes de crear, se enlaza a la factura existente en vez de duplicar.
- **CABYS sin producto / impuesto sin match**: igual que hoy en el asistente — la línea queda para completar a mano, no bloquea la creación.

## 5. Decisiones tomadas durante el diseño

- **Buzón dedicado, no el correo general de la empresa** — evita que el proceso automático marque como leído y procese correo que no tiene nada que ver con proveedores, interfiriendo con el uso diario de una bandeja compartida.
- **Correos sin XML válido se registran en el log de auditoría, pero no crean factura** — visibilidad sin ensuciar la lista de Facturas de proveedor.
- **Duplicados por Clave se detectan y no se duplican** — se enlazan a la factura ya existente.

## 6. Fuera de alcance (documentado para retomar en el futuro)

- **Aislar por etiqueta de Gmail en vez de buzón dedicado**: se consideró y se descartó por ahora (se prefirió un buzón dedicado, más simple); si en el futuro se decide usar el correo general de la empresa, se necesitaría además sobrescribir la selección de carpeta IMAP (`fetchmail.server` hoy siempre revisa `INBOX`) para apuntar a una etiqueta/carpeta específica.
- **Recordatorios/alertas de plazo por vencer**: ahora que cada factura de proveedor puede tener una fecha real de "recibido por correo" (`l10n_cr_fe_proveedor_email.date`), esto habilita — pero no construye — el proyecto ya documentado como fuera de alcance en el diseño de Recepción de comprobantes (avisar cuando se acerca el plazo de Hacienda para responder).
- **Soporte para otros proveedores de correo (Outlook/IMAP genérico)**: el diseño asume Gmail/Google Workspace porque es lo que decidió el cliente; agregar Outlook (módulo `microsoft_outlook`, mismo patrón de `fetchmail.server`) o IMAP genérico con usuario/contraseña sería una extensión directa si el proveedor de correo cambia.
- **Reprocesar manualmente un registro `sin_xml_valido`**: no se agrega ningún botón de "reintentar" sobre estos logs — si algo falló, hoy la única vía es usar el asistente manual con el XML adjunto descargado a mano.

## 7. Verificación

- Simular un correo entrante con un XML válido adjunto (usando las utilidades de test de `mail.thread`/`message_process`, sin conexión IMAP real) → se crea el `l10n_cr.fe.proveedor.email` con `state='procesado'` y el `account.move` en borrador, igual que si se hubiera subido con el asistente.
- Simular un correo con la misma Clave que una factura ya existente → `state='duplicado'`, enlazado a la factura existente, no se crea una segunda.
- Simular un correo sin adjunto XML (o con uno inválido) → `state='sin_xml_valido'`, con motivo, sin factura creada.
- Confirmar que el asistente manual (`l10n_cr.fe.proveedor.upload`) sigue funcionando igual tras el refactor (mismos tests existentes, ahora contra el método compartido).
