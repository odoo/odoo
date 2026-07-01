---
layout: default
title: Plan de Proyecto
---

<style>
    
table th {
    background-color: #020d1a !important;
    color: white !important;
}
</style>

# Plan de Proyecto: SCRUM y DevOps – Odoo (Módulo Ventas)

## 1. Objetivo del Proyecto
Implementar un proceso de desarrollo de software que integre la metodología ágil **Scrum** con prácticas **DevOps** automatizadas sobre el proyecto de código abierto **Odoo ([Módulo de Ventas](ArquitecturaModuloVnetas.md))**. El propósito es que el equipo comprenda, analice y ejecute las fases del ciclo de vida del software mediante la refactorización o mejora de este producto.

## 2. Información del Software Seleccionado
* **Nombre del Producto:** Odoo ERP (Open Source).
* **Repositorio:** [https://github.com/roydanpe/odooIPS](https://github.com/roydanpe/odooIPS)
* **Dominio:** Sistema empresarial (ERP/CRM) aplicado al rubro comercial.
* **Complejidad:** Mediana. Se trabajará con el [**Módulo de Ventas**](ArquitecturaModuloVnetas.md), el cual cuenta con más de 10,000 líneas de código (> 10 KLOC).
* **Viabilidad Técnica y Legal:** [GNU Lesser General Public License, version 3 (LGPL-3)](REPORTE_VERIFICACION.md) (verificada para uso académico) e infraestructura DevOps adaptable, permitiendo la implementación de un entorno containerizado basado en [Docker Compose](REPORTE_VERIFICACION.md), facilitando la implementación del pipeline de automatización solicitado.

## 3. Equipo y Metodología de Trabajo
El equipo de trabajo está formado por 5 estudiantes. El rol de **Líder de Equipo** será rotativo por cada Sprint para desarrollar habilidades de liderazgo y responsabilidad.

### Integrantes
* **Apaza Anahua Roydan**.
* **Quiñonez Delgado Aarón Fernando**.
* **Sencia Ale Bryan Daniel**.
* **Yauli Merma Diego Raul**.
* **Sivincha Machaca Saul Andre**.

### Sprint 0 
### Roles y Responsabilidades:

| Integrante | Rol | Responsabilidades |
| --- | --- | --- |
| **Apaza Anahua Roydan** | Líder | Coordinación general, integración del documento final y configuración de herramientas GitHub. |
| **Quiñonez Delgado Aarón Fernando** | Verificación Técnica | Validación de `docker-compose.yml` y cumplimiento de los criterios de licencia MIT. |
| **Sencia Ale Bryan Daniel** | Arquitectura de Código | Delimitación del módulo de Ventas y verificación técnica de la complejidad (>10 KLOC). |
| **Yauli Merma Diego Raul** | Gestión de Documentación | Desarrollo del reporte del Hito 1, consolidación de evidencias y documentación del avance del proyecto Scrum y DevOps. |
| **Sivincha Machaca Saul Andre** | Cronograma Maestro | Planificación de los Sprints de 15 días alineados a los hitos del curso. |

### Sprint 1 
### Roles y Responsabilidades ([ver en github page](sprint1.md)):

| Integrante | Rol | Responsabilidades |
|------------|-----|-------------------|
| **Yauli Merma Diego Raul** | Líder Scrum y Coordinación | Organizar reuniones, supervisar el Sprint, revisar avances, coordinar la integración de tareas y administrar GitHub Projects. |
| **Apaza Anahua Roydan** | Configuración del Entorno | Configurar Odoo, PostgreSQL y Docker Compose; verificar la ejecución local del sistema y resolver problemas de despliegue inicial. |
| **Quiñonez Delgado Aarón Fernando** | Análisis de Arquitectura | Analizar la estructura del módulo *sale*, revisar modelos, vistas XML, dependencias y el flujo funcional del sistema. |
| **Sivincha Machaca Saul Andre** | Gestión de Backlog e Issues | Refinar historias de usuario, crear GitHub Issues, priorizar tareas y organizar el Product Backlog del Sprint. |
| **Sencia Ale Bryan Daniel** | Integración DevOps y Evidencias | Configurar ramas de trabajo, apoyar en GitHub Actions, registrar commits, recopilar evidencias y colaborar en la documentación técnica del Sprint. |

### Sprint 2 
### Roles y Responsabilidades ([ver en github page](sprint2.md)):

| Integrante | Rol Sprint 2 | Responsabilidades |
|------------|-------------|-------------------|
| **Apaza Anahua Roydan** | Desarrollador Backend (Python) | Extender modelos del módulo *sale*, implementar la funcionalidad seleccionada y realizar pruebas básicas de integración. |
| **Sencia Ale Bryan Daniel** | Ingeniero DevOps (CI/CD) | Configurar GitHub Actions, automatizar el despliegue y validar el entorno Docker Compose. |
| **Yauli Merma Diego Raul** | Desarrollador Frontend (XML/UI) | Modificar vistas XML del módulo de ventas e integrar la funcionalidad desarrollada en la interfaz. |
| **Sivincha Machaca Saul Andre** | Especialista QA y Documentación | Ejecutar pruebas funcionales, validar resultados, actualizar documentación y consolidar evidencias del Sprint. |
| **Quiñonez Delgado Aarón Fernando** | Líder de Sprint (Scrum Master) | Coordinar el Sprint, gestionar GitHub Projects, supervisar Issues y consolidar el informe de avance. |

### Sprint 3 
### Roles y Responsabilidades :

| Integrante | Rol | Responsabilidades |
| --- | --- | --- |
| **Apaza Anahua Roydan** |  |  |
| **Quiñonez Delgado Aarón Fernando** |  |  |
| **Sencia Ale Bryan Daniel** |  |  |
| **Yauli Merma Diego Raul** |  |  |
| **Sivincha Machaca Saul Andre** |  |  |

### Sprint 4 
### Roles y Responsabilidades :

| Integrante | Rol | Responsabilidades |
| --- | --- | --- |
| **Apaza Anahua Roydan** |  |  |
| **Quiñonez Delgado Aarón Fernando** |  |  |
| **Sencia Ale Bryan Daniel** |  |  |
| **Yauli Merma Diego Raul** |  |  |
| **Sivincha Machaca Saul Andre** |  |  |

## 4. Herramientas Tecnológicas

| Herramienta | Uso en el Proyecto |
| --- | --- |
| [**GitHub Projects**](https://github.com/users/roydanpe/projects/1) | Gestionar el Product Backlog, armar Sprints y ver el progreso en tiempo real. |
| **GitHub Issues** | Registrar historias de usuario, reportar bugs y documentar decisiones técnicas. |
| **GitHub Actions** | Automatización CI/CD: compilar código, correr pruebas y desplegar a staging. |
| **GitHub Pages** | Publicar el entorno de staging, la documentación técnica y el burndown chart. |
| **Google Meet** | Reuniones virtuales y coordinación del equipo de trabajo. |

## 5. [Cronograma de Sprints e Hitos](cronograma.md)

El cronograma maestro consolida el Sprint 0, los cuatro Sprints de desarrollo, los hitos de evaluación y los entregables esperados para el avance del proyecto.

[Ver cronograma maestro](cronograma.md)


