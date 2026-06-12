# UNIVERSIDAD NACIONAL DE SAN AGUSTÍN DE AREQUIPA

**FACULTAD DE INGENIERÍA DE PRODUCCIÓN Y SERVICIOS**

**ESCUELA PROFESIONAL DE INGENIERÍA DE SISTEMAS**

**CURSO:** INGENIERÍA DE PROCESOS Y SERVICIOS

**TEMA:** HITO 1 - ODOO

**DOCENTE:** RAMIREZ OSCAR

**GRUPO - INTEGRANTES:**
- Apaza Anahua Roydan Artemio
- Quiñonez Delgado Aarón Fernando
- Sencia Ale Bryan Daniel
- Sivincha Machaca Saul Andre
- Yauli Merma Diego Raul

AREQUIPA - PERÚ
2026

---

umbral vigente sin permitir modificaciones accidentales desde el formulario.

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <record id="view_order_form_inherit_discount" model="ir.ui.view">
    <field name="name">sale.order.form.inherit.discount</field>
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="sale.view_order_form"/>
    <field name="arch" type="xml">
      <xpath expr="//field[@name='note']" position="before">
        <group string="CONTROL DE DESCUENTOS" name="control_descuentos">
          <field name="descuento_maximo_permitido" readonly="1"/>
        </group>
      </xpath>
    </field>
  </record>
</odoo>
```

La verificación funcional confirmó que el formulario mostraba el valor 15.00 sobre el área de términos y condiciones. La extensión conservó la vista original y añadió únicamente el componente requerido.

## Aseguramiento de calidad

La estrategia de pruebas se aplicó sobre los puntos de entrada create, write y action_confirm del ORM. Los casos cubrieron valores inferiores, iguales y superiores al límite; cambios de descuento en líneas existentes; pedidos con múltiples productos; y aislamiento respecto de transacciones que no incumplían la regla.

| Categoría | Escenario | Resultado esperado |
|---|---|---|
| Límite inferior | Descuento menor a 15.0% | La confirmación continúa. |
| Límite exacto | Descuento igual a 15.0% | La confirmación continúa. |
| Límite excedido | Descuento de 15.1% o más | El pedido requiere revisión y se informa al usuario. |
| Actualización | Una línea existente cambia a un valor inválido | La validación detecta el nuevo valor. |
| Múltiples líneas | Solo una línea supera el umbral | El pedido completo queda retenido. |
| Aislamiento | Otros pedidos cumplen la política | No se producen efectos colaterales. |

La ejecución registrada el 8 de junio de 2026 a las 12:21 comprendió 15 pruebas de posinstalación. El reporte indicó cero fallas, cero errores y una tasa de aprobación del 100%. Estos resultados respaldan el comportamiento esperado del estado requires_review y de la excepción emitida durante la confirmación.

## Discusión

La secuencia entre ambos sprints fue técnicamente consistente. El análisis del Sprint 1 identificó action_confirm como un punto apropiado para incorporar controles previos a la confirmación. El Sprint 2 convirtió esa observación en una extensión funcional, acompañada por una vista informativa y pruebas automatizadas. De este modo, la implementación se apoyó en el conocimiento arquitectónico obtenido previamente y evitó modificar directamente el código del módulo sale.

La contenedorización facilitó la reproducibilidad del entorno, mientras que GitHub Actions trasladó una parte de la verificación a un agente remoto. Sin embargo, la comprobación del puerto constituye principalmente una prueba de humo de infraestructura. En iteraciones posteriores conviene ejecutar también la suite de pruebas de Odoo dentro del pipeline, registrar cobertura y comprobar migraciones del módulo.

La regla actual retiene cualquier pedido que excede el umbral, pero un flujo productivo debería considerar permisos, aprobadores, auditoría de cambios y configuración por compañía o categoría comercial. También debe verificarse cuidadosamente el efecto transaccional de escribir el estado antes de lanzar UserError, debido a que Odoo puede revertir operaciones dentro de la misma transacción. Una implementación madura puede requerir un flujo explícito de solicitud y aprobación en lugar de depender únicamente de una excepción.

## Conclusiones

El Sprint 1 produjo una base de trabajo reproducible y un análisis suficiente de las dependencias, modelos, estados, métodos y vistas del módulo de Ventas. Esta preparación permitió seleccionar un punto de extensión compatible con el framework.

El Sprint 2 implementó un producto mínimo viable que combina lógica de servidor, interfaz XML, seguimiento ágil, integración continua y pruebas automatizadas. La suite reportó 15 pruebas aprobadas, sin fallas ni errores, y el pipeline remoto confirmó la disponibilidad del servicio contenedorizado.

La herencia de modelos y vistas permitió incorporar la regla de descuento sin alterar el núcleo de Odoo. Para el Sprint 3 se recomienda integrar las pruebas funcionales al pipeline, formalizar el flujo de aprobación, revisar el comportamiento transaccional del estado de revisión y ampliar la parametrización del límite comercial.

## Referencias

Apaza Anahua, R. A. (2026). odooIPS [Código fuente]. GitHub. https://github.com/roydanpe/odooIPS

Docker, Inc. (2026). Docker [Software de computadora]. https://www.docker.com/

GitHub, Inc. (2026). GitHub Actions [Servicio de integración continua]. https://github.com/features/actions

Odoo S.A. (2026). Odoo source code (Versión 19.0) [Código fuente]. GitHub. https://github.com/odoo/odoo

---

## Apéndice A — Evidencias visuales del Sprint 1

**Figura 1** — Evidencia técnica del Sprint 1 (image1.png)
*Mapeo de Dependencias: Módulo `sale` de Odoo y sus Integraciones (Hito 2 - Análisis Sprint 1)*
- Módulo `sales_team` (Gestión de Equipos de Venta) → Módulo `sale` de Odoo (Núcleo)
- Módulo `sale` → Módulo `utm` (Rastreo de Campañas)
- Módulo `sale` → account_payment Module (Integración de Pagos y Facturación) → Módulo `account` (Núcleo de Contabilidad), Módulo `payment` (Pasarelas de Pago/Tokens), Módulo `portal` (Vista del Portal del Cliente)
*Mapeo de Arquitectura Conceptual - Hito 2 IPS 2025-A*

**Figura 2** — Evidencia técnica del Sprint 1 (image2.png)
```
roydan2404@roydan2404-HP-250-G7-Notebook-PC:~/odooIPS$ git branch -m feature/roydan-configuracion-entorno
roydan2404@roydan2404-HP-250-G7-Notebook-PC:~/odooIPS$ git branch
  19.0
