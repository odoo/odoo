# Buscador CABYS integrado en el formulario de producto

- **Fecha:** 2026-08-10
- **Estado:** Aprobado (diseño)
- **Alcance:** Buscar códigos CABYS (por texto libre o código exacto) contra la API pública
  de Hacienda desde el formulario de producto, elegir la coincidencia correcta entre varias
  y aplicar CABYS + descripción + impuesto de venta sugerido, siempre con confirmación
  explícita del usuario.

---

## 1. Contexto

El módulo `l10n_cr_fe_crlibre` ya tiene un campo `l10n_cr_fe_cabys` en `product.template`
([product_template.py](../../../addons/l10n_cr_fe_crlibre/models/product_template.py)) que solo
valida el formato (13 dígitos), sin verificar que el código exista en el catálogo de Hacienda ni
que la tarifa de IVA del producto en Odoo coincida con la que Hacienda tiene registrada para ese
código.

Al usar el sistema en el ambiente sandbox de Hacienda, apareció una advertencia (código -300) que
recuerda que la tarifa reducida del 1% solo aplica a productos de la Canasta Básica Tributaria o a
insumos agropecuarios respaldados con inscripción MAG del comprador. Investigando cómo evitar ese
tipo de inconsistencias se confirmó que Hacienda expone una API pública y sin autenticación para
consultar su catálogo CABYS:

- `GET https://api.hacienda.go.cr/fe/cabys?codigo=<13 dígitos>` — búsqueda por código exacto.
- `GET https://api.hacienda.go.cr/fe/cabys?q=<texto>` — búsqueda por descripción (mínimo 3
  caracteres), devuelve varias coincidencias.

Ambos endpoints se probaron manualmente y devuelven JSON con `codigo`, `descripcion`, `impuesto`
(tarifa de IVA) y `categorias` por cada resultado.

Los productos en este sistema se agregan uno por uno a mano (no hay importación masiva), lo que
hace viable una interacción manual por producto en vez de un proceso de sincronización batch.

**Decisión de diseño clave:** el sistema nunca asigna CABYS ni impuesto de forma automática/
silenciosa. La descripción de un producto puede coincidir con varias categorías del catálogo
(ej. "aguacate" puede ser fresco, procesado, con o sin cáscara, cada uno con código y tarifa
distintos) y la responsabilidad legal de elegir el código correcto es del contribuyente. El
sistema solo debe facilitar la búsqueda; la selección final siempre la hace una persona.

---

## 2. Objetivo y definición de "hecho"

Desde el formulario de un producto, un botón "Buscar CABYS" abre un asistente donde el usuario:

1. Escribe una búsqueda (texto libre, ej. "Aguacate Hass", o un código de 13 dígitos).
2. Ve una lista de coincidencias con descripción, código CABYS e IVA%.
3. Selecciona la fila correcta y confirma.
4. El producto queda con `l10n_cr_fe_cabys` y una nueva descripción oficial guardados, y con el
   impuesto de venta (`taxes_id`) ajustado a la tarifa que reporta Hacienda, si existe un
   `account.tax` de venta con esa tarifa configurado en la empresa.

**Éxito =** un producto de prueba, buscado por texto, muestra varias coincidencias reales de
Hacienda; al seleccionar una y confirmar, el producto queda con el CABYS, la descripción y el
impuesto de venta correctos.

---

## 3. Arquitectura

```
┌──────────────────────┐   click "Buscar CABYS"   ┌───────────────────────────┐
│ product.template      │ ───────────────────────▶ │ l10n_cr.fe.cabys.wizard   │
│ (formulario producto)│                            │ (TransientModel)         │
└──────────────────────┘                            └───────────┬───────────────┘
                                                                  │ buscar(query)
                                                                  ▼
                                                     ┌───────────────────────────┐
                                                     │ l10n_cr.fe.cabys.client   │
                                                     │ (AbstractModel, HTTP)     │
                                                     └───────────┬───────────────┘
                                                                  │ GET
                                                                  ▼
                                                     https://api.hacienda.go.cr/fe/cabys
```

