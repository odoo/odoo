# Integración completa de Factura Electrónica CR (sandbox) — Odoo ↔ API_Hacienda ↔ Hacienda

- **Fecha:** 2026-07-06
- **Estado:** Aprobado (diseño)
- **Alcance:** Ciclo completo de Factura Electrónica (FE) contra el **sandbox de Hacienda**, con firma XAdES, envío, consulta de estado y notificación al cliente. Multi-company desde el inicio. Notas de Crédito/Débito, Tiquete Electrónico y mensajes de confirmación receptor quedan fuera de esta fase.
- **Continúa de:** `docs/superpowers/specs/2026-06-30-poc-odoo-api-hacienda-cr-design.md` (PoC de conectividad y generación, ya funcionando).

---

## 1. Contexto

El PoC (`l10n_cr_fe_crlibre`) ya demuestra que desde una factura de Odoo se puede generar una clave de 50 dígitos y un XML v4.4 sin firmar, llamando a dos endpoints `users_openAccess` de la API_Hacienda (CRLibre) local. Esta fase lleva ese PoC a un ciclo **fiscalmente completo**: firma con certificado `.p12`, autenticación OAuth contra el IDP real de Hacienda, envío a recepción, consulta de estado (aceptado/rechazado) y entrega al cliente por correo — todo contra el **ambiente sandbox** (`stag`) de Hacienda, con datos tributarios reales de prueba ya obtenidos (usuario/contraseña `stag`, PIN, cédula, certificado `.p12`).

Exploración de `D:\API_Hacienda` (más allá de lo que usa el PoC) confirmó que la API ya implementa el pipeline completo:
- `token` (`w=token&r=gettoken`/`refresh`) — OAuth contra el IDP de Hacienda (`grant_type=password`).
- `clave` / `genXML` — ya integrados en el PoC.
- `firmarXML` (`w=firmar&r=firmar`) / `signXML` — firma XAdES con `.p12`, requiere un `p12Url` que en realidad es un **`downloadCode`** obtenido subiendo el certificado previamente vía `fileUploader` (`subir_certif`), bajo sesión propia del sistema de usuarios interno de la API (independiente de las credenciales de Hacienda).
- `send` (`w=send&r=json`) — POST a `https://api-sandbox.comprobanteselectronicos.go.cr/recepcion/v1/recepcion/` (o el equivalente de producción según `client_id`).
- `consultar` (`w=consultar&r=consultarCom`) — GET de estado por clave.

También existe un módulo `facturador` con su propia capa multi-tenant (empresas, receptores, consecutivos, inventario). **Decisión: no se usa** — Odoo ya es la fuente de verdad de partners/productos/secuencias; duplicar esa gestión en la API añadiría complejidad sin beneficio.

**Dato sensible:** las credenciales de Hacienda (usuario/contraseña, PIN, certificado) obtenidas para esta fase son datos fiscales reales. No se guardan en este spec, en el plan de implementación, ni en ningún archivo versionado. Se ingresan una sola vez, a mano, en la configuración de Odoo una vez implementado el modelo `l10n_cr.fe.config`.

---

## 2. Objetivo y definición de "hecho"

Al confirmar (`action_post`) una factura de cliente en Odoo, el sistema debe, de forma automática y sin bloquear el posteo contable:

1. Generar clave y consecutivo fiscal real (secuencia por empresa, sin huecos ni duplicados).
2. Generar el XML v4.4.
3. Firmarlo con el certificado `.p12` de la empresa emisora.
4. Obtener un token OAuth de Hacienda y enviar el comprobante a recepción.
5. Permitir consultar el estado (botón manual) y, al quedar **aceptado**, notificar por correo al cliente con el XML firmado y la respuesta de Hacienda adjuntos.
6. Si Hacienda **rechaza**, permitir reintentar el envío con una clave/consecutivo nuevos sin afectar la factura contable ya posteada.