* feature/roydan-configuracion-entorno
```

**Figura 3** — Evidencia técnica del Sprint 1 (image3.png)
```
roydan2404@roydan2404-HP-250-G7-Notebook-PC:~/odooIPS/docker-config$ docker compose ps
NAME                  IMAGE          COMMAND                  SERVICE  CREATED         STATUS         PORTS
docker-config-db-1    postgres:15    "docker-entrypoint.s…"   db       4 minutes ago   Up 4 minutes   5432/tcp
docker-config-web-1   odoo:19.0      "/entrypoint.sh odoo"    web      4 minutes ago   Up 43 seconds  0.0.0.0:8069->8069/tcp, [::]:8069->8069/tcp, 8071-8072/tcp
```

**Figura 4** — Evidencia técnica del Sprint 1 (image4.png)
Formulario de creación de base de datos de Odoo:
- Master Password: ••••••••••••
- Database Name: odoo_ventas
- Email: admin
- Password: admin
- Phone Number: (vacío)
- Language: Spanish / Español
- Country: Peru
- Demo Data: ✓ (marcado)
- Botones: "Create database" | "or restore a database"

**Figura 5** — Evidencia técnica del Sprint 1 (image5.png)
*Diagrama de estados del flujo de Odoo (sale.order):*
- Inicialización (Estado por defecto) → **draft** (Presupuesto)
- draft --action_quotation_send()\n(Envío de cotización)--> **sent** (Cotizacion_Enviada)
- draft --action_confirm()\n(Confirmación directa)--> **sale** (Pedido_de_Venta)
- sent --action_confirm()\n(Aceptación del cliente)--> **sale** (Pedido_de_Venta)
- sent --action_cancel()\n(Anulación)--> **cancel** (Cancelado)
- draft --action_cancel()--> **cancel** (Cancelado)
- sale --_action_cancel()\n(Cancela facturas borrador e inhabilita)--> **cancel** (Cancelado)
- cancel --action_draft()\n(Establecer como presupuesto)--> **draft**

**Figura 6** — Evidencia técnica del Sprint 1 (image6.png)
```
roydan2404@roydan2404-HP-250-G7-Notebook-PC:~/odooIPS/docker-config$ docker compose up -d
[+] Running 2/2
 ✓ Container docker-config-db-1   Running   0.0s
 ✓ Container docker-config-web-1  Started   0.8s
