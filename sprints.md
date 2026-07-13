---
layout: default
title: Sprints del Proyecto
---

# Sprints del Proyecto

[Volver al portal](index.md)

Esta pagina resume el avance Scrum del proyecto desde la planificacion inicial hasta el cierre profesional del Sprint 4.

| Sprint | Objetivo | Entregable principal | Estado | Enlace |
|---|---|---|---|---|
| Sprint 0 | Seleccionar Odoo, definir alcance, equipo, cronograma y viabilidad tecnica | Plan inicial del proyecto y cronograma | Completado como antecedente | [Portal](index.md) / [Cronograma](cronograma.md) |
| Sprint 1 | Preparar entorno, analizar arquitectura y documentar el modulo de Ventas | Entorno Docker Compose y documentacion tecnica inicial | Completado | [Sprint 1](sprint1.md) |
| Sprint 2 | Implementar MVP de validacion de descuento maximo en Ventas | Addon `validacion_descuento_maximo` y pruebas iniciales | Completado | [Sprint 2](sprint2.md) |
| Sprint 3 | Evolucion del flujo de descuentos con aprobacion, supervisor, limite configurable y CI | Mejoras funcionales y pipeline con artifact | Antecedente historico | [Issues Sprint 3](https://github.com/odooIPS-team/odooIPS/issues?q=is%3Aissue%20label%3ASprint3) |
| Sprint 4 | Cerrar el Hito 3 con GitHub Pages, QA, DevOps, documentacion, evidencias e insumos finales | Portal profesional y entregables de cierre | En ejecucion | [Issues Sprint 4](https://github.com/odooIPS-team/odooIPS/issues?q=is%3Aissue%20label%3ASprint4) |

## Vista de cierre del Sprint 4

| Frente | Issue | Responsable | Resultado esperado |
|---|---|---|---|
| GitHub Pages | [#56](https://github.com/odooIPS-team/odooIPS/issues/56) | Saul | Portal publico navegable |
| Producto | [#65](https://github.com/odooIPS-team/odooIPS/issues/65) | Aaron | Alcance Ventas/Compras documentado |
| QA | [#66](https://github.com/odooIPS-team/odooIPS/issues/66) | Aaron | Informe QA final |
| Scrum | [#67](https://github.com/odooIPS-team/odooIPS/issues/67) | Diego | Trazabilidad del cierre |
| DevOps | [#68](https://github.com/odooIPS-team/odooIPS/issues/68) | Bryan | Actions, Docker Compose, Jenkinsfile y badges |
| Entregables | [#69](https://github.com/odooIPS-team/odooIPS/issues/69) | Diego | Changelog, roadmap, guia y presentacion |
| Insumos finales | [#70](https://github.com/odooIPS-team/odooIPS/issues/70) | Saul | Evidencias para informe y articulo |
| Integracion final | [#33](https://github.com/odooIPS-team/odooIPS/issues/33) | Saul | PR final y cierre |

## Ruta recomendada de trabajo

1. Construir el portal Pages y su navegacion.
2. Publicar documentacion Scrum y entregables.
3. Integrar QA y DevOps como evidencias verificables.
4. Consolidar insumos finales.
5. Abrir PR final contra `19.0`.