Al confirmar una selección en el wizard, este escribe directamente sobre el `product.template`
que lo abrió (identificado por `active_id` en el contexto de la acción).

---

## 4. Componentes

### 4.1 `models/cabys_client.py` — `l10n_cr.fe.cabys.client` (`AbstractModel`)

Cliente HTTP dedicado a la API pública de Hacienda, separado de `l10n_cr.fe.client` (el cliente de
CRLibre) porque es un servicio distinto, con su propio host fijo (no varía por ambiente
sandbox/producción, a diferencia de CRLibre).

- `buscar(self, query)`:
  - Si `query` coincide con `^\d{13}$` → llama `GET /fe/cabys?codigo=<query>`.
  - En caso contrario → llama `GET /fe/cabys?q=<query>` (requiere mínimo 3 caracteres; si el
    texto es más corto, lanzar `CabysApiError` antes de llamar a la API).
  - Normaliza la respuesta a una lista de diccionarios `{codigo, descripcion, impuesto}`,
    independientemente de si la API respondió una lista simple (búsqueda por código) o un objeto
    con `cabys: [...]` (búsqueda por texto).
  - Lista vacía es una respuesta válida (sin coincidencias), no un error.
- URL base fija: `https://api.hacienda.go.cr/fe/cabys` (constante en el módulo, no en
  `ir.config_parameter`, porque no varía por empresa ni ambiente).
- Timeout razonable (ej. 15s). Sin lógica de reintentos (a diferencia de `CrlibreFeClient`, cuyos
  reintentos existen por la inestabilidad conocida del sandbox local de CRLibre; no aplica aquí).
- Excepción propia `CabysApiError` para: timeout, conexión rechazada, HTTP≠200, cuerpo no-JSON.

### 4.2 `wizards/cabys_wizard.py` — `l10n_cr.fe.cabys.wizard` (`TransientModel`)

Campos:
- `query` — `Char`, texto de búsqueda escrito por el usuario.
- `product_id` — `Many2one('product.template')`, precargado desde `active_id` al abrir el
  asistente.
- `result_ids` — `One2many` a un modelo transitorio auxiliar (o campo `Selection`/lista serializada
  en memoria; se decide el mecanismo concreto en el plan de implementación) que representa cada
  coincidencia devuelta: `codigo`, `descripcion`, `impuesto`.
- `selected_result_id` — referencia a la fila elegida por el usuario.

Métodos:
- `action_buscar(self)` — llama a `l10n_cr.fe.cabys.client.buscar(self.query)`, puebla
  `result_ids`. Si la API falla, muestra el error de forma legible sin cerrar el asistente
  (el usuario puede corregir la búsqueda y reintentar). Si no hay coincidencias, mensaje
  "No se encontraron coincidencias para esta búsqueda."
