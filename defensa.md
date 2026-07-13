---
layout: default
title: Defensa Ejecutiva
---

# Defensa Ejecutiva del Proyecto

[Volver al portal](index.md)

Esta pagina resume el proyecto para una explicacion rapida ante el docente evaluador.

## Que es el proyecto

El proyecto aplica Scrum y practicas DevOps sobre Odoo ERP, un sistema empresarial open source. El equipo trabajo principalmente sobre el modulo de Ventas, porque el control de descuentos representa una regla comercial clara, verificable y relevante.

## Problema abordado

En un flujo comercial, descuentos excesivos pueden afectar margenes y requieren control. La mejora implementada permite identificar pedidos con descuentos superiores al limite permitido y llevarlos a revision antes de su confirmacion final.

## Incremento funcional

| Elemento | Descripcion |
|---|---|
| Validacion de descuentos | Revisa descuentos en lineas de pedido de venta |
| Estado `requires_review` | Retiene pedidos que superan el limite permitido |
| Supervisor de descuentos | Grupo autorizado para aprobar pedidos retenidos |
| Boton de aprobacion | Permite confirmar pedidos revisados por supervisor |
| Limite configurable | Permite parametrizar el porcentaje maximo permitido |

## Scrum aplicado

| Practica | Evidencia |
|---|---|
| Product Backlog | [GitHub Issues](https://github.com/odooIPS-team/odooIPS/issues) |
| Kanban | [GitHub Project](https://github.com/orgs/odooIPS-team/projects/1) |
| Sprints | [Resumen de sprints](sprints.md) |
| Avance | [Burndown / tabla Scrum](burndown.md) |
| Cierre | Issues #56, #65, #66, #67, #68, #69, #70 y #33 |

## DevOps aplicado

| Practica | Evidencia |
|---|---|
| Entorno reproducible | [Docker Compose](docker-config/docker-compose.yml) |
| CI | [GitHub Actions](https://github.com/odooIPS-team/odooIPS/actions) |
| Artifact de pruebas | Run de Actions con `odoo-test-results` si esta disponible |
| Pipeline alternativo | Jenkinsfile planificado en issue #68 |
| Publicacion | [GitHub Pages](https://odooips-team.github.io/odooIPS/) |

## QA y evidencia

La calidad se defiende con casos funcionales del flujo de descuento, resultados esperados y evidencia enlazada desde GitHub Actions, artifacts, capturas o documentos versionados.

| Frente | Donde revisar |
|---|---|
| QA final | [Issue #66](https://github.com/odooIPS-team/odooIPS/issues/66) |
| Evidencias centralizadas | [Dashboard](evidencias.md) |
| DevOps | [Issue #68](https://github.com/odooIPS-team/odooIPS/issues/68) |
| Producto | [Issue #65](https://github.com/odooIPS-team/odooIPS/issues/65) |

## Mensaje final de defensa

El proyecto demuestra un ciclo completo de trabajo agil y tecnico: seleccion de software, analisis, implementacion incremental, validacion, automatizacion CI/CD, documentacion publica y cierre trazable mediante GitHub.
