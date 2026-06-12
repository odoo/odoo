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

## Resumen del proyecto

El proyecto se desarrolló en dos sprints sobre el módulo **sale** (Ventas) de Odoo 19.0. El Sprint 1 se enfocó en el análisis de la arquitectura del módulo (modelos, vistas, estados y métodos), mientras que el Sprint 2 implementó una extensión funcional real: una **política de control de descuentos máximos**, sin modificar el código fuente original de Odoo, usando los mecanismos de herencia que ofrece el framework.

## Implementación: control de descuento máximo

Se extendió la lógica del modelo `sale.order` para validar el porcentaje de descuento aplicado a las líneas de un pedido. La regla establece un **umbral del 15%**: si alguna línea supera ese valor, el pedido queda retenido en estado "Requiere Revisión" y se informa al usuario mediante una excepción (`UserError`), en lugar de permitir la confirmación.

Para que el valor del umbral fuera visible y no modificable accidentalmente desde el formulario, se creó una vista heredada que añade un panel de solo lectura "Control de Descuentos" en el formulario del pedido de venta:

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

La verificación funcional confirmó que el formulario muestra correctamente el valor **15.00** en el área de términos y condiciones. La extensión conservó la vista original de Odoo y únicamente añadió el componente requerido, sin alterar el resto de la interfaz.

## Aseguramiento de calidad (QA)

La estrategia de pruebas se aplicó sobre los puntos de entrada `create`, `write` y `action_confirm` del ORM de Odoo. Los casos de prueba cubrieron: valores de descuento inferiores, iguales y superiores al límite; cambios de descuento sobre líneas ya existentes; pedidos con múltiples productos; y la verificación de que pedidos que cumplen la política no se vean afectados (aislamiento).

| Categoría | Escenario | Resultado esperado |
|---|---|---|
| Límite inferior | Descuento menor a 15.0% | La confirmación continúa normalmente. |
| Límite exacto | Descuento igual a 15.0% | La confirmación continúa normalmente. |
| Límite excedido | Descuento de 15.1% o más | El pedido requiere revisión y se informa al usuario. |
| Actualización | Una línea existente cambia a un valor inválido | La validación detecta el nuevo valor. |
| Múltiples líneas | Solo una línea supera el umbral | El pedido completo queda retenido. |
| Aislamiento | Otros pedidos cumplen la política | No se producen efectos colaterales sobre ellos. |

La ejecución de pruebas, registrada el **8 de junio de 2026 a las 12:21**, comprendió **15 pruebas de posinstalación**, con **0 fallas, 0 errores y 100% de aprobación**. Estos resultados validan tanto el comportamiento del nuevo estado `requires_review` como la excepción lanzada durante la confirmación cuando se excede el umbral.

## Infraestructura y flujo de trabajo

El proyecto se trabajó sobre un entorno **contenedorizado con Docker** (servicios de base de datos PostgreSQL 15 y Odoo 19.0 mediante Docker Compose), lo que facilitó la reproducibilidad del entorno entre los integrantes del equipo. Adicionalmente, se configuró un pipeline en **GitHub Actions** que se ejecuta automáticamente con cada push, validando que el entorno de Docker Compose se levante correctamente (build-and-validate).

La gestión del trabajo se organizó mediante un tablero **Kanban en GitHub** dividido en columnas "Por hacer", "En progreso" y "Completado", asociado a un *milestone* ("Hito 2 - Sprint 2") que alcanzó el 100% de avance al cierre del sprint, con 5 issues completados correspondientes a las áreas de Backend, DevOps, Frontend, QA/Documentación y Gestión.

## Discusión

La secuencia entre ambos sprints fue técnicamente consistente. El análisis del Sprint 1 identificó `action_confirm` como un punto apropiado para incorporar controles previos a la confirmación de un pedido. El Sprint 2 convirtió esa observación en una extensión funcional concreta, acompañada de una vista informativa y pruebas automatizadas. De este modo, la implementación se apoyó en el conocimiento arquitectónico obtenido previamente y evitó modificar directamente el código del módulo `sale`.

La contenedorización facilitó la reproducibilidad del entorno, mientras que GitHub Actions trasladó parte de la verificación a un agente remoto. Sin embargo, la comprobación realizada (levantar el entorno y verificar el puerto) constituye principalmente una **prueba de humo de infraestructura**. En iteraciones posteriores conviene ejecutar también la suite completa de pruebas de Odoo dentro del pipeline, registrar cobertura de código y comprobar las migraciones del módulo.

La regla actual retiene cualquier pedido que excede el umbral, pero un flujo productivo debería considerar permisos diferenciados, aprobadores designados, auditoría de cambios y configuración del límite por compañía o categoría comercial. También debe verificarse cuidadosamente el efecto transaccional de escribir el nuevo estado antes de lanzar el `UserError`, debido a que Odoo puede revertir operaciones dentro de la misma transacción si esta falla. Una implementación madura podría requerir un flujo explícito de solicitud y aprobación, en lugar de depender únicamente de una excepción que bloquea la operación.

## Conclusiones

1. El **Sprint 1** produjo una base de trabajo reproducible y un análisis suficiente de las dependencias, modelos, estados, métodos y vistas del módulo de Ventas. Esta preparación permitió seleccionar un punto de extensión compatible con el framework de Odoo.

2. El **Sprint 2** implementó un producto mínimo viable (MVP) que combina lógica de servidor, interfaz XML, seguimiento ágil del trabajo, integración continua y pruebas automatizadas. La suite reportó 15 pruebas aprobadas, sin fallas ni errores, y el pipeline remoto confirmó la disponibilidad del servicio contenedorizado.

3. La **herencia de modelos y vistas** permitió incorporar la regla de descuento sin alterar el núcleo de Odoo, siguiendo las buenas prácticas de extensión recomendadas por el framework.

4. Para el **Sprint 3** se recomienda: integrar las pruebas funcionales al pipeline de CI, formalizar un flujo explícito de aprobación, revisar el comportamiento transaccional del estado de revisión, y ampliar la parametrización del límite comercial (por compañía, categoría, etc.).

## Referencias

- Apaza Anahua, R. A. (2026). *odooIPS* [Código fuente]. GitHub. https://github.com/roydanpe/odooIPS
- Docker, Inc. (2026). *Docker* [Software de computadora]. https://www.docker.com/
- GitHub, Inc. (2026). *GitHub Actions* [Servicio de integración continua]. https://github.com/features/actions
- Odoo S.A. (2026). *Odoo source code* (Versión 19.0) [Código fuente]. GitHub. https://github.com/odoo/odoo