- `action_confirmar_seleccion(self)`:
  1. Requiere que `selected_result_id` esté definido (si no, error de validación).
  2. Escribe en `product_id`: `l10n_cr_fe_cabys` = código elegido,
     `l10n_cr_fe_cabys_descripcion` = descripción elegida.
  3. Busca `account.tax` con `type_tax_use='sale'`, `amount=<impuesto elegido>`,
     `company_id=env.company` (mismo patrón que `_l10n_cr_fe_xml_find_tax` en
     [account_move.py:334](../../../addons/l10n_cr_fe_crlibre/models/account_move.py#L334), pero
     para venta en vez de compra).
     - Si existe un único resultado → se asigna a `product_id.taxes_id`.
     - Si no existe → `taxes_id` se deja sin tocar; se postea un aviso (mensaje de retorno /
       notificación, no bloqueante) indicando la tarifa que Hacienda reporta y que falta
       configurar un impuesto de venta de esa tarifa en Odoo.
  4. Cierra el asistente.

### 4.3 `models/product_template.py` — cambios

- Campo nuevo `l10n_cr_fe_cabys_descripcion` — `Char`, `readonly=True`. Descripción oficial de
  Hacienda para el código CABYS asignado.
- Botón "Buscar CABYS" que abre `l10n_cr.fe.cabys.wizard` con `context={'default_product_id':
  active_id}`.

### 4.4 Vistas

- `views/product_template_views.xml`: botón junto al campo `l10n_cr_fe_cabys` existente; el nuevo
  campo `l10n_cr_fe_cabys_descripcion` visible como readonly al lado.
- `wizards/cabys_wizard_views.xml`: formulario del asistente con campo de búsqueda, botón
  "Buscar", lista de resultados (descripción, código, IVA%) con selección de una fila, y botones
  "Usar este código" / "Cancelar".

---

## 5. Manejo de errores

- API de Hacienda caída, timeout o conexión rechazada → mensaje claro dentro del asistente; el
  usuario puede reintentar sin perder el texto ya escrito. No afecta el producto.
- Búsqueda sin resultados → mensaje informativo, no es un error técnico.
- Búsqueda por texto con menos de 3 caracteres → validación local antes de llamar a la API,
  mensaje pidiendo ampliar el texto.
- Tarifa de IVA sin `account.tax` de venta configurado en Odoo → **no bloquea** la asignación de
  CABYS y descripción (esos datos ya son correctos y verificados contra Hacienda); solo se avisa
  que falta configurar el impuesto correspondiente. `taxes_id` queda como estaba.

---

## 6. Estrategia de pruebas

`TransactionCase` mockeando `l10n_cr.fe.cabys.client` (mismo patrón que
[test_consultar_estado_fe.py](../../../addons/l10n_cr_fe_crlibre/tests/test_consultar_estado_fe.py)):

1. Búsqueda por texto libre devuelve varias coincidencias, se listan correctamente.
2. Búsqueda por código exacto (13 dígitos) devuelve una coincidencia.
3. Confirmar una selección aplica `l10n_cr_fe_cabys`, `l10n_cr_fe_cabys_descripcion` y `taxes_id`
   en el producto cuando existe un impuesto de venta con esa tarifa.
4. Confirmar una selección cuya tarifa no tiene impuesto de venta configurado: CABYS y
   descripción se guardan, `taxes_id` no cambia, se muestra el aviso.
5. Error de red durante la búsqueda: mensaje legible, el asistente no se cierra.
6. Búsqueda sin resultados: mensaje informativo, sin resultados seleccionables.
7. Confirmar sin haber seleccionado ninguna fila: error de validación.

---

## 7. Limitaciones y consideraciones

1. **No valida vigencia histórica.** Se consulta el catálogo vigente al momento de la búsqueda;
   si el código queda obsoleto más adelante, este asistente no lo detecta retroactivamente (fuera
   de alcance: una revisión periódica de códigos ya asignados).
2. **Dependencia de un servicio externo en tiempo real.** Si `api.hacienda.go.cr` está caído, la
   búsqueda no funciona; no hay catálogo local de respaldo en esta fase.
3. **Planes de cuentas sin todas las tarifas.** El template `l10n_cr` solo trae el impuesto de
   venta del 13% (ver
   [account.tax-cr.csv](../../../addons/l10n_cr/data/template/account.tax-cr.csv)); es esperable
   que el aviso de "falta configurar el impuesto" aparezca seguido para productos de tarifa
   reducida (1%, 2%, 4%) hasta que la empresa cree esos impuestos.

---

## 8. Fuera de alcance (fases futuras)

- Integración con `/fe/agropecuario` para validar inscripción MAG del receptor (resuelve el
  mensaje -300 de forma completa, es un problema distinto: validación por factura/cliente, no de
  catálogo de producto).
- Uso de CABYS en el mapeo de la factura al generarla/enviarla a Hacienda.
- Sincronización o re-verificación masiva de productos ya existentes.
- Historial o favoritos de búsquedas CABYS.