**Éxito =** una factura de prueba, contra el sandbox real de Hacienda, llega a estado **aceptado** con el flujo disparado automáticamente desde `action_post`, usando datos tributarios cargados desde Odoo (no fijos en código).

**Multi-company:** cada `res.company` tiene su propia configuración tributaria (cédula, ubicación, certificado, credenciales, ambiente stag/prod) — pensado para que un cliente nuevo del sistema pueda darse de alta con sus propios datos sin tocar código, aunque en esta fase solo se valide contra sandbox.

---

## 3. Arquitectura

```
┌─────────────────────────┐        HTTP (host.docker.internal:8080)        ┌────────────────────────┐
│  Odoo 19 (erp-odoo-1)    │ ───────────────────────────────────────────▶  │  API_Hacienda (CRLibre)│
│                          │                                                │  (stack local existente)│
│  addon                   │                                                │                          │
│  l10n_cr_fe_crlibre      │ ◀─────────────────────────────────────────── │                          │
│  (extendido, no nuevo)   │                                                └───────────┬──────────────┘
└─────────────────────────┘                                                            │ HTTPS
                                                                                          ▼
                                                                          ┌──────────────────────────────┐
                                                                          │ Hacienda (sandbox por ahora)  │
                                                                          │ idp.comprobanteselectronicos │
                                                                          │ api-sandbox.comprobantes...  │
                                                                          └──────────────────────────────┘
```

- Se extiende el addon existente `l10n_cr_fe_crlibre` — reutiliza el cliente HTTP base (`l10n_cr.fe.client`) y los tests ya existentes de `clave`/`genXML`.
- Los datos tributarios viven en un modelo companion `l10n_cr.fe.config` (1-a-1 con `res.company`), no en `ir.config_parameter` global — habilita multi-company real.
- No se usa el módulo `facturador` de la API. Solo los endpoints de bajo nivel: `token`, `clave`, `genXML`, `firmarXML`, `send`, `consultar`, y `fileUploader` (solo para la subida inicial del certificado).
- Gestión del certificado: Odoo crea **un usuario en la API por cada empresa Odoo** (registro automático, contraseña generada al azar, guardada junto al resto de la config), y hace login + subida del `.p12` en background cuando el usuario lo carga desde Odoo, obteniendo el `download_code` que luego se usa para firmar.
- Siguen dos stacks Docker (Odoo + API_Hacienda) comunicándose por `host.docker.internal`, sin cambios de topología.

---

## 4. Modelos de datos

### 4.1 `l10n_cr.fe.config` (nuevo, 1-a-1 con `res.company` vía `company_id`)

| Campo | Tipo | Notas |
|---|---|---|
| `company_id` | Many2one `res.company` | único por empresa |
| `environment` | Selection `stag`/`prod` | controla URLs/realm/`client_id` usados por el cliente HTTP |
| `identification_type` | Selection (01 física, 02 jurídica, 03 DIMEX, 04 NITE) | |
| `identification_number` | Char | cédula del emisor |
| `legal_name`, `trade_name` | Char | razón social / nombre comercial |
| `economic_activity_code` | Char | código de actividad económica |
| `province`, `canton`, `district`, `neighborhood` | Char | ubicación, entrada manual (sin importar catálogo, consistente con CABYS) |
| `address_detail` | Char | "otras señas" |
| `phone`, `email` | Char | |
| `branch_number`, `terminal_number` | Char, fijos por defecto (`'001'`/`'00001'`) | |
| `hacienda_username`, `hacienda_password` | Char, grupo restringido `l10n_cr_fe.group_fe_admin` | credenciales del contribuyente ante el IDP de Hacienda |
| `certificate_file` | Binary | `.p12` subido desde Odoo |
| `certificate_pin` | Char, mismo grupo restringido | PIN de 4 dígitos |
| `crlibre_api_username`, `crlibre_api_password` | Char, invisibles en UI normal | cuenta de servicio auto-generada en la API_Hacienda para esta empresa |
| `certificate_download_code` | Char, readonly | resultado de subir el `.p12` |

