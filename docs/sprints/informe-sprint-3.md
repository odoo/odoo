# Informe del Sprint 3 — Mejoras, refactorización y estabilización

> Versión Markdown organizada a partir del documento fuente [Sprint 3 (PDF)](../../Sprint%203%20.pdf).

## Ficha del informe

| Campo | Detalle |
| --- | --- |
| Universidad | Universidad Nacional de San Agustín de Arequipa |
| Facultad | Ingeniería de Producción y Servicios |
| Escuela profesional | Ingeniería de Sistemas |
| Curso | Ingeniería de Procesos de Software |
| Docente | Ramírez Oscar |
| Proyecto | OdooIPS — Odoo Community 19.0 |
| Año | 2026 |

## Integrantes consignados en el PDF

- Quiñonez Delgado, Aarón Fernando
- Sencia Ale, Bryan Daniel
- Sivincha Machaca, Saúl André
- Yauli Merma, Diego Raúl

## Contenido

1. [Introducción](#1-introducción)
2. [Gestión del proyecto](#2-gestión-del-proyecto)
3. [Ingeniería de backend y seguridad](#3-ingeniería-de-backend-y-seguridad)
4. [Interfaz de usuario y despliegue público](#4-interfaz-de-usuario-y-despliegue-público)
5. [Infraestructura de integración continua](#5-infraestructura-de-integración-continua)
6. [Aseguramiento de la calidad](#6-aseguramiento-de-la-calidad)
7. [Resultados y conclusiones](#7-resultados-y-conclusiones)

## 1. Introducción

El Sprint 3 evolucionó el prototipo del Hito 2 hacia un producto transaccional parametrizable, respaldado por integración continua y documentación técnica pública. La arquitectura de ejecución se basa en Odoo Community 19.0 y Docker Compose.

Durante el sprint se corrigió una decisión central de diseño: la validación de descuentos dejó de lanzar una excepción `UserError`, que revertía la transacción, y pasó a retener el pedido mediante el estado `requires_review`. La versión consolidada en el Issue #53 se considera la fuente de verdad del comportamiento final.

## 2. Gestión del proyecto

### 2.1 Roles del Sprint 3

| Frente | Responsable |
| --- | --- |
| Scrum Master | Bryan Daniel Sencia |
| Product Owner | Aarón Fernando Quiñonez |
| DevOps / CI-CD | Bryan Daniel Sencia |
| Backend y parametrización | Aarón Fernando Quiñonez |
| Frontend XML y GitHub Pages | Diego Raúl Yauli |
| Aseguramiento de la calidad | Saúl André Sivincha |

### 2.2 Meta del sprint

Convertir el control de descuentos de un bloqueo simple a un flujo de aprobación parametrizable, ejecutar las pruebas automáticamente en cada `push` mediante integración continua y publicar la documentación técnica en GitHub Pages.

### 2.3 Historias de usuario priorizadas

| ID | Prioridad | Resultado esperado |
| --- | --- | --- |
| HU-1 | Crítica | Pipeline que ejecuta las pruebas y falla ante cualquier regresión. |
| HU-2 | Alta | Flujo de aprobación reservado al Supervisor de Descuentos. |
| HU-3 | Alta | Límite global de descuento configurable por compañía, con 15 % por defecto. |
| HU-4 | Alta | Pruebas del estado `requires_review` y de la parametrización empresarial. |
| HU-5 | Media | Documentación técnica y Burndown Chart publicados. |
| HU-6 | Media | Inicio del artículo IEEE y recopilación de métricas del sprint. |

### 2.4 Estado del Sprint Backlog

Las 13 tareas registradas terminaron en estado **Done**. Incluyeron la ejecución de pruebas en CI, el grupo de seguridad, la aprobación sin excepción, la parametrización por compañía, las vistas XML, el artefacto de resultados, las pruebas de aprobación y límites, GitHub Pages, el artículo IEEE, las métricas y la corrección transaccional del Issue #53.

## 3. Ingeniería de backend y seguridad

### 3.1 Arquitectura del módulo personalizado

El módulo `validacion_descuento_maximo` hereda de `sale.order` y sigue la estructura convencional de Odoo:

```text
validacion_descuento_maximo/
├── __manifest__.py
├── models/
│   ├── res_company.py
│   ├── res_config_settings.py
│   └── sale_order.py
├── security/
│   ├── discount_security.xml
│   └── ir.model.access.csv
└── views/
    ├── res_config_settings_views.xml
    └── sale_order_views.xml
```

### 3.2 Parametrización dinámica

El modelo `res.company` incorpora `discount_limit_percentage`, un campo que permite definir el límite comercial por empresa. Si no se configura un valor, se aplica un límite predeterminado de 15 %.

```python
discount_limit_percentage = fields.Float(
    string="Límite de Descuento Global (%)",
    default=15.0,
    help="Porcentaje máximo permitido sin aprobación de supervisor.",
)
```

### 3.3 Control transaccional

`action_confirm` revisa las líneas comerciales. Si alguna supera el límite, conserva el pedido y cambia su estado a `requires_review`. La aprobación autorizada devuelve temporalmente el pedido a borrador y confirma con el contexto `skip_discount_limit_validation=True`.

```python
def action_confirm(self):
    for order in self:
        if self.env.context.get("skip_discount_limit_validation"):
            continue
        if order._has_discount_above_limit():
            order.write({"state": "requires_review"})
            return True
    return super().action_confirm()
```

Este flujo evita el `rollback` que producía la implementación anterior basada en excepciones.

### 3.4 Seguridad y jerarquías

El grupo `group_discount_supervisor` identifica al Supervisor de Descuentos y se integra con el rol Gerente de Ventas. El permiso se valida en dos niveles:

- La vista solo muestra el botón de aprobación al grupo autorizado.
- El backend vuelve a comprobar `has_group` antes de ejecutar la operación.

### 3.5 Flujo funcional E2E

1. Un usuario intenta confirmar una cotización que supera el límite configurado.
2. El sistema cambia el pedido a **Requiere revisión** sin perder la transacción.
3. Un supervisor abre el pedido y visualiza **Aprobar descuento**.
4. El backend verifica el permiso y confirma el pedido en estado `sale`.

## 4. Interfaz de usuario y despliegue público

### 4.1 Vistas heredadas

La vista de `sale.order` incorpora el botón **Aprobar descuento** dentro del encabezado. Su visibilidad depende del estado `requires_review` y del grupo `group_discount_supervisor`.

La vista de configuración de Ventas también expone el campo `discount_limit_percentage`, de modo que un administrador pueda modificar la política sin editar código.

### 4.2 Documentación

El sprint contempló la publicación en GitHub Pages de la documentación técnica y el gráfico Burndown. Esta versión Markdown mantiene el contenido principal del informe enlazado desde el índice general del repositorio.

## 5. Infraestructura de integración continua

### 5.1 Pipeline de CI

El flujo de GitHub Actions se ejecuta ante `push` y `pull_request` en las ramas `19.0`, `main` y `develop`. Sus pasos principales son:

1. Obtener el código.
2. Levantar Odoo y PostgreSQL 15 con Docker Compose.
3. Ejecutar únicamente las pruebas de `validacion_descuento_maximo`.
4. Imprimir el log aunque existan fallos.
5. Propagar el código de salida para marcar el job como fallido.
6. Publicar `odoo_tests.log` como artefacto, incluso si la suite falla.

El comando de pruebas usa `--test-enable`, `--test-tags /validacion_descuento_maximo`, `--stop-after-init` y el puerto aislado `8070`.

### 5.2 Decisiones de diseño

- **Puerto 8070:** evita colisiones con la instancia principal de Odoo en el puerto 8069.
- **Captura de `TEST_EXIT`:** permite mostrar el log completo y conserva el resultado real de la suite.
- **Condición `if: always()`:** garantiza la disponibilidad del artefacto de QA tanto en ejecuciones correctas como fallidas.
- **Trazabilidad:** el pipeline usa la base limpia `odoo_ventas`; las ejecuciones sobre el puerto 8079 y `odooips_discount_tests_report_final` corresponden a validaciones manuales locales.

## 6. Aseguramiento de la calidad

### 6.1 Estrategia automatizada

La suite se adaptó al comportamiento definitivo del Issue #53. En lugar de esperar una excepción, ahora verifica directamente la retención transaccional:

```python
order.action_confirm()
self.assertEqual(order.state, "requires_review")
```

Los casos cubren:

- límite predeterminado de 15 %;
- límite personalizado por compañía;
- asociación correcta de cada pedido con su compañía;
- retención del pedido en `requires_review`;
- aprobación por el grupo autorizado;
- rechazo de usuarios sin el permiso requerido.

### 6.2 Resultado

La ejecución documentada terminó correctamente:

```text
Ran 16 tests in 1.373s
OK (0 failed, 0 errors of 16 tests)
```

## 7. Resultados y conclusiones

| Indicador | Resultado |
| --- | --- |
| Tareas del Sprint Backlog | 13 completadas |
| Pruebas automatizadas | 16 correctas |
| Fallos y errores reportados | 0 |
| Estado de control incorporado | `requires_review` |
| Límite predeterminado | 15 % |
| Evidencia de CI | Log publicado como artefacto |

La integración continua permite detectar regresiones antes de consolidar cambios. La sustitución de excepciones bloqueantes por un flujo basado en estados protege la persistencia de los pedidos y habilita una aprobación comercial explícita. Para los siguientes ciclos se recomienda mantener aislados los puertos y las bases de prueba, y conservar filtros de etiquetas específicos para evitar ejecuciones ajenas al módulo.

## Referencia

Apaza Nahua, R. (2026). *odooIPS* [Código fuente]. GitHub: <https://github.com/roydanpe/odooIPS.git>

---

[Volver al índice de documentación](../README.md) · [Volver al plan del proyecto](../../index.md)