```

**Figura 7** — Evidencia técnica del Sprint 1 (image7.png)
*Diagrama de relación entre sale_order_views.xml (Vista Formulario) y sale_order.py (Modelo sale.order):*
- `<button name='action_confirm' state='draft'>` y `<button name='action_confirm' state='sent'>` → Disparo type='object' → 
- `@api.depends('amount_total')` `def _compute_partner_credit_warning(self)` → Inyección reactiva de datos → `<div class='alert alert-warning' invisible='partner_credit_warning == empty'>`
- `def action_confirm(self)` → Invoca pipeline interno → `def _action_confirm(self)` ⚡ HOOK DE EXTENSIÓN PARA MEJORAS

**Figura 8** — Evidencia técnica del Sprint 1 (image8.png)
*Diagrama Conceptual de Entidad-Relación (DER) — Modelo `sale.order` y Conexiones Clave (Odoo - IPS 2026-A)*

- **res.company (Compañía)**: ID, name (Nombre) — relación Many-to-One con sale.order
- **res.partner (Cliente/Proveedor)**: ID, name (Nombre), email, vat (RUC/DNI) — relación Many-to-One con sale.order
- **sale.order (Orden de Venta)**: ID, name (Clave Primaria/Referencia), date_order (Fecha de Orden), state (Estado), partner_id (FK Cliente), company_id (FK Compañía), user_id (FK Vendedor), amount_total (Monto Total)
- **res.users (Usuario/Vendedor)**: ID, login (Usuario), partner_id (FK Nombre Comercial) — relación Many-to-One con sale.order
- **sale.order.line (Línea de Pedido)**: ID, order_id (FK Orden de Venta), product_id (FK Producto), name (Descripción), product_uom_qty (Cantidad Ordered), price_unit (Precio Unitario), discount (Descuento) — relación One to Many con sale.order
- **account.move (Asiento/Factura Contable)**: ID, name (N° Asiento/Factura), move_type (Tipo de Movimiento), amount_total (Monto Facturado) — relación Many-to-Many con sale.order

---

## Apéndice B — Evidencias visuales del Sprint 2

**Figura 9** — Evidencia técnica del Sprint 2 (image1.png)
```
.../feature/origin/feature/roydan-configuracion-entorno
roydan2404@roydan2404-HP-250-G7-Notebook-PC:~/odooIPS$ git checkout 19.0
Cambiado a rama '19.0'
Tu rama está actualizada con 'origin/19.0'.
roydan2404@roydan2404-HP-250-G7-Notebook-PC:~/odooIPS$ git status
En la rama 19.0
Tu rama está actualizada con 'origin/19.0'.

nada para hacer commit, el árbol de trabajo está limpio
roydan2404@roydan2404-HP-250-G7-Notebook-PC:~/odooIPS$ git pull origin 19.0
remote: Enumerating objects: 1, done.
remote: Total 1 (delta 0), reused 0 (delta 0), pack-reused 1 (from 1)
Desempaquetando objetos: 100% (1/1), 922 byte | 461.00 KiB/s, listo.
Desde https://github.com/roydanpe/odooIPS
 * branch              19.0       -> FETCH_HEAD
   a7c056f8504..8c877c0bad0  19.0     -> origin/19.0
