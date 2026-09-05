# UNIVERSIDAD NACIONAL DE SAN AGUSTÍN DE AREQUIPA

**Facultad de Ingeniería de Producción y Servicios**
**Escuela Profesional de Ingeniería de Sistemas**

**Curso:** Ingeniería de Procesos y Servicios
**Tema:** Hito 1 - Odoo
**Docente:** Ramirez Oscar

**Integrantes:**
- Apaza Anahua Roydan Artemio
- Quiñonez Delgado Aarón Fernando
- Sencia Ale Bryan Daniel
- Sivincha Machaca Saul Andre
- Yauli Merma Diego Raul

Arequipa - Perú, 2026

---

# Informe de Sprint 1 — Mejoras al Módulo de Ventas de Odoo

## Resumen del Proyecto

El Sprint 1 tuvo como objetivo preparar la base técnica y organizativa del proyecto para el desarrollo posterior de mejoras en el módulo de **Ventas (sale)** de Odoo. Durante este período, el equipo se enfocó en comprender la arquitectura del sistema, configurar el entorno de trabajo local, organizar el Product Backlog y definir las tareas iniciales que serían implementadas en los siguientes sprints.

Como parte de las actividades realizadas:

- Se configuró el entorno de ejecución utilizando **Docker Compose**.
- Se analizó la estructura funcional y técnica del módulo `sale`.
- Se identificaron posibles oportunidades de mejora.
- Se organizaron las tareas mediante **GitHub Projects e Issues**.
- Se documentó la arquitectura del módulo seleccionado.
- Se establecieron las ramas de trabajo necesarias para el desarrollo colaborativo.

---

## Tabla de Contenido

