---
layout: default
title: Historial de cambios
---

[Volver al portal](index.html)

# Historial de cambios

Resumen de los principales avances del proyecto por sprint. El detalle y las evidencias se conservan en la [documentación del portal](docs/README.html).

## Sprint 0 — Planificación y selección

- Se seleccionó Odoo Community como producto de trabajo y se delimitó el módulo de Ventas.
- Se definieron el equipo, el alcance, el cronograma y el backlog inicial.
- Se verificaron la viabilidad técnica, la licencia y la infraestructura base.

## Sprint 1 — Análisis y configuración

- Se preparó el entorno con Odoo, PostgreSQL y Docker Compose.
- Se documentaron la arquitectura, las dependencias, los modelos y las vistas de Ventas.
- Se refinó el backlog y se organizaron las primeras tareas técnicas.

## Sprint 2 — Implementación inicial y CI/CD

- Se creó el módulo `validacion_descuento_maximo` con la regla inicial de control de descuentos.
- Se incorporaron el estado de revisión, la integración en la interfaz y las pruebas del módulo.
- Se configuró el flujo inicial de integración continua con GitHub Actions.

## Sprint 3 — Estabilización y mejora funcional

- El control se convirtió en un flujo de aprobación sin pérdida de la transacción.
- Se añadieron un límite configurable por compañía, el rol de supervisor y la aprobación autorizada.
- Se reforzaron las pruebas automatizadas, el pipeline y la documentación técnica.

## Sprint 4 — Cierre documental y publicación

- Se consolidó el portal de GitHub Pages con sprints, evidencias, burndown y material de defensa.
- Se realizó el cierre de QA, DevOps y trazabilidad del proyecto.
- Se incorporaron este historial, el [roadmap](ROADMAP.html) y la [guía de instalación](docs/instalacion.html).
