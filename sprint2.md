# Hito 2 - Sprint 2: Implementación Inicial e Integración CI/CD en Odoo

**Universidad Nacional de San Agustín de Arequipa**  
Facultad de Ingeniería de Producción y Servicios  
Escuela Profesional de Ingeniería de Sistemas  

**Curso:** Ingeniería de Procesos y Servicios  
**Docente:** Ramirez Oscar  

**Integrantes:**
- Apaza Anahua Roydan Artemio
- Quiñonez Delgado Aarón Fernando
- Sencia Ale Bryan Daniel
- Sivincha Machaca Saul Andre
- Yauli Merma Diego Raul

**Arequipa - Perú, 2026**

---

## Resumen

El presente documento expone los resultados de la ingeniería de software y automatización DevOps correspondientes al **Hito 2 - Sprint 2** sobre el sistema ERP open-source **Odoo (V19.0)**.

Durante este ciclo constructivo se priorizó el desarrollo del **Producto Mínimo Viable (MVP)** enfocado en la validación del descuento comercial máximo, implementado mediante herencia lógica de clases en el backend. Paralelamente, fue configurada e integrada una infraestructura de **integración continua (CI)** en GitHub Actions, la cual automatiza la compilación del entorno Docker Compose en la nube y ejecuta tareas dinámicas de verificación de red y puertos de servicios.

Adicionalmente, se diseñó y desplegó una batería automatizada de **15 pruebas funcionales y de regresión** sobre el ORM de Odoo, alcanzando un porcentaje de éxito total del **100%** libre de fallas y errores. Los frentes visuales de herencia de vistas XML fueron modificados de manera integrada en los formularios del presupuesto de ventas, lográndose una interfaz responsiva y reactiva que muestra de forma explícita las restricciones de los umbrales financieros de negocio.

---

## Introducción y Planificación del Sprint 2

### Contexto del Sprint

