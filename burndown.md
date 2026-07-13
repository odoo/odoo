---
layout: default
title: Burndown y Avance Scrum
---

# Burndown y Avance Scrum

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
.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
    margin: 18px 0;
}
.summary-card {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 14px;
    background: #ffffff;
}
.summary-card strong {
    display: block;
    color: #714B67;
    font-size: 28px;
    line-height: 1.1;
}
.summary-card span {
    display: block;
    color: #6c757d;
    font-size: 13px;
    margin-top: 4px;
}
.chart-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
    margin: 18px 0;
}
.chart-panel {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 16px;
    background: #f8f9fa;
}
.chart-panel h2,
.chart-panel h3 {
    margin: 0 0 4px;
}
.chart-desc {
    color: #6c757d;
    font-size: 12px;
    margin: 0 0 10px;
}
.bar-row {
    display: grid;
    grid-template-columns: 92px 1fr 62px;
    align-items: center;
    gap: 10px;
    margin: 10px 0;
    font-size: 14px;
}
.bar-track {
    height: 18px;
    border-radius: 4px;
    background: #dee2e6;
    overflow: hidden;
}
.bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #714B67, #017e84);
}
.bar-fill.pending {
    background: #dc3545;
}
.bar-fill.scope {
    background: #71639e;
}
.milestone-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 12px;
    margin: 18px 0;
}
.milestone-card {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 14px;
    background: #ffffff;
}
.milestone-card h3 {
    margin-top: 0;
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
El burndown muestra como se redujo el trabajo pendiente del proyecto completo desde Sprint 0 hasta Sprint 4. No mide solo el portal publico: resume planificacion, analisis, implementacion, QA, DevOps, documentacion y cierre.
</p>

<div class="quick-nav">
  <a href="#resumen">Resumen</a>
  <a href="#burndown">Burndown</a>
  <a href="#detalle">Detalle por sprint</a>
  <a href="#hitos">Hitos</a>
  <a href="#lectura">Lectura para defensa</a>
</div>

<h2 id="resumen">Resumen del avance</h2>

<div class="summary-grid">
  <div class="summary-card"><strong>43</strong><span>Issues y tareas trazadas</span></div>
  <div class="summary-card"><strong>43</strong><span>Tareas terminadas en la vista de cierre</span></div>
  <div class="summary-card"><strong>0</strong><span>Pendientes para la defensa</span></div>
  <div class="summary-card"><strong>100%</strong><span>Avance total presentado</span></div>
</div>

<h2 id="burndown">Graficos de avance</h2>

<div class="chart-grid">
  <div class="chart-panel">
    <h3>Trabajo completado acumulado</h3>
    <p class="chart-desc">Muestra cuantas tareas quedaron completas al finalizar cada sprint.</p>
    <div class="bar-row"><span>Sprint 0</span><div class="bar-track"><div class="bar-fill" style="width: 12%;"></div></div><strong>5/43</strong></div>
    <div class="bar-row"><span>Sprint 1</span><div class="bar-track"><div class="bar-fill" style="width: 28%;"></div></div><strong>12/43</strong></div>
    <div class="bar-row"><span>Sprint 2</span><div class="bar-track"><div class="bar-fill" style="width: 40%;"></div></div><strong>17/43</strong></div>
    <div class="bar-row"><span>Sprint 3</span><div class="bar-track"><div class="bar-fill" style="width: 67%;"></div></div><strong>29/43</strong></div>
    <div class="bar-row"><span>Sprint 4</span><div class="bar-track"><div class="bar-fill" style="width: 100%;"></div></div><strong>43/43</strong></div>
  </div>

  <div class="chart-panel">
    <h3>Trabajo pendiente restante</h3>
    <p class="chart-desc">Visualiza como el trabajo pendiente disminuye hasta llegar a cero.</p>
    <div class="bar-row"><span>Sprint 0</span><div class="bar-track"><div class="bar-fill pending" style="width: 88%;"></div></div><strong>38</strong></div>
    <div class="bar-row"><span>Sprint 1</span><div class="bar-track"><div class="bar-fill pending" style="width: 72%;"></div></div><strong>31</strong></div>
    <div class="bar-row"><span>Sprint 2</span><div class="bar-track"><div class="bar-fill pending" style="width: 60%;"></div></div><strong>26</strong></div>
    <div class="bar-row"><span>Sprint 3</span><div class="bar-track"><div class="bar-fill pending" style="width: 33%;"></div></div><strong>14</strong></div>
    <div class="bar-row"><span>Sprint 4</span><div class="bar-track"><div class="bar-fill pending" style="width: 0%;"></div></div><strong>0</strong></div>
  </div>
</div>

<div class="chart-panel">
  <h3>Carga de trabajo por sprint</h3>
  <p class="chart-desc">Compara la cantidad de trabajo abordada en cada sprint del proyecto.</p>
  <div class="bar-row"><span>Sprint 0</span><div class="bar-track"><div class="bar-fill scope" style="width: 36%;"></div></div><strong>5</strong></div>
  <div class="bar-row"><span>Sprint 1</span><div class="bar-track"><div class="bar-fill scope" style="width: 50%;"></div></div><strong>7</strong></div>
  <div class="bar-row"><span>Sprint 2</span><div class="bar-track"><div class="bar-fill scope" style="width: 36%;"></div></div><strong>5</strong></div>
  <div class="bar-row"><span>Sprint 3</span><div class="bar-track"><div class="bar-fill scope" style="width: 86%;"></div></div><strong>12</strong></div>
  <div class="bar-row"><span>Sprint 4</span><div class="bar-track"><div class="bar-fill scope" style="width: 100%;"></div></div><strong>14</strong></div>
</div>

<h2 id="detalle">Detalle por sprint</h2>

| Sprint | Trabajo del sprint | Completado acumulado | Pendiente restante | Resultado |
|---|---:|---:|---:|---|
| Sprint 0 | 5 | 5 | 38 | Planificacion, seleccion de Odoo, alcance y viabilidad inicial |
| Sprint 1 | 7 | 12 | 31 | Entorno, analisis tecnico, backlog, ramas y base DevOps |
| Sprint 2 | 5 | 17 | 26 | MVP de validacion de descuento maximo en Ventas |
| Sprint 3 | 12 | 29 | 14 | Supervisor, aprobacion, limite configurable, pruebas y artifact |
| Sprint 4 | 14 | 43 | 0 | Portal publico, QA final, DevOps, documentacion, defensa y PR |

<h2 id="hitos">Hitos del proyecto</h2>

<div class="milestone-grid">
  <div class="milestone-card">
    <h3>Base Scrum</h3>
    <span class="status-pill">Completado</span>
    <p>Equipo, cronograma, backlog, roles, sprints y tablero Kanban.</p>
  </div>
  <div class="milestone-card">
    <h3>MVP funcional</h3>
    <span class="status-pill">Completado</span>
    <p>Addon de validacion de descuento maximo integrado al flujo de Ventas.</p>
  </div>
  <div class="milestone-card">
    <h3>Evolucion tecnica</h3>
    <span class="status-pill">Completado</span>
    <p>Supervisor, aprobacion, limite configurable, CI y artifact de pruebas.</p>
  </div>
  <div class="milestone-card">
    <h3>Cierre profesional</h3>
    <span class="status-pill">Completado</span>
    <p>Dashboard, burndown, defensa, QA, DevOps, evidencias y PR final.</p>
  </div>
</div>

<h2 id="lectura">Lectura para defensa</h2>

| Pregunta del docente | Respuesta breve |
|---|---|
| Para que sirve este burndown | Para demostrar que el trabajo pendiente bajo sprint por sprint hasta llegar a cero. |
| Que muestra sobre Scrum | Que hubo planificacion, seguimiento, distribucion de trabajo y cierre por sprint. |
| Que muestra sobre el proyecto | Que el equipo avanzo desde analisis hasta implementacion, QA, DevOps y documentacion final. |
| Donde se verifican las evidencias | En [Sprints](sprints.md), [Dashboard de evidencias](evidencias.md), [Issues](https://github.com/odooIPS-team/odooIPS/issues), [Project](https://github.com/orgs/odooIPS-team/projects/1) y [Actions](https://github.com/odooIPS-team/odooIPS/actions). |
