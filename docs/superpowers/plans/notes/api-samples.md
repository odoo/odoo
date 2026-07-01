# Task 1 — Muestras reales de la API_Hacienda (CRLibre)

Fecha de captura: 2026-06-30. Stack de la API levantado localmente en `http://localhost:8080`.

## Envelope de respuesta (IMPORTANTE)

Todas las respuestas vienen envueltas así:

```json
{ "status": "ok", "resp": <datos> }
```

**El cliente de Odoo debe leer `data["resp"]`, no la raíz.** Conviene también verificar `data["status"] == "ok"`.

## Endpoint `ejemplo` (smoke test)

Request:
```
GET http://localhost:8080/api.php?w=ejemplo&r=hola
```
Response:
```json
{"status":"ok","resp":"hola :)"}
```

## Endpoint `clave` (`w=clave&r=clave`)

Request:
```
GET http://localhost:8080/api.php?w=clave&r=clave&tipoDocumento=FE&tipoCedula=fisico&cedula=702320717&consecutivo=1&situacion=normal&codigoSeguridad=12345678&sucursal=001&terminal=00001
```
Response:
```json
{"status":"ok","resp":{"clave":"50630062600070232071700100001010000000001112345678","consecutivo":"00100001010000000001","length":50}}
```
- `resp.clave`: 50 dígitos.
- `resp.consecutivo`: 20 dígitos (`sucursal(3) + terminal(5) + tipoDoc(2) + consecutivo(10)`).

## Endpoint `gen_xml_fe` (`w=genXML&r=gen_xml_fe`)

Request: GET con parámetros url-encoded. `detalles` y `medios_pago` van como **strings JSON**.
Cada elemento de `detalles` DEBE incluir: `codigoCABYS`, `subTotal`, `impuestoAsumidoEmisorFabrica`, `impuestoNeto` (además de `cantidad`, `unidadMedida`, `detalle`, `precioUnitario`, `montoTotal`, `montoTotalLinea`, `impuesto[]`).

Response:
```json
{"status":"ok","resp":{"clave":"...","xml":"<base64>"}}
```
- `resp.xml` viene **codificado en base64**. Decodificado empieza con:
```xml
<?xml version = "1.0" encoding = "utf-8"?>
<FacturaElectronica
  xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica" ...>
  <Clave>50630062600070232071700100001010000000001112345678</Clave>
  <ProveedorSistemas>702320717</ProveedorSistemas>
  <CodigoActividadEmisor>011101</CodigoActividadEmisor>
  <NumeroConsecutivo>00100001010000000001</NumeroConsecutivo>
  <FechaEmision>2026-06-30T09:00:00-06:00</FechaEmision>
  <Emisor>...</Emisor> <Receptor>...</Receptor> <DetalleServicio>...</DetalleServicio> <ResumenFactura>...</ResumenFactura>
</FacturaElectronica>
```
Confirmado: emite **versión v4.4** (la vigente). Esto resuelve la limitación #3 de la spec para el PoC.

## Arreglos de infraestructura necesarios para levantar la API (no venía "out of the box")

El stack Docker de la API no arranca tal cual en Windows/Debian actual. Fue necesario:

1. **Dockerfile** (`docker-php-apache/Dockerfile`): la base `php:7.4.9-apache` usa Debian **buster** (EOL); sus repos APT dan 404. Se apuntaron a `archive.debian.org` (fix de infraestructura local; el código PHP de la API no se tocó).
2. **Entrypoint** (`docker-php-apache/docker-entrypoint.sh`): tenía finales de línea **CRLF** → `exec ... no such file or directory`. Convertido a LF.
3. **`www/settings.php`**: el mecanismo `.env`/plantilla del entrypoint está desalineado (`core_install` quedaba vacío → "No se ha encontrado la carpeta api"). Se escribió un `settings.php` con valores fijos: `coreInstall = /var/www/html/api/`, BD `testdb/testuser/testpassword@mariadb`, crypto key dummy. (`www/settings.php` está en `.gitignore`.)
4. **Carpetas de la API**: faltaban `api/logs`, `api/errors`, `api/files` (montadas desde `./api`). Sin ellas, PHP emitía un `Warning` que **contaminaba el JSON** con HTML al final y rompería `response.json()`. Creadas con permisos 777.

> Recomendación: capturar este arranque como un project skill vía `/run-skill-generator`, porque requirió múltiples parches no obvios.

## Impacto en el plan

- `crlibre_client.py` debe parsear `data["resp"]` (no la raíz) y validar `status == "ok"`.
- La URL base para llamadas desde el contenedor Odoo será `http://host.docker.internal:8080` (verificado en Task 8).
