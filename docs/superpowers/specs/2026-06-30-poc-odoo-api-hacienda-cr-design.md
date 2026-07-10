# PoC de conectividad y generación — Odoo ↔ API_Hacienda (CRLibre)

- **Fecha:** 2026-06-30
- **Estado:** Aprobado (diseño)
- **Alcance:** Prueba de concepto en *sandbox*. Solo **conectividad y generación** (clave + XML). Sin firma, sin token, sin envío a Hacienda.
- **Enfoque elegido:** Addon de Odoo (`l10n_cr_fe_crlibre`) con **botón manual** en la factura de cliente.

---

## 1. Contexto

El sistema Odoo 19 (este repositorio, rama `19.0`) corre en Docker (`docker-compose.yml`:
servicios `db` PostgreSQL 16 y `odoo` en el puerto 8069). Ya tiene instalados los módulos
`sale_management`, `stock`, `sale_stock` y `purchase_stock`.

El módulo `l10n_cr` de Odoo **solo aporta el plan de cuentas** de Costa Rica; **no** incluye
factura electrónica ni conexión con el Ministerio de Hacienda (verificado: cero referencias a
`comprobanteselectronicos` / `hacienda.go.cr` en `addons/`). Odoo sí trae el framework genérico
`account_edi`, pero no un conector para Costa Rica.

La **API_Hacienda** de CRLibre (clonada en `D:\API_Hacienda`) es una API PHP (basada en CalaAPI)
que cubre el ciclo de Factura Electrónica de CR: generación de clave, generación de XML
(FE/NC/ND/TE/Mensajes), firma XAdES con certificado `.p12`, token OAuth, envío a Hacienda y
consulta de estado. Tiene su propio stack Docker (PHP + Apache en 8080/8443, MariaDB en 4407) y su
propia base de datos MySQL multi-tenant.

**Hecho técnico decisivo:** los endpoints `clave` (`w=clave&r=clave`) y `gen_xml_fe`
(`w=genXML&r=gen_xml_fe`) están declarados como `users_openAccess` — **no requieren login,
sessionKey ni certificado**. Esto hace viable un PoC mínimo con solo dos llamadas HTTP.

---

## 2. Objetivo y definición de "hecho"

Desde una factura de cliente en Odoo, pulsar un botón:

1. Mapea los datos de la factura a los parámetros de la API.
2. Llama a `clave` y obtiene la **clave numérica de 50 dígitos**.
3. Llama a `gen_xml_fe` y obtiene el **XML de Factura Electrónica** (sin firmar).
4. Guarda clave + XML en la factura y lo registra en el chatter.

**Éxito = ** una factura de prueba muestra una clave de 50 dígitos y un XML bien formado,
guardados en sus campos. **No** se firma ni se envía a Hacienda.

---

## 3. Arquitectura

```
┌─────────────────┐     HTTP (host.docker.internal:8080)     ┌──────────────────┐
│  Odoo 19         │  ── api.php?w=clave&r=clave ─────────▶   │  API_Hacienda    │
│  erp-odoo-1      │  ── api.php?w=genXML&r=gen_xml_fe ───▶    │  PHP + Apache    │
│  (PostgreSQL)    │  ◀── { clave }  /  { xml } ──────────     │  + MariaDB       │
│                  │                                           │  (stack aparte)  │
│  addon nuevo:    │                                           │  puerto 8080     │
│  l10n_cr_fe_     │                                           └──────────────────┘
│  crlibre         │
└─────────────────┘
```

- **Dos stacks Docker independientes.** Odoo llama a la API por `host.docker.internal:8080`.
  No se modifican las redes de Docker; es la opción más simple y reversible.
- La API se levanta con su propio `docker-compose.yml`. Requisitos previos:
  - Crear un archivo vacío `www/settings.php` (lo persiste un volumen).
  - MariaDB carga el seed `recursos/sql/api_base.sql` al inicializarse.
