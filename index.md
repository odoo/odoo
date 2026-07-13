---
layout: default
title: Portal del Proyecto
---

<style>
table th {
    background-color: #020d1a !important;
    color: white !important;
}
.hero {
    border: 1px solid #d8dee4;
    border-radius: 6px;
    padding: 18px;
    margin: 16px 0;
    background: #f6f8fa;
}
.quick-links a {
    display: inline-block;
    margin: 4px 8px 4px 0;
    padding: 6px 10px;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    text-decoration: none;
    background: #ffffff;
}
</style>

# Scrum y DevOps aplicado a Odoo ERP

<div class="hero">
<strong>Proyecto:</strong> mejora y validacion del modulo de Ventas en Odoo, con analisis complementario de Compras.<br>
<strong>Curso:</strong> Ingenieria y Procesos de Software 2026-A.<br>
<strong>Sprint actual:</strong> Sprint 4 - cierre profesional del Hito 3.<br>
<strong>Repositorio:</strong> <a href="https://github.com/odooIPS-team/odooIPS">odooIPS-team/odooIPS</a>.<br>
<strong>GitHub Pages:</strong> <a href="https://odooips-team.github.io/odooIPS/">https://odooips-team.github.io/odooIPS/</a>.
</div>

## Navegacion

<div class="quick-links">
<a href="sprints.md">Sprints</a>
<a href="evidencias.md">Evidencias</a>
<a href="burndown.md">Burndown</a>
<a href="defensa.md">Defensa ejecutiva</a>
<a href="sprint1.md">Sprint 1</a>
<a href="sprint2.md">Sprint 2</a>
<a href="ArquitecturaModuloVnetas.md">Arquitectura Ventas</a>
<a href="REPORTE_VERIFICACION.md">Verificacion tecnica</a>
<a href="cronograma.md">Cronograma</a>
</div>

## Objetivo del proyecto

Aplicar Scrum y practicas DevOps sobre un producto real de software open source: Odoo ERP. El equipo trabajo sobre el modulo de Ventas para implementar y validar una mejora funcional relacionada con el control de descuentos, y uso el modulo de Compras como parte del analisis tecnico del alcance.

El cierre del Sprint 4 busca presentar una entrega verificable, navegable y defendible mediante GitHub Issues, GitHub Actions, Docker Compose, documentacion tecnica, evidencia QA y GitHub Pages.

## Alcance funcional

| Area | Alcance | Estado |
|---|---|---|
| Ventas | Validacion de descuento maximo, estado `requires_review`, aprobacion por supervisor y limite configurable | Implementado y en cierre de evidencia |
| Compras | Analisis tecnico y documentacion del modulo como parte del alcance ERP | Documentado como antecedente tecnico |
| DevOps | Docker Compose, GitHub Actions, artifact de pruebas y Jenkinsfile como evidencia adicional | En cierre por issue #68 |
| QA | Casos de prueba funcionales, artifact y resultados finales | En cierre por issue #66 |
| Documentacion | Portal Pages, trazabilidad, changelog, roadmap, guia y presentacion | En cierre por issues #56, #67 y #69 |

## Equipo Sprint 4

| Integrante | Rol en Sprint 4 | Issues principales |
|---|---|---|
| Sivincha Machaca Saul Andre | Scrum Master, GitHub Pages, cierre e insumos finales | [#56](https://github.com/odooIPS-team/odooIPS/issues/56), [#70](https://github.com/odooIPS-team/odooIPS/issues/70), [#33](https://github.com/odooIPS-team/odooIPS/issues/33) |
| Quinonez Delgado Aaron Fernando | Validacion funcional, Ventas/Compras y QA final | [#65](https://github.com/odooIPS-team/odooIPS/issues/65), [#66](https://github.com/odooIPS-team/odooIPS/issues/66) |
| Sencia Ale Bryan Daniel | DevOps, Docker Compose, GitHub Actions, Jenkinsfile y badges | [#68](https://github.com/odooIPS-team/odooIPS/issues/68) |
| Yauli Merma Diego Raul | Documentacion Scrum, entregables, changelog, roadmap, guia y presentacion | [#67](https://github.com/odooIPS-team/odooIPS/issues/67), [#69](https://github.com/odooIPS-team/odooIPS/issues/69) |

## Sprint 4: cierre profesional

| Issue | Frente | Responsable | Resultado esperado |
|---|---|---|---|
| [#56](https://github.com/odooIPS-team/odooIPS/issues/56) | GitHub Pages profesional | Saul | Portal publico con navegacion, evidencias, burndown y defensa |
| [#65](https://github.com/odooIPS-team/odooIPS/issues/65) | Validacion funcional | Aaron | Comportamiento final de Ventas y alcance de Compras documentado |
| [#66](https://github.com/odooIPS-team/odooIPS/issues/66) | QA final | Aaron | Informe QA con casos, resultados, artifact y evidencias |
| [#67](https://github.com/odooIPS-team/odooIPS/issues/67) | Documentacion Scrum | Diego | Sprint 4, roles y matriz de trazabilidad |
| [#68](https://github.com/odooIPS-team/odooIPS/issues/68) | DevOps final | Bryan | Docker Compose, Actions, artifact, Jenkinsfile y badges |
| [#69](https://github.com/odooIPS-team/odooIPS/issues/69) | Entregables | Diego | Changelog, roadmap, guia de instalacion y presentacion |
| [#70](https://github.com/odooIPS-team/odooIPS/issues/70) | Insumos finales | Saul | Tabla de evidencias para informe final y articulo |
| [#33](https://github.com/odooIPS-team/odooIPS/issues/33) | Integracion final | Saul | PR final, merge y cierre del Hito 3 |

## Evidencias principales

| Evidencia | Enlace | Proposito |
|---|---|---|
| Dashboard de evidencias | [evidencias.md](evidencias.md) | Centralizar issues, PRs, Actions, artifact y entregables |
| Burndown / avance Scrum | [burndown.md](burndown.md) | Mostrar avance planificado, completado y pendiente |
| Defensa ejecutiva | [defensa.md](defensa.md) | Explicar el proyecto en lectura rapida para el docente |
| Cronograma | [cronograma.md](cronograma.md) | Mostrar plan de sprints e hitos |
| GitHub Actions | [Actions](https://github.com/odooIPS-team/odooIPS/actions) | Verificar pipeline y artifacts |
| Project Kanban | [Gestion Scrum - odoo](https://github.com/orgs/odooIPS-team/projects/1) | Ver estado del Product Backlog |

## Criterio de cierre de GitHub Pages

Esta pagina se considera lista cuando el docente puede entender el proyecto desde la portada, navegar a cada evidencia relevante y verificar los entregables sin depender de explicaciones verbales ni archivos locales.