**Seguridad de secretos (nivel razonable para esta fase, no cifrado a nivel de BD):** los campos de contraseña/PIN usan `groups=` restringido a un grupo nuevo `l10n_cr_fe.group_fe_admin`, widget `password` en la vista, y nunca se postean en el chatter ni se loguean. Cifrado real en BD queda como mejora futura explícitamente fuera de esta fase.

### 4.2 `account.move` (extiende lo del PoC)

- Mantiene: `l10n_cr_fe_clave`, `l10n_cr_fe_consecutivo`, `l10n_cr_fe_xml`.
- Nuevos: `l10n_cr_fe_xml_firmado` (Text), `l10n_cr_fe_respuesta_xml` (Text), `l10n_cr_fe_motivo_rechazo` (Char).
- `l10n_cr_fe_state` amplía sus opciones: `draft → generado → enviado → aceptado / rechazado / error`.
- Botón "Consultar estado FE" (visible si `state == 'enviado'`).
- Botón "Reintentar envío FE" (visible si `state == 'rechazado'`).
- Override de `action_post()`: dispara la orquestación completa automáticamente, sin bloquear el posteo contable si algo falla.

### 4.3 `product.template`

- Nuevo campo `l10n_cr_fe_cabys` (Char, 13 dígitos, con constraint de formato). Entrada manual, sin importar el catálogo completo de CABYS en esta fase.

### 4.4 Secuencia fiscal

- `ir.sequence` por empresa + tipo de documento (FE), usada para el número secuencial de 10 dígitos del consecutivo (`sucursal(3) + terminal(5) + tipoDoc(2) + secuencial(10)`), con `branch_number`/`terminal_number` fijos desde `l10n_cr.fe.config`.

---

## 5. Cliente HTTP (`l10n_cr.fe.client`, `AbstractModel` existente, se le agregan métodos)

| Método | Endpoint API_Hacienda | Uso |
|---|---|---|
| `register_api_user(username, password)` | `users_register` | una vez por empresa, al guardar config por primera vez |
| `login_api_user(username, password)` | `users_log_me_in` | obtiene `sessionKey` interno de la API (no es el token de Hacienda) |
| `upload_certificate(session_key, p12_bytes)` | `fileUploader/subir_certif` | devuelve `download_code` |
| `get_hacienda_token(username, password, environment)` | `token/gettoken` | token OAuth real de Hacienda (stag o prod) |
| `sign_xml(download_code, pin, xml_base64)` | `firmarXML/firmar` | XML firmado en base64 |
| `send_fe(token, clave, xml_firmado_base64, ...)` | `send/json` | envío a recepción v1 |
| `consultar_estado(token, clave, environment)` | `consultar/consultarCom` | consulta síncrona bajo demanda |

### Flujo completo al confirmar una factura (`action_post`)

```
1. _l10n_cr_fe_ensure_certificate_uploaded()
   → si l10n_cr.fe.config no tiene download_code todavía (fallback/lazy-init;
     normalmente ya se hizo al guardar la configuración):
     register_api_user (si no existe cuenta) → login → upload_certificate → guardar download_code

2. get_clave(...)          → clave + consecutivo (vía ir.sequence de la empresa)
3. gen_xml_fe(...)         → XML sin firmar
4. get_hacienda_token(...) → token OAuth (se pide uno nuevo cada vez; sin cache/refresh,
                              simplificación válida al volumen bajo de esta fase)
5. sign_xml(...)           → XML firmado
6. send_fe(...)            → Hacienda responde "recibido" (HTTP 202) → state = 'enviado'
```

---

## 6. Manejo de errores