> 🔗 **Repositorio:** [https://github.com/roydanpe/odooIPS](https://github.com/roydanpe/odooIPS)

El progreso metodológico y técnico alcanzado durante el Hito 2 - Sprint 2 (*"Implementación inicial e integración CI/CD"*) es detallado en el presente informe para el proyecto de auditoría del ERP Odoo. Tras haberse consolidado el análisis arquitectónico inicial del módulo de ventas (`sale`) y el levantamiento local de contenedores mediante Docker Compose en el período anterior, la meta estratégica consistió en materializar la primera funcionalidad lógica del backlog y orquestar un pipeline DevOps completamente automatizado.

### Delimitación de Alcance

| Sprint | Descripción |
|--------|-------------|
| **Sprint 2** — Ciclo de Construcción Inicial | Codificación de la regla transaccional base en Python, control de excepciones nativas mediante cuadros de diálogo, suite de pruebas unitarias automatizadas a nivel de ORM y validación automática del build en GitHub Actions. |
| **Sprint 3** — Ciclo de Estabilización y Refactorización | Optimización avanzada de índices de bases de datos, flujos dinámicos de aprobación por jerarquías de usuarios y pulido fino de alertas reactivas en la interfaz de usuario. |

---

## Gestión Ágil del Proyecto

### Configuración del Tablero Kanban e Issues en GitHub Projects

El control de las actividades fue estructurado mediante GitHub Projects. Los tickets analíticos previos fueron migrados al estado de archivados, habilitando un espacio ágil para el seguimiento de la construcción actual. Se incorporaron **5 Issues de tipo "Blank Issue"**, definiendo de manera unívoca los criterios de aceptación y asignando formalmente las responsabilidades a los usuarios del repositorio remoto.

Las tarjetas progresan secuencialmente a través de los estados clásicos de Scrum:

```
To Do  →  In Progress  →  In Review  →  Done
```

**Issues del Sprint 2:**

| # | Issue | Estado |
|---|-------|--------|
| #36 | Módulo de compras | ✅ Done |
| #35 | Módulo ventas | ✅ Done |
| #37 | Issues | ✅ Done |
| #41 | [Sprint 2] Backend: Extender modelos e implementación de funcionalidad base | ✅ Done |
| #42 | [Sprint 2] DevOps: Configuración de GitHub Actions y validación de Docker | ✅ Done |
| #43 | [Sprint 2] Frontend: Modificación de vistas XML e integración de interfaz | ✅ Done |
| #44 | [Sprint 2] QA & Docs: Ejecución de pruebas funcionales y consolidación de evidencias |  ✅ Done  |
| #45 | [Sprint 2] Gestión: Coordinación del Sprint, control de Kanban y consolidación de informe |  ✅ Done  |

### Administración del Milestone

Un Milestone de control fue establecido en el repositorio con el identificador **"Hito 2 - Sprint 2"**, con fecha límite orientada al cierre de la iteración. Los 5 issues técnicos del ciclo fueron indexados directamente bajo este hito, permitiendo la monitorización automática del porcentaje de avance — alcanzando el **100% de completitud**.

### Facilitación de Daily Syncs

Fueron lideradas reuniones diarias breves de sincronización asíncrona para recopilar el estado de los componentes, identificar impedimentos y agilizar las transferencias de código entre integrantes. Gracias a este monitoreo continuo, se detectó de forma oportuna la culminación del módulo de backend, permitiendo coordinar de inmediato el inicio de la fase de aseguramiento de calidad (QA).

---

## Desarrollo Backend

### Regla Comercial del MVP

La regla comercial seleccionada para el MVP establece matemáticamente que ningún descuento asignado a una línea de pedido (*dᵢ*) puede quebrantar el umbral máximo parametrizado por defecto (**Dmax = 15.0%**):

$$d_i \leq D_{max}, \quad \forall \, d_i \in \text{order\_line}$$

### Sincronización de Entorno y Preparación de Ramas

Para garantizar el aislamiento seguro del software, se actualizó el entorno local respecto a la rama base `19.0` y se creó una rama de características dedicada:

```bash
git checkout 19.0
git pull origin 19.0
git checkout -b feature/roydan-backend-descuento
```

### Arquitectura de Archivos del Módulo Personalizado

```
/addons/validacion_descuento_maximo/
├── __init__.py
├── __manifest__.py
└── models/
    ├── __init__.py
    └── sale_order.py
```

### Codificación de la Lógica del Servidor

Se implementó herencia de clases sobre el modelo nativo `sale.order`, inyectando un nuevo estado `requires_review` e interceptando el método transaccional de confirmación mediante excepciones controladas (`UserError`):

```python
from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    descuento_maximo_permitido = fields.Float(
        string='Descuento Máximo Permisible (%)',
        default=15.0
    )

    state = fields.Selection(
        selection_add=[('requires_review', 'Requiere Revisión')],
        ondelete={'requires_review': 'set default'}
    )

    def action_confirm(self):
        for order in self:
            supera_limite = any(
                line.discount > order.descuento_maximo_permitido
                for line in order.order_line
            )
            if supera_limite:
                order.write({'state': 'requires_review'})
                raise UserError(
                    "¡Alerta de Control (MVP)! Este pedido supera el 15% de "
                    "descuento permitido. El presupuesto ha sido retenido en "
                    "estado 'Requiere Revisión' para la aprobación."
                )
        return super(SaleOrder, self).action_confirm()
```

### Despliegue Local y Pruebas Iniciales

Se ejecutó el reinicio de los contenedores Docker locales mediante `docker compose restart`. Tras activarse el modo desarrollador en el ERP y actualizarse el árbol de aplicaciones, se validó el correcto funcionamiento a través de **5 escenarios analíticos locales (PR-01 a PR-05)**:

- ✅ Descuentos ≤ 15% → transacción confirmada exitosamente.
- 🚫 Descuentos > 15% → estado cambia a `requires_review` y se dispara la alerta emergente.

---

## Infraestructura y Pipeline CI/CD

### Objetivo y Fundamentación de DevOps

Un pipeline automatizado de integración continua fue diseñado y desplegado con el objetivo de **eliminar revisiones manuales** y blindar la integridad del repositorio ante nuevos cambios. La herramienta permite detectar anomalías de compilación de forma inmediata en la nube cada vez que un desarrollador efectúa operaciones de carga de código.

### Especificación del Flujo de Trabajo

El archivo de configuración fue registrado en `.github/workflows/main.yml` en la rama `feature/daniel-cicd-github-actions`. El subproceso automatizado `build-and-validate` orquesta los siguientes pasos cronológicos:

1. **Checkout** — Descarga y clonación del repositorio actualizado en el agente virtual de GitHub.
2. **Docker Compose Up** — Inicialización en segundo plano de los servicios Odoo 19 y PostgreSQL.
3. **Pausa de estabilización** — Espera pasiva de 30 segundos para garantizar la estabilización de sockets internos y bases de datos.
4. **Health Check** — Comprobación de red para certificar que el puerto `8069` responda a peticiones HTTP.
5. **Cleanup** — Desmantelamiento limpio de contenedores y eliminación de volúmenes volátiles de prueba.

### Resultado de Ejecución

| Campo | Valor |
|-------|-------|
| **Estado** | ✅ Success |
| **Tiempo de ejecución** | 1m 47s |
| **Rama** | `feature/daniel-cicd-github-actions` |
| **Commit** | `66a9902` |
| **Autor** | SenciaAleBryanDaniel |

---

## Presentación e Interfaz XML

### Objetivos del Desarrollo de la Interfaz

Se implementó una extensión visual en el módulo de ventas mediante **herencia de vistas XML de Odoo**. El objetivo fue incorporar al formulario nativo la visualización explícita del descuento máximo permitido, evitando que el usuario intente registrar transacciones inválidas de forma inadvertida.

### Flujo de Control Git y Modificaciones Estructurales

Las modificaciones se aislaron en la rama `feature/diego-frontend-descuento`. Dentro del paquete `validacion_descuento_maximo`, se creó la carpeta `views/` y el archivo `sale_order_views.xml`. El manifiesto del addon fue actualizado:

```python
'data': [
    'views/sale_order_views.xml',
],
```

### Código de la Vista Heredada en XML

El archivo hereda estrictamente el formulario original de ventas (`sale.view_order_form`). Se utilizó **XPath** para inyectar una sección de solo lectura "CONTROL DE DESCUENTOS" encima del área de notas:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <record id="view_order_form_inherit_discount" model="ir.ui.view">
    <field name="name">sale.order.form.inherit.discount</field>
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="sale.view_order_form"/>
    <field name="arch" type="xml">
      <!-- Inserción visual del campo de solo lectura en el formulario nativo -->
      <xpath expr="//field[@name='note']" position="before">
        <group string="CONTROL DE DESCUENTOS" name="control_descuentos">
          <field name="descuento_maximo_permitido" readonly="1" class="oe_inline"/>
        </group>
      </xpath>
    </field>
  </record>
</odoo>
```

### Resultado Visual

En los formularios de pedidos de venta se verificó la correcta renderización del campo informativo mostrando la restricción matemática de **15.00** de manera estática y responsiva, justo encima del campo "Términos y condiciones".

---

## Control de Calidad y Evidencias

### Metodología de Pruebas Automatizadas en Backend

La estrategia de QA consistió en el diseño y despliegue de una **suite de pruebas automatizadas** aplicadas sobre los entry points del ORM de Odoo (`create`, `write` y `action_confirm`). La suite fue ejecutada dentro del entorno contenedorizado local, simulando de forma determinista la interacción multiusuario y la manipulación de datos en PostgreSQL.

### Diseño de Casos de Prueba y Cobertura

Los escenarios formulados evaluaron el comportamiento del servidor bajo condiciones de estrés funcional y valores límite:

- ✅ Validaciones de fronteras exactas: **15.0%** (válido) y **15.1%** (bloqueado).
- ✅ Actualizaciones en caliente de porcentajes de descuento en líneas existentes.
- ✅ Inserción de múltiples productos donde solo uno quiebra la política comercial.
- ✅ Verificación de aislamiento: garantizar que transacciones externas no sufran afectaciones colaterales.

### Reporte de Resultados (QA Backend)

| Métrica | Resultado |
|---------|-----------|
| **Fecha de ejecución** | 8 de junio de 2026, 12:21 hs |
| **Total de pruebas** | 15 pruebas funcionales |
| **Fallas (failures)** | 0 |
| **Errores (errors)** | 0 |
| **Tasa de éxito** | **100% ✅** |
| **Estado final** | Success |

```
2026-06-08 17:10:27,309 INFO odooips_qa_tests_ieee 15 post-tests in 0.75s; 1007 queries
2026-06-08 17:10:27,310 INFO odooips_qa_tests_ieee validacion_descuento_maximo: 17 tests 0.69s
2026-06-08 17:10:27,310 INFO odooips_qa_tests_ieee 0 failed, 0 error(s) of 15 tests
Interpretación: suite backend aprobada sin fallos ni errores.
```

---

## Conclusiones y Recomendaciones

**Robustez del Modelo de Herencia**
Los mecanismos de extensión de clases provistos por el ORM de Odoo permiten incorporar complejas reglas de control e interceptar flujos transaccionales nativos de forma limpia y transparente, logrando un código desacoplado y de fácil mantenimiento.

**Mitigación de Regresiones mediante QA Automatizado**
El desarrollo oportuno de la suite de 15 pruebas ha blindado la lógica matemática del descuento del MVP, garantizando que futuras inclusiones de código no corrompan los flujos ya validados.

**Efectividad del Monitoreo DevOps**
La automatización del Smoke Test dinámico en GitHub Actions asegura un control continuo de la salud de la infraestructura de contenedores. Se recomienda mantener el enfoque acotado a la estabilidad del contenedor, postergando suites unitarias avanzadas para el Sprint 3.

---

## Referencias

- Apaza Anahua, R. A. (2026). *odooIPS* [Código fuente]. GitHub. [https://github.com/roydanpe/odooIPS](https://github.com/roydanpe/odooIPS)
- Odoo S.A. (2026). *Odoo Source Code (Versión 19.0)* [Código fuente]. GitHub. [https://github.com/odoo/odoo](https://github.com/odoo/odoo)
- Docker Inc. (2026). *Docker* [Software de computadora]. [https://www.docker.com/](https://www.docker.com/)

