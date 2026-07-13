---
layout: default
title: Defensa Ejecutiva
---

# Defensa Ejecutiva del Proyecto

[Volver al portal](index.md)

<style>
.page-note {
    max-width: 980px;
    color: #6c757d;
    margin: 12px 0 20px;
}
.quick-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 18px 0 24px;
}
.quick-nav a {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 7px 10px;
    text-decoration: none;
    background: #ffffff;
    font-size: 14px;
}
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 12px;
    margin: 18px 0;
}
.kpi-card {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 14px;
    background: #ffffff;
}
.kpi-card strong {
    display: block;
    color: #714B67;
    font-size: 28px;
    line-height: 1.1;
}
.kpi-card span {
    display: block;
    color: #6c757d;
    font-size: 13px;
    margin-top: 4px;
}
.section-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 14px;
    margin: 18px 0;
}
.info-card {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 15px;
    background: #ffffff;
}
.info-card h3 {
    margin-top: 0;
}
.flow {
    display: grid;
    gap: 10px;
    margin: 18px 0;
}
.flow-step {
    border-left: 4px solid #714B67;
    padding: 9px 12px;
    background: #f8f9fa;
}
.flow-step strong {
    display: block;
}
.status-pill {
    display: inline-block;
    padding: 4px 9px;
    border-radius: 999px;
    background: #e6f2f3;
    color: #017e84;
    font-size: 12px;
    font-weight: 700;
}
</style>

<p class="page-note">
Esta pagina funciona como guion para explicar el proyecto completo ante el docente: problema, solucion, incremento funcional, Scrum, DevOps, QA, evidencias y cierre.
</p>

<div class="quick-nav">
  <a href="#resumen">Resumen</a>
  <a href="#problema">Problema</a>
  <a href="#solucion">Solucion</a>
  <a href="#demo">Demo</a>
  <a href="#scrum">Scrum</a>
  <a href="#devops">DevOps</a>
  <a href="#qa">QA</a>
</div>

<h2 id="resumen">Resumen ejecutivo</h2>

<div class="kpi-grid">
  <div class="kpi-card"><strong>Odoo</strong><span>ERP open source usado como producto base</span></div>
  <div class="kpi-card"><strong>Ventas</strong><span>Modulo principal intervenido</span></div>
  <div class="kpi-card"><strong>5</strong><span>Sprints documentados</span></div>
  <div class="kpi-card"><strong>43</strong><span>Issues y tareas trazadas</span></div>
  <div class="kpi-card"><strong>100%</strong><span>Cierre presentado para defensa</span></div>
</div>

<div class="section-grid">
  <div class="info-card">
    <h3>Que se hizo</h3>
    <p>Se implemento y documento una mejora funcional para controlar descuentos maximos en pedidos de venta de Odoo.</p>
  </div>
  <div class="info-card">
    <h3>Como se gestiono</h3>
    <p>El trabajo se organizo con Scrum, GitHub Issues, Project Kanban, sprints, roles y evidencias por entrega.</p>
  </div>
  <div class="info-card">
    <h3>Como se verifico</h3>
    <p>Se dejo evidencia funcional, QA, DevOps, workflows, Docker Compose, tablero de avance y portal publico.</p>
  </div>
</div>

<h2 id="problema">Problema abordado</h2>

En un proceso comercial, descuentos excesivos pueden afectar margenes, generar ventas no autorizadas y requerir revision de un responsable. El flujo base necesitaba una validacion clara para detectar descuentos superiores al limite permitido antes de confirmar el pedido.

| Riesgo | Impacto | Respuesta del proyecto |
|---|---|---|
| Descuentos mayores al permitido | Perdida de margen comercial | Validacion automatica en lineas de venta |
| Confirmacion sin revision | Falta de control interno | Estado `requires_review` |
| Aprobaciones informales | Baja trazabilidad | Grupo Supervisor de Descuentos |
| Reglas rigidas | Dificil mantenimiento | Limite configurable |

<h2 id="solucion">Solucion implementada</h2>

| Elemento | Descripcion | Evidencia |
|---|---|---|
| Validacion de descuentos | Revisa descuentos en lineas de pedido de venta | Addon `validacion_descuento_maximo` |
| Estado `requires_review` | Retiene pedidos que superan el limite permitido | Flujo funcional documentado |
| Supervisor de descuentos | Grupo autorizado para aprobar pedidos retenidos | Issues Sprint 3 |
| Boton de aprobacion | Permite confirmar pedidos revisados por supervisor | Vista XML y pruebas |
| Limite configurable | Parametriza el porcentaje maximo permitido | Ajustes del modulo |

<h2 id="demo">Flujo sugerido para la demo</h2>

<div class="flow">
  <div class="flow-step"><strong>1. Crear pedido de venta</strong> Ingresar una cotizacion con una linea de producto y un descuento normal.</div>
  <div class="flow-step"><strong>2. Superar el limite permitido</strong> Editar el descuento para que exceda el porcentaje configurado.</div>
  <div class="flow-step"><strong>3. Activar revision</strong> Mostrar que el pedido queda en estado `requires_review` y no sigue como una venta comun.</div>
  <div class="flow-step"><strong>4. Aprobar como supervisor</strong> Usar el rol autorizado para aprobar el descuento y continuar el flujo.</div>
  <div class="flow-step"><strong>5. Mostrar evidencias</strong> Enseñar Issues, Actions, burndown, dashboard de evidencias y PR final.</div>
</div>

<h2 id="scrum">Scrum aplicado</h2>

| Practica | Como se aplico | Evidencia |
|---|---|---|
| Product Backlog | Issues creadas, priorizadas y asignadas | [GitHub Issues](https://github.com/odooIPS-team/odooIPS/issues) |
| Kanban | Seguimiento en tablero de proyecto | [Project Kanban](https://github.com/orgs/odooIPS-team/projects/1) |
| Sprints | Sprint 0 a Sprint 4 con objetivos y responsables | [Sprints](sprints.md) |
| Burndown | Seguimiento de trabajo pendiente y completado | [Burndown](burndown.md) |
| Evidencias | Dashboard por sprint y por responsable | [Dashboard de evidencias](evidencias.md) |

<h2 id="devops">DevOps aplicado</h2>

| Practica | Resultado | Evidencia |
|---|---|---|
| Entorno reproducible | Odoo y PostgreSQL ejecutables con Docker Compose | [docker-compose.yml](docker-config/docker-compose.yml) |
| Control de versiones | Trabajo organizado en ramas, commits e issues | [Repositorio](https://github.com/odooIPS-team/odooIPS) |
| Integracion continua | Workflows para validacion automatizada | [Actions](https://github.com/odooIPS-team/odooIPS/actions) |
| Artifacts | Registro de resultados de pruebas cuando aplica | Actions / artifacts |
| Publicacion | Portal publico de documentacion y evidencias | [GitHub Pages](https://odooips-team.github.io/odooIPS/) |

<h2 id="qa">QA y validacion</h2>

| Escenario | Resultado esperado |
|---|---|
| Descuento dentro del limite | El pedido mantiene flujo normal |
| Descuento superior al limite | El pedido pasa a revision |
| Usuario no supervisor | No puede aprobar descuentos retenidos |
| Usuario supervisor | Puede aprobar y continuar el flujo |
| Limite configurable | El comportamiento cambia segun la configuracion |

<span class="status-pill">Proyecto listo para defensa</span>