Mismo principio que el PoC: cualquier excepción en los pasos 1-6 se captura, persiste `state = 'error'` con el detalle en el chatter, y retorna una notificación no bloqueante. **Nunca se interrumpe la transacción de posteo contable.**

- **Botón "Consultar estado FE"** (`state == 'enviado'`): llama `consultar_estado`.
  - `aceptado` → guarda `l10n_cr_fe_respuesta_xml`, dispara correo con adjuntos (ver §7).
  - `rechazado` → guarda `l10n_cr_fe_motivo_rechazo`, habilita "Reintentar envío FE".
  - pendiente → sin cambios; el usuario puede volver a consultar después.
- **Botón "Reintentar envío FE"** (`state == 'rechazado'`): repite el flujo desde el paso 2 (clave/consecutivo nuevos — Hacienda no permite reenviar una clave rechazada).

---

## 7. Notificación al cliente

Al quedar `aceptado`, se dispara un `mail.template` que envía un correo a `partner_id.email` adjuntando:
- El XML firmado del comprobante.
- El XML de respuesta de Hacienda.

Fuera de alcance de esta fase: representación gráfica / PDF del comprobante para el cliente (se resuelve en una fase posterior, reutilizando el reporte de factura que ya tiene Odoo).

---

## 8. Estrategia de pruebas

**Unitarias (mock del cliente HTTP, sin red, patrón ya usado en el addon):**
- Cada método nuevo de `l10n_cr.fe.client`: request bien formado, parseo de respuesta OK, manejo de error (HTTP≠200, JSON inválido, `status≠ok`).
- `l10n_cr.fe.config`: constraints de formato (CABYS, cédula), flujo de `download_code` con `register_api_user`/`login_api_user`/`upload_certificate` mockeados.
- `account.move`: mapeo factura→parámetros (extiende el existente), consecutivo vía `ir.sequence`, orquestación completa de `action_post` mockeada (éxito y cada punto de falla marca `state='error'` sin romper el posteo), transición `enviado→aceptado` con envío de correo, transición `enviado→rechazado` habilitando reintento.
- Seguridad: un usuario sin `l10n_cr_fe.group_fe_admin` no puede leer `hacienda_password`/`certificate_pin`.

**Manual end-to-end contra el sandbox real (una sola vez, con las credenciales ya obtenidas):**
- Configurar la empresa en Odoo con cédula, `.p12`, PIN y credenciales `stag` reales.
- Confirmar una factura de prueba → el flujo automático debe llegar a `enviado`, y al consultar manualmente debe pasar a `aceptado` contra el sandbox real.
- Documentar como evidencia (clave generada, resultado), **sin** guardar credenciales/PIN en el archivo de evidencia.

---

## 9. Fuera de alcance (fases futuras)

Ambiente de producción real (esta fase se valida y cierra contra `stag`), Notas de Crédito/Débito, Tiquete Electrónico, mensajes de confirmación receptor (aceptación/rechazo de comprobantes recibidos de proveedores), múltiples sucursales/terminales por empresa, importación del catálogo completo CABYS, representación gráfica/PDF del comprobante, cache/refresh de tokens OAuth, cifrado en BD de credenciales/PIN, consulta de estado automática por cron (queda manual por ahora).

---

## 10. Riesgos abiertos a validar durante la implementación

1. **Formato exacto de `send`/`consultar` en el envelope `{status, resp}`** — el PoC ya confirmó el envelope para `clave`/`genXML`; falta confirmar el de `token`, `firmarXML`, `send` y `consultar` (probablemente el mismo, pero se valida contra el sandbox real).
2. **`client_id` de producción** — se conoce `client_id=api-stag` para sandbox; el valor exacto para producción se confirma cuando se necesite (fuera de alcance de esta fase).
3. **Multi-tenencia del usuario de servicio en la API_Hacienda** — se asume que `users_register` no colisiona entre empresas si se generan `username` únicos (ej. basados en `company_id` + cédula); se valida en la implementación.