Actualizando a7c056f8504..8c877c0bad0
...
```

**Figura 10** — Evidencia técnica del Sprint 2 (image2.png)
GitHub Actions — Workflow "main.yml" (on: push)
- Triggered via push 3 minutes ago
- SenciaAleBryanDaniel pushed -> 66a9902 feature/daniel-cicd-github-...
- Status: Success | Total duration: 1m 47s | Artifacts: –
- Job: build-and-validate ✓ (1m 44s)

**Figura 11** — Evidencia técnica del Sprint 2 (image3.png)
✅ feat: configurar GitHub Actions CI para Docker Compose
CI - Validar Entorno Docker Compose #1: Commit 66a9902 pushed by SenciaAleBryanDaniel
Rama: feature/daniel-cicd-github-...

**Figura 12** — Evidencia técnica del Sprint 2 (image4.png)
Vista de pedido de venta (antes de aplicar descuento alto):
- Estado: Presupuesto / Presupuesto enviado / **Pedido de venta**
- Producto: [FURN_0002] Alfombrilla de escritorio | Cantidad: 100,00 | Precio unitario: 10,00 | Desc.%: 10,00 | Importe: $900,00

Segunda tabla (estado Pedido de venta):
- Producto: [FURN_0002] Alfombrilla de escritorio | Cantidad: 100,00 | Entregado: 0,00 | Facturado: 0,00 | Precio unitario: 10,00 | Desc.%: 10,00 | Importe: $900,00
- Botones: Crear factura, Enviar, Vista previa, Cancelar

**Figura 13** — Evidencia técnica del Sprint 2 (image5.png)
(Misma vista que la Figura 12, repetida)
- Estado: Presupuesto > Presupuesto enviado > Pedido de venta
- Producto: [FURN_0002] Alfombrilla de escritorio | Cantidad: 100,00 | Precio unitario: 10,00 | Desc.%: 10,00 | Importe: $900,00
- Segunda tabla: Cantidad 100,00 | Entregado 0,00 | Facturado 0,00 | Precio unitario 10,00 | Desc.% 10,00 | Importe $900,00

**Figura 14** — Evidencia técnica del Sprint 2 (image6.png)
Vista con descuento elevado (15,10%):
- Producto: [FURN_0002] Alfombrilla de escritorio | Cantidad: 100,00 | Precio unitario: 10,00 | Desc.%: 15,10 | Importe: $849,00

Modal de error mostrado:
> **Operación no válida**
> ¡Alerta de Control (MVP)! Este pedido supera el 15% de descuento permitido. El presupuesto ha sido retenido en estado 'Requiere Revisión' para la aprobación de Diego.
> [Cerrar]

**Figura 15** — Evidencia técnica del Sprint 2 (image8.png)
Sección "CONTROL DE DESCUENTOS" en el formulario:
- Descuento Máximo Permisible (%): **15.00**

**Figura 16** — Evidencia técnica del Sprint 2 (image9.png)
*Evidencia 9 - Resultado final real reportado por Odoo*
```
2026-06-08 17:10:27,309 INFO odooips_qa_tests_ieee 15 post-tests in 0.75s, 1007 queries
2026-06-08 17:10:27,310 INFO odooips_qa_tests_ieee validacion_descuento_maximo: 17 tests 0.69s
2026-06-08 17:10:27,310 INFO odooips_qa_tests_ieee 0 failed, 0 error(s) of 15 tests
2026-06-08 17:10:27,316 INFO odoo.sql_db: ConnectionPool Closed 1 connections
```
Interpretación: suite backend aprobada sin fallos ni errores.

**Figura 17** — Evidencia técnica del Sprint 2 (image10.png)
Tablero Kanban:
- **Todo (POR HACER)** — 0 ítems — "This item hasn't been started"
- **In Progress** — 2 ítems — "This is actively being worked on"
  - odooIPS #45 — [Sprint 2] Gestión: Coordinación del Sprint, control de Kanban y consolidación de informe
  - odooIPS #44 — [Sprint 2] QA & Docs: Ejecución de pruebas funcionales y consolidación de evidencias
- **Done** — 5 ítems — "This has been completed"
  - odooIPS #36 — Modulo de compras
  - odooIPS #35 — Modulo ventas
  - odooIPS #37 — Issues
  - odooIPS #41 — [Sprint 2] Backend: Extender modelos e implementación de funcionalidad base
  - odooIPS #42 — [Sprint 2] DevOps: Configuración de GitHub Actions y validación de Docker

**Figura 18** — Evidencia técnica del Sprint 2 (image11.png)
**Hito 2 - Sprint 2** (GitHub Milestone)
- Estado: Open | Due by June 9, 2026 · Last updated 3 minutes ago
- 100% complete
- Open: 0 | Closed: 5
  - [Sprint 2] Backend: Extender modelos e implementación de funcionalidad base — #41 by aaronQuinonez was closed 2 days ago
  - [Sprint 2] DevOps: Configuración de GitHub Actions y validación de Docker — #42 by aaronQuinonez was closed 19 hours ago
  - [Sprint 2] Frontend: Modificación de vistas XML e integración de interfaz — #43 by aaronQuinonez
  - [Sprint 2] QA & Docs: Ejecución de pruebas funcionales y consolidación de evidencias — #44 by aaronQuinonez was closed 18 minutes ago
  - [Sprint 2] Gestión: Coordinación del Sprint, control de Kanban y consolidación de informe — #45 by aaronQuinonez was closed 18 minutes ago

**Figura 19, 20 y 21** — Evidencia de reuniones
- Captura de videollamada (10:30 p.m., key-bneb-ckw) con participantes: Bryan Daniel Sencia Ale, Diego Raul Yauli Merma, Aaron Fernando Quiñonez De..., Roydan Artemio Apaza Anahua.
- Captura de videollamada (7:20 p.m., key-bneb-ckw) con Saul Andre Sivincha Machaca presentando y anotando, junto con Diego Raul Yauli Merma, Aaron Fernan..., Roydan Artemi..., Bryan Daniel S...
- Captura de videollamada móvil (9:31 p.m.) con Saul Andre presentando y anotando, junto a otros participantes (2 más).

**Figura 22** — Evidencia de reunión grupal en la hora de clases
Fotografía de los integrantes del grupo trabajando juntos en el salón de clases, frente a una laptop.