- Ambos endpoints del PoC son `users_openAccess`: sin login, token ni certificado.

---

## 4. Componentes del addon `l10n_cr_fe_crlibre`

Ubicación: `addons/l10n_cr_fe_crlibre/`.

### 4.1 `__manifest__.py`
- `name`: "Costa Rica - Factura Electrónica (PoC CRLibre)".
- `depends`: `['account', 'l10n_cr']`.
- `data`: vistas de `account.move`, parámetros de configuración.
- `license`: `LGPL-3` (nuestro código; **no** incrustamos código de la API AGPL).

### 4.2 `models/account_move.py` (extensión de `account.move`)
Campos nuevos:
- `l10n_cr_fe_clave` — `Char`, solo lectura. Clave de 50 dígitos.
- `l10n_cr_fe_xml` — `Text`, solo lectura. XML generado.
- `l10n_cr_fe_state` — `Selection([('draft','Borrador'),('generated','Generado'),
  ('error','Error')])`, por defecto `draft`.

Método:
- `action_l10n_cr_fe_generate(self)` — orquesta: construye params → `get_clave` →
  `gen_xml_fe` → guarda resultados → postea en el chatter. Captura errores y marca estado `error`.

### 4.3 `models/crlibre_client.py` (servicio HTTP — `AbstractModel` o helper)
- `get_clave(self, params) -> str` — llama `GET api.php?w=clave&r=clave` con timeout; devuelve la clave.
- `gen_xml_fe(self, params) -> str` — llama `GET api.php?w=genXML&r=gen_xml_fe`; devuelve el XML.
- Usa la librería `requests`. Lee la URL base de `ir.config_parameter`.
- Maneja: timeout, conexión rechazada, status != 200, cuerpo inesperado → lanza excepción
  tipada que el método del move convierte en `UserError`.

### 4.4 Configuración (`ir.config_parameter`)
Sembrada vía `data/config_params.xml`:
- `l10n_cr_fe.api_url` = `http://host.docker.internal:8080`
- `l10n_cr_fe.proveedor_sistemas` = cédula del proveedor de sistemas (fija para el PoC)
- Datos fijos del emisor para el PoC: `cedula`, `tipo_identif`, `provincia`, `canton`,
  `distrito`, `otras_senas`, `email`, `codigo_actividad`. (En esta fase **no** se leen de
  `res.company`.)

### 4.5 Vistas (`views/account_move_views.xml`)
- Botón "Generar comprobante (PoC)" en la cabecera del formulario de factura, visible solo para
  `move_type == 'out_invoice'`.
- Una pestaña/grupo "Factura Electrónica CR" mostrando `l10n_cr_fe_state`, `l10n_cr_fe_clave` y el XML.

---

## 5. Mapeo factura → parámetros de la API (PoC, mínimo)

### 5.1 `clave` (`w=clave&r=clave`)
Parámetros requeridos: `tipoDocumento`, `tipoCedula`, `cedula`, `consecutivo`, `situacion`,
`codigoSeguridad` (y opcionales `codigoPais`, `terminal`, `sucursal`).

| Parámetro | Origen en el PoC |
|---|---|
| `tipoDocumento` | fijo: `FE` |
| `tipoCedula`, `cedula` | config fija del emisor |
| `consecutivo` | generado en el PoC (contador simple / placeholder de 20 dígitos) |
| `situacion` | fijo: `normal` |
| `codigoSeguridad` | aleatorio de 8 dígitos generado en el PoC |
| `terminal`, `sucursal` | fijos: `00001` / `001` |