1. [Configuración del Entorno](#1-configuración-del-entorno)
2. [Documentación de Arquitectura — Análisis de Dependencias](#2-documentación-de-arquitectura--análisis-de-dependencias)
3. [Análisis de Arquitectura del Software: Modelo `sale.order`](#3-análisis-de-arquitectura-del-software-modelo-saleorder)
4. [Análisis de Arquitectura del Software: Vistas e Interfaz de Usuario (XML)](#4-análisis-de-arquitectura-del-software-vistas-e-interfaz-de-usuario-xml)

---

## 1. Configuración del Entorno

**Objetivo:** configurar Odoo, PostgreSQL y Docker Compose; verificar la ejecución local y resolver problemas de despliegue inicial.

### Etapa 1 — Preparación del sistema (Ubuntu)

En la terminal de Ubuntu se realizaron los siguientes pasos:

1. Actualización de los paquetes del sistema:

   ```bash
   sudo apt update
   ```

2. Instalación de Docker y Docker Compose:

   ```bash
   sudo apt install docker.io docker-compose -y
   ```

3. Asignación de permisos al usuario para no requerir `sudo` en cada comando de Docker:

   ```bash
   sudo usermod -aG docker $USER
   ```

Luego se reinició el sistema para aplicar los cambios.

### Etapa 2 — Clonado del repositorio y configuración de Docker Compose

1. Clonado del repositorio en la rama `19.0`:

   ```bash
   git clone -b 19.0 https://github.com/roydanpe/odooIPS.git
   ```

2. Acceso al directorio del proyecto:

   ```bash
   cd odooIPS
   ```

3. Creación de la rama de trabajo:

   ```bash
   git checkout -b feature/roydan-configuracion-entorno
   ```

   Verificación de la rama activa:

   ![Creación y verificación de rama en Git](assets/01-git-branch.png)

4. Edición del archivo `docker-config/docker-compose.yml` con la siguiente configuración:

   ```yaml
   services:
     # Servicio 1: El motor de Base de Datos (PostgreSQL)
     db:
       image: postgres:15
       environment:
         - POSTGRES_DB=postgres
         - POSTGRES_USER=odoo
         - POSTGRES_PASSWORD=odoo
       volumes:
         - odoo-db-data:/var/lib/postgresql/data
       networks:
         - odoo-network

     # Servicio 2: El sistema ERP (Odoo v19.0)
     web:
       image: odoo:19.0
       depends_on:
         - db
       ports:
         - "8069:8069"
       volumes:
         - odoo-web-data:/var/lib/odoo
         - ../addons:/mnt/extra-addons
       environment:
         - HOST=db
         - USER=odoo
         - PASSWORD=odoo
       networks:
         - odoo-network

   volumes:
     odoo-web-data:
     odoo-db-data:

   networks:
     odoo-network:
       driver: bridge
   ```

5. Dentro de `docker-config`, se levantaron los contenedores en segundo plano (esto descarga PostgreSQL 15 y Odoo 19 automáticamente):

   ```bash
   docker compose up -d
   ```

   ![Salida de docker compose up -d](assets/02-docker-compose-up.png)

6. Verificación de que los contenedores estuvieran activos:

   ```bash
   docker compose ps
   ```

   ![Salida de docker compose ps](assets/03-docker-compose-ps.png)

   En la columna **STATUS**, ambos contenedores deben mostrar `Up` o `Running`.

### Etapa 3 — Configuración inicial en el navegador

1. Se accedió a `http://localhost:8069`, donde se mostró el formulario de creación de la base de datos de Odoo. Los campos se completaron de la siguiente manera para que todo el equipo cuente con los mismos accesos:

   - **Master Password:** código generado por defecto por Odoo (se guarda para uso futuro).
   - **Database Name:** `odoo_ventas`
   - **Email:** `admin`
   - **Password:** `admin`
   - **Language:** Español (PE) o Español
   - **Country:** Perú
   - **Demo Data:** activada — al habilitarla, Odoo se llena automáticamente con clientes, productos y ventas de prueba. Si no se activa, el sistema aparece vacío y los datos deben ingresarse manualmente.

   ![Formulario de creación de base de datos en Odoo](assets/04-odoo-db-setup.png)

2. Se hizo clic en **Create database** y se esperó a que el proceso finalizara.

---

## 2. Documentación de Arquitectura — Análisis de Dependencias

Como parte del **Hito 2 - Sprint 1** ("Análisis, backlog y configuración inicial"), y sobre la base del entorno Docker funcional, se auditó el archivo `__manifest__.py` del módulo de Ventas (`sale`) para trazar sus relaciones de interdependencia técnica con el ecosistema de Odoo.

### Hallazgos clave en `__manifest__.py`

Se extrajo la siguiente definición de la sección `depends`:

```python
'depends': [
    'sales_team',      # Para la gestión de equipos de ventas.
    'account_payment', # -> account, payment, portal
    'utm',             # Para el rastreo de campañas de marketing.
],
```

### Análisis de la red de dependencias

El análisis revela que el módulo de Ventas no es una entidad aislada, sino el núcleo de orquestación de un ecosistema complejo que integra datos maestros, operaciones financieras y vistas de cliente.

#### Dependencias directas

- **`sales_team`**: esencial para organizar a los vendedores en equipos, definir jerarquías y gestionar cuotas de ventas dentro de las órdenes.
- **`account_payment`**: la dependencia más crítica y compleja. Se encarga de la integración directa con el motor financiero para permitir el registro de cobros desde la orden de venta o la factura generada.
- **`utm`**: permite el rastreo de campañas de marketing (Urchin Tracking Module), asociando cotizaciones y ventas a fuentes específicas (origen, medio, campaña).

#### Dependencias transitivas (anidadas)

La dependencia con `account_payment` actúa como un "puente" que introduce automáticamente tres módulos fundamentales adicionales:

- **`account`**: núcleo de Contabilidad, necesario para generar facturas a partir de órdenes de venta confirmadas y registrar asientos contables.
- **`payment`**: gestiona las pasarelas de pago externas (tarjetas, PayPal) y los tokens de pago para transacciones seguras.
- **`portal`**: define la interfaz web del portal del cliente, donde se pueden visualizar cotizaciones y pagar facturas.

### Mapa de dependencias del módulo `sale`

![Mapeo de dependencias del módulo sale de Odoo](assets/05-dependencias-sale.png)

---

## 3. Análisis de Arquitectura del Software: Modelo `sale.order`

Este apartado consolida la auditoría técnica realizada sobre el backend del módulo de Ventas (`sale`), específicamente en sus componentes de persistencia de datos, control de estados y lógica de orquestación de procesos transaccionales.

### Pilar 1 — Estructura de persistencia y relaciones del modelo

El modelo `sale.order` actúa como la cabecera (orquestador central) de la transacción comercial. Su diseño de base de datos se fundamenta en relaciones clave con el núcleo del sistema:

- **Identidad y contexto**
  - `name` (Char): identificador único de la orden (llave primaria lógica), indexado mediante un algoritmo de *trigram* para búsquedas de texto eficientes a nivel de base de datos.
  - `company_id` (Many2one → `res.company`): garantiza el aislamiento de datos en entornos multi-compañía de forma nativa.

- **Vinculación comercial**
  - `partner_id` (Many2one → `res.partner`): llave foránea obligatoria hacia el maestro de clientes que realiza la compra.

- **Composición de líneas de detalle**
  - `order_line` (One2many → `sale.order.line`): relación de composición estructural. Una cabecera de orden de venta posee múltiples líneas de ítems donde se desglosan productos, precios y cantidades.

- **Acoplamiento contable financiero**
  - `invoice_ids` (Many2many → `account.move`): tabla intermedia que enlaza la orden con los documentos de facturación emitidos, permitiendo trazabilidad bidireccional entre ventas y contabilidad.
  - `invoice_status` (Selection): campo calculado dinámicamente (`store=True`) que evalúa si el pedido está listo para facturar, completamente facturado o si no requiere facturación.

### Diagrama Entidad-Relación (DER) del modelo `sale.order`

![Diagrama Entidad-Relación del modelo sale.order](assets/06-der-sale-order.png)

---

### Pilar 2 — Máquina de estados del flujo comercial

El ciclo de vida del documento está controlado por la constante `SALE_ORDER_STATE`. El campo `state` opera como una máquina de estados determinista que restringe o habilita acciones del usuario y procesos del backend de manera síncrona:

| Código del estado | Etiqueta del estado | Comportamiento e impacto en el sistema |
| --- | --- | --- |
| `draft` | Quotation (Presupuesto) | Estado inicial por defecto. El documento es editable. No afecta inventarios ni genera pasivos financieros. |
| `sent` | Quotation Sent (Enviado) | La propuesta comercial se compartió formalmente con el cliente. Bloquea ciertas propiedades de edición visual. |
| `sale` | Sales Order (Pedido Firme) | Estado transaccional crítico. La cotización es aceptada. Bloquea la edición básica y dispara eventos de reserva en el módulo de inventarios (`stock`). |
| `cancel` | Cancelled (Cancelado) | Estado de anulación. Revierte flujos y libera los documentos borrador enlazados. |

### Diagrama de la máquina de estados

![Diagrama de la máquina de estados del flujo comercial](assets/07-maquina-estados.png)

---

### Pilar 3 — Métodos clave de orquestación funcional

La lógica de negocio pesada y las transacciones entre módulos se ejecutan mediante tres métodos *core* que procesan los estados y los documentos financieros.

#### A. Cancelación síncrona — `_action_cancel`

Este método asegura la integridad referencial antes de dar de baja un pedido:

```python
def _action_cancel(self):
    inv = self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
    inv.button_cancel()
    return self.write({'state': 'cancel'})
```

**Lógica interna:** filtra todas las facturas enlazadas en la relación Many2many que aún se encuentren en estado `draft` y ejecuta de manera segura su cancelación (`button_cancel()`). Posteriormente, muta el estado del registro actual a `cancel`.

#### B. Motor de facturación — `_create_invoices`

Es un método extenso y crítico encargado de transformar datos desde el dominio de Ventas al dominio Contable (`account.move`). Su ejecución sigue un pipeline estructurado de 4 fases:

1. **Validación y preparación**: verifica los permisos de escritura/creación en el entorno contable (`has_access('create')`). Itera sobre las órdenes seleccionadas, ajusta el contexto de idioma (`lang`) y compañía (`with_company`), y extrae las líneas aptas para facturación (`_get_invoiceable_lines`).

2. **Gestión de anticipos (Down Payments)**: si detecta líneas marcadas como anticipos (`line.is_downpayment`), inyecta secciones especiales en la factura y revierte cantidades o bases impositivas utilizando funciones contables del núcleo fiscal, si se está emitiendo la factura final.

3. **Agrupamiento transaccional (`grouped`)**: si el parámetro `grouped` es `False`, el método ordena y agrupa múltiples órdenes de venta bajo claves comunes (mismo cliente, dirección de envío y moneda), unificando las líneas de detalle en una única factura consolidada para optimizar la emisión de documentos.

4. **Resecuenciación y conversión final**: si se agruparon documentos, reordena de forma segura la secuencia visual de las líneas para evitar colisiones. Finalmente, delega la creación física a `_create_account_invoices` y convierte automáticamente la factura en un documento de reembolso (nota de crédito) si el monto total resultante es negativo (`amount_total < 0`).

---

### Pilar 4 — Puntos de extensión de la arquitectura (hooks para mejoras)

El framework de Odoo provee *hooks* específicos en el código de `sale.order`. Estos son los puntos exactos donde el equipo puede inyectar las mejoras planificadas en el Sprint 0 de forma limpia y mantenible.

#### Hook A — Intercepción del flujo de confirmación (`action_confirm` y `_action_confirm`)

Cuando el usuario o un evento externo gatilla la confirmación de la venta, se invoca `action_confirm(self)`:

```python
def action_confirm(self):
    # ... validaciones iniciales
    for order in self:
        error_msg = order._confirmation_error_message()
        if error_msg:
            raise UserError(error_msg)
    # ... actualización de valores de confirmación
    self.with_context(context)._action_confirm()
    # ... bloqueo de orden y envío de correos
```

- **Propósito del hook:** antes de mutar el estado a `sale`, el método valida las distribuciones analíticas y los mensajes de error. Luego invoca la función interna `_action_confirm()`.
- **Aplicación de la mejora (validaciones adicionales):** este es el punto exacto para extender la lógica mediante herencia. El comentario de Odoo lo estipula explícitamente: este método debe extenderse cuando la confirmación deba generar otros documentos. Aquí es donde se debe programar la validación personalizada del equipo (por ejemplo, impedir la confirmación si no cumple con un control de stock estricto o un control de aprobaciones directivas).

#### Hook B — Control preventivo de riesgo comercial (`_compute_partner_credit_warning`)

Método calculado y reactivo que depende de cambios en variables críticas del modelo:

```python
@api.depends('company_id', 'partner_id', 'amount_total')
def _compute_partner_credit_warning(self):
    # ... lógica para evaluar el límite de crédito del cliente
```

- **Propósito del hook:** se dispara automáticamente cada vez que cambia la compañía, el cliente (`partner_id`) o el monto total del pedido (`amount_total`), siempre que el documento esté en estado preliminar (`draft` o `sent`).
- **Aplicación de la mejora (automatización de reglas de descuento / alertas):** al estar amarrado al cambio de `amount_total`, este decorador `@api.depends` expone la ventana arquitectónica idónea para inyectar auditorías de negocio en tiempo real, calculando si el monto actual califica para un descuento masivo automatizado o bloqueando visualmente la pantalla si el monto del pedido supera el límite financiero parametrizado para el cliente.

---

## 4. Análisis de Arquitectura del Software: Vistas e Interfaz de Usuario (XML)

El archivo `sale_order_views.xml` define la capa de presentación (UI) del módulo. Odoo utiliza una arquitectura basada en datos donde las vistas se registran en la base de datos PostgreSQL a través de registros `<record>` del modelo de metadatos `ir.ui.view`.

### 4.1 El ecosistema de multi-vistas de ventas

El sistema implementa un robusto modelo de representación visual múltiple para la misma entidad de datos (`sale.order`). Dependiendo del contexto transaccional o analítico, el framework renderiza distintos componentes de interfaz:

- **Vista de formulario (`form`)**: concentra la edición detallada, gestión de líneas de ítems y orquestación del flujo de trabajo de la orden.
- **Vista de lista (`list`)**: reemplaza estructuralmente a las antiguas vistas `tree`. Despliega registros tabulares masivos con soporte de agregaciones numéricas (`sum="Total Tax Included"`).
- **Vista Kanban (`kanban`)**: representación visual ágil por tarjetas, optimizada para flujos de trabajo móviles y pipelines comerciales.
- **Vistas analíticas (`pivot` y `graph`)**: proveen capacidades nativas de Business Intelligence (BI) para agrupar montos totales (`amount_total`) cruzados por dimensiones de tiempo o clientes (`partner_id`).
- **Vistas operativas (`calendar` y `activity`)**: vinculan los documentos comerciales a fechas límite y al sistema de hilos de actividades pendientes (`activity_ids`).

### 4.2 Anatomía de la vista formulario principal (`view_order_form`)

La arquitectura interna de la vista de formulario se divide en componentes jerárquicos de alta prioridad.

#### A. El encabezado de control de flujo (`<header>`)

Contiene la botonera operativa y el componente visual del pipeline (`statusbar`). Este bloque actúa como puente de disparo directo hacia los métodos del backend analizados en el pilar anterior:

```xml
<header>
    <button string="Create Invoice" id="create_invoice"
            name="%(sale.action_view_sale_advance_payment_inv)d"
            type="action" class="btn-primary"
            invisible="invoice_status != 'to invoice'"/>
    <button string="Confirm" id="action_confirm"
            name="action_confirm" type="object" class="btn-primary"
            invisible="state != 'sent'"/>
    <button string="Cancel" name="action_cancel" type="object"
            confirm="Are you sure..."
            invisible="state not in ['draft', 'sent', 'sale'] or not id or locked"/>
    <field name="state" widget="statusbar"
           statusbar_visible="draft,sent,sale"/>
</header>
```

#### B. Sistema de alertas dinámicas (banners condicionales)

Inmediatamente debajo del encabezado, el diseño arquitectónico sitúa un bloque de notificaciones reactivas. Estas alertas evalúan campos lógicos calculados en Python para renderizar advertencias críticas en pantalla:

- **Riesgo financiero**: el banner del campo `partner_credit_warning` aparece dinámicamente si el cliente excede su límite financiero en el sistema contable.
- **Consistencia de catálogo**: se despliega una alerta si la cotización contiene productos archivados o inactivos (`has_archived_products`).
- **Integridad documental**: advierte si el documento actual puede ser un duplicado de transacciones previas (`duplicated_order_ids`).

#### C. El bloque relacional compuesto: tabla de detalle (`order_line`)

El núcleo transaccional de la pantalla reside en la pestaña *Order Lines*. Utiliza un componente avanzado que empotra vistas internas (`<form>`, `<list>` y `<kanban>`) dedicadas exclusivamente a manipular el modelo One2many hacia las líneas de venta:

- **Modo de edición**: configurado como `editable="bottom"`, permitiendo inserción rápida en grilla sin abrir ventanas emergentes.
- **Lógica modular del sub-formulario**: controla dinámicamente qué campos mostrar según la naturaleza de la línea a través del atributo `display_type` (manejando variantes si la fila es un producto estándar, una sección organizativa o una nota de texto).
- **Hook para descuentos**: en la sección inferior derecha de las líneas se localiza el botón **Discount**, que invoca de forma nativa al asistente de cálculo masivo (`action_open_discount_wizard`), punto de anclaje visual para la automatización de reglas de precios propuesta por el equipo.

### 4.3 Matriz de trazabilidad: interfaz XML vs. métodos backend

| Componente XML (botón / campo) | Atributo `name` (destino) | Tipo de disparo (`type`) | Condición de visibilidad (`invisible`) | Propósito arquitectónico |
| --- | --- | --- | --- | --- |
| Botón "Confirm" | `action_confirm` | object (método Python) | `state != 'sent'` o `'draft'` | Gatilla la confirmación en firme del pedido comercial. |
| Botón "Cancel" | `action_cancel` | object (método Python) | Fuera de estados `draft`, `sent`, `sale` | Dispara la lógica interna de reversión contable y cancelación. |
| Botón "Create Invoice" | `sale.action_view_sale_advance_payment_inv` | action (ventana de asistente) | `invoice_status != 'to invoice'` | Despliega el asistente intermedio de creación de facturas. |
| Botón "Discount" | `action_open_discount_wizard` | object (asistente Python) | Si el pedido está bloqueado o cancelado | Invoca el wizard del sistema para inyectar descuentos. |
| Botón "Update Prices" | `action_update_prices` | object (método Python) | Si no hay cambios en tarifas o está confirmado | Recalcula la lista de precios de los productos en la grilla. |

### 4.4 Arquitectura de consultas y capa de búsqueda (`<search>`)

La vista `view_sales_order_filter` administra el motor de indexación de búsquedas y filtros rápidos de la plataforma. Su diseño está optimizado para segmentar las operaciones en base a las reglas de negocio:

- **Filtros predefinidos del dominio**: traduce requerimientos comerciales en cláusulas SQL directas mediante el atributo `domain` a nivel de cliente (por ejemplo, `domain="[('invoice_status','=','to invoice')]"` para aislar órdenes listas para su proceso contable).
- **Optimización de carga**: agrupa registros por criterios operacionales (vendedor, cliente, mes de orden) a través de los contextos nativos del framework `{'group_by': 'field_name'}`, disminuyendo el costo computacional de procesamiento en el cliente web.

### Mapa de trazabilidad: interfaz XML vs. código Python

![Mapa de trazabilidad entre la interfaz XML y el código Python](assets/08-trazabilidad-xml-python.png)

---

*Documentación correspondiente al Hito 2 — Sprint 1 (Análisis, backlog y configuración inicial) del proyecto de mejoras al módulo de Ventas de Odoo.*

## Referencias

- Apaza Anahua, R. A. (2026). *odooIPS* [Código fuente]. GitHub. https://github.com/roydanpe/odooIPS
- Docker, Inc. (2026). *Docker* [Software de computadora]. https://www.docker.com/
- GitHub, Inc. (2026). *GitHub Actions* [Servicio de integración continua]. https://github.com/features/actions
- Odoo S.A. (2026). *Odoo source code* (Versión 19.0) [Código fuente]. GitHub. https://github.com/odoo/odoo
