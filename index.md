---
layout: default
title: Portal del Proyecto
---

<style>
:root {
    --odoo-primary: #714B67;
    --odoo-action: #017e84;
    --odoo-community: #71639e;
    --odoo-muted: #6c757d;
    --odoo-border: #dee2e6;
    --odoo-bg: #f8f9fa;
}
table th {
    background-color: var(--odoo-primary) !important;
    color: white !important;
}
.hero {
    border: 1px solid var(--odoo-border);
    border-radius: 6px;
    padding: 20px;
    margin: 16px 0;
    background: var(--odoo-bg);
}
.hero p {
    max-width: 960px;
}
.meta-line {
    color: var(--odoo-muted);
    margin-top: 10px;
}
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin: 18px 0;
}
.kpi-card {
    border: 1px solid var(--odoo-border);
    border-radius: 6px;
    padding: 14px;
    background: #ffffff;
}
.kpi-card strong {
    display: block;
    color: var(--odoo-primary);
    font-size: 28px;
    line-height: 1.1;
}
.kpi-card span {
    display: block;
    color: var(--odoo-muted);
    font-size: 13px;
    margin-top: 4px;
}
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 14px;
    margin: 18px 0;
}
.nav-card,
.info-card {
    border: 1px solid var(--odoo-border);
    border-radius: 6px;
    padding: 15px;
    background: #ffffff;
}
.nav-card h3,
.info-card h3 {
    margin-top: 0;
}
.nav-card a {
    color: var(--odoo-action);
    font-weight: 700;
    text-decoration: none;
}
.feature-list {
    display: grid;
    gap: 8px;
    margin: 16px 0;
}
.feature-item {
    border-left: 4px solid var(--odoo-primary);
    background: var(--odoo-bg);
    padding: 9px 12px;
}
.feature-item strong {
    display: block;
}
.team-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    margin: 18px 0;
}
.team-card {
    border: 1px solid var(--odoo-border);
    border-radius: 6px;
    padding: 14px;
    background: #ffffff;
}
.team-card strong {
    display: block;
    color: var(--odoo-primary);
}
.team-card span {
    display: block;
    color: var(--odoo-muted);
    margin-top: 4px;
    font-size: 13px;
}
</style>

# Scrum y DevOps aplicado a Odoo ERP

<div class="hero">
  <p><strong>Proyecto:</strong> mejora y validacion del modulo de Ventas en Odoo, con analisis complementario de Compras.</p>
  <p>El equipo aplico Scrum y practicas DevOps sobre Odoo ERP para implementar una mejora funcional de control de descuentos: validacion de porcentaje maximo, estado de revision, aprobacion por supervisor y limite configurable.</p>
  <p class="meta-line"><strong>Curso:</strong> Ingenieria y Procesos de Software 2026-A · <strong>Sprint final:</strong> Sprint 4 · <strong>Repositorio:</strong> <a href="https://github.com/odooIPS-team/odooIPS">odooIPS-team/odooIPS</a></p>
</div>

## Resumen ejecutivo

Este portal presenta el proyecto completo: objetivos, avance por sprint, evidencias, burndown, defensa, arquitectura y verificacion tecnica. La portada funciona como punto de entrada; los detalles estan separados en paginas especificas para evitar duplicar informacion.

<div class="kpi-grid">
  <div class="kpi-card"><strong>5</strong><span>Sprints documentados</span></div>
  <div class="kpi-card"><strong>43</strong><span>Issues y tareas trazadas</span></div>
  <div class="kpi-card"><strong>100%</strong><span>Avance presentado</span></div>
  <div class="kpi-card"><strong>0</strong><span>Pendientes para defensa</span></div>
</div>

## Que se construyo

<div class="feature-list">
  <div class="feature-item"><strong>Control de descuentos en Ventas</strong> Validacion de descuentos maximos en lineas de pedido de venta.</div>
  <div class="feature-item"><strong>Revision comercial</strong> Estado `requires_review` para pedidos que superan el limite permitido.</div>
  <div class="feature-item"><strong>Aprobacion por supervisor</strong> Grupo autorizado y boton de aprobacion para continuar el flujo.</div>
  <div class="feature-item"><strong>Configuracion flexible</strong> Limite de descuento parametrizable para adaptar la regla comercial.</div>
</div>

## Explorar el proyecto

<div class="card-grid">
  <div class="nav-card">
    <h3>Sprints</h3>
    <p>Objetivos, lideres, tiempos, asignaciones y aportes desde Sprint 0 hasta Sprint 4.</p>
    <a href="sprints.md">Ver sprints</a>
  </div>
  <div class="nav-card">
    <h3>Evidencias</h3>
    <p>Dashboard visual por sprint con issues, asignaciones, roles y enlaces de verificacion.</p>
    <a href="evidencias.md">Ver evidencias</a>
  </div>
  <div class="nav-card">
    <h3>Burndown</h3>
    <p>Avance Scrum del proyecto completo y reduccion del trabajo pendiente por sprint.</p>
    <a href="burndown.md">Ver burndown</a>
  </div>
  <div class="nav-card">
    <h3>Defensa</h3>
    <p>Guion ejecutivo para explicar problema, solucion, Scrum, DevOps y QA.</p>
    <a href="defensa.md">Ver defensa</a>
  </div>
  <div class="nav-card">
    <h3>Arquitectura</h3>
    <p>Analisis tecnico del modulo de Ventas y estructura funcional revisada.</p>
    <a href="ArquitecturaModuloVnetas.md">Ver arquitectura</a>
  </div>
  <div class="nav-card">
    <h3>Verificacion</h3>
    <p>Reporte tecnico, pruebas y evidencias de validacion del comportamiento implementado.</p>
    <a href="REPORTE_VERIFICACION.md">Ver verificacion</a>
  </div>
</div>

## Equipo

<div class="team-grid">
  <div class="team-card"><strong>Sivincha Machaca Saul Andre</strong><span>Scrum Master Sprint 4, portal publico, evidencias e integracion final.</span></div>
  <div class="team-card"><strong>Quinonez Delgado Aaron Fernando</strong><span>Validacion funcional, Ventas/Compras y QA final.</span></div>
  <div class="team-card"><strong>Sencia Ale Bryan Daniel</strong><span>DevOps, Docker Compose, GitHub Actions, artifacts y Jenkinsfile.</span></div>
  <div class="team-card"><strong>Yauli Merma Diego Raul</strong><span>Documentacion Scrum, entregables, roadmap, guia y presentacion.</span></div>
</div>