### 5.2 `gen_xml_fe` (`w=genXML&r=gen_xml_fe`)
| Parámetro API | Origen en Odoo |
|---|---|
| `clave` | salida del paso anterior |
| `proveedor_sistemas`, `codigo_actividad_emisor`, `emisor_*` | config fija del emisor |
| `consecutivo`, `fecha_emision` | generados / fecha de la factura en formato `YYYY-MM-DDThh:mm:ss-06:00` |
| `receptor_*` | `partner_id` de la factura (nombre, tipo y número de cédula, email) |
| `condicion_venta`, `medios_pago` | fijos: `01` (contado) / `01` (efectivo) |
| `cod_moneda`, `tipo_cambio` | moneda de la factura / `1` si es CRC |
| `detalles` | `invoice_line_ids` serializadas (línea, descripción, cantidad, precio, total) |
| `total_ventas`, `total_ventas_neta`, `total_comprobante` | totales de la factura |

> Nota: el formato exacto de `detalles` (string vs. JSON) se confirma leyendo `genXML.php`
> durante la implementación, antes de fijar el serializador.

---

## 6. Manejo de errores

- API caída / timeout / conexión rechazada / status != 200 / cuerpo inesperado →
  la factura pasa a `l10n_cr_fe_state = 'error'`, se postea el detalle en el chatter y se
  lanza un `UserError` legible.
- Nunca se bloquea la validación contable ni se rompe la transacción de Odoo.
- Los datos faltantes obligatorios (p. ej. cédula del receptor) se validan **antes** de llamar
  a la API, con mensaje claro.

---

## 7. Estrategia de pruebas

1. **Smoke de la API:** `GET api.php?w=ejemplo&r=hola` responde OK tras levantar el stack.
2. **Test unitario (TransactionCase):** el mapeo factura→params produce el diccionario esperado
   a partir de una factura demo (sin red; se *mockea* el cliente HTTP).
3. **Prueba manual end-to-end:** crear factura de cliente de prueba → botón "Generar comprobante
   (PoC)" → verificar clave de 50 dígitos + XML bien formado guardados.

---

## 8. Limitaciones y consideraciones (riesgos conocidos)

1. **Sin certificado = sin valor fiscal.** El XML va sin firmar; no tiene validez ante Hacienda.
   Es demostración técnica (acordado).
2. **Licencia AGPL v3 de la API.** Si en el futuro **modificamos** la API y la exponemos como
   servicio, hay obligación legal de publicar los cambios. En el PoC **solo consumimos** la API
   (no la modificamos) para evitar esa obligación.
3. **Versión del XML.** Debe confirmarse que `gen_xml_fe` emite la versión vigente exigida por
   Hacienda (v4.4). Si genera una versión anterior, el XML no serviría en producción aunque el
   PoC "funcione".
4. **Catálogos de Hacienda ≠ catálogos de Odoo.** Ubicación (provincia/cantón/distrito), unidades
   de medida e impuestos (IVA 13 % y tarifas) usan catálogos propios de Hacienda. El PoC usa
   valores fijos; un flujo real necesita una capa de mapeo.
5. **Consecutivos y claves.** En el PoC se generan pero **no** se gestionan como secuencia fiscal
   real. Usarlo "en serio" sin control de consecutivos causaría duplicados/rechazos.
6. **Calidad del código de la API.** Es PHP legacy con SQL por concatenación (propenso a
   inyección). No es apto para exponer a internet sin endurecerlo. En el PoC se mantiene **solo
   en local**.
7. **Dos bases de datos / dos stacks.** Mayor costo operativo. El propio CRLibre advierte que sus
   contenedores **no están optimizados para producción**.
8. **Red entre contenedores.** Depende de que `host.docker.internal` resuelva desde el contenedor
   de Odoo (válido en Docker Desktop / Windows, que es el entorno actual). En otro entorno habría
   que ajustar la estrategia de red.

---

## 9. Fuera de alcance (fases futuras)

Firma XAdES con `.p12`, token OAuth contra el IDP de Hacienda, envío a recepción, consulta de
estado, mensajes de aceptación/rechazo, gestión real de consecutivos como secuencia fiscal,
mapeo completo de catálogos (ubicación, unidades, impuestos), y lectura de los datos del emisor
desde `res.company` en lugar de configuración fija.
