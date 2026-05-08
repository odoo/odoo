# Plan de Proyecto: Scrum y DevOps – Odoo (Módulo Ventas)

## 1. Objetivo del Proyecto
Implementar un proceso de desarrollo de software que integre la metodología ágil **Scrum** con prácticas **DevOps** automatizadas sobre el proyecto de código abierto **Odoo (Módulo Ventas)**[cite: 7, 8]. [cite_start]El propósito es que el equipo comprenda, analice y ejecute las fases del ciclo de vida del software mediante la refactorización o mejora de este producto[cite: 8].

## 2. Información del Software Seleccionado
* [cite_start]**Nombre del Producto:** Odoo ERP (Open Source)[cite: 10, 15].
* **Repositorio:** [Insertar Link del Fork de GitHub aquí].
* [cite_start]**Licencia:** **MIT** verificada, permitiendo fork, modificación y uso académico sin restricciones[cite: 14].
* [cite_start]**Dominio:** Sistema empresarial (ERP/CRM) aplicado al rubro comercial[cite: 15].
* **Complejidad:** Mediana. [cite_start]Se trabajará con el **Módulo de Ventas**, el cual cuenta con más de **10,000 líneas de código (> 10 KLOC)**[cite: 18].
* [cite_start]**Infraestructura DevOps:** El proyecto incluye **Docker Compose**, lo que facilita la configuración del pipeline de automatización solicitado[cite: 19].

## 3. Equipo y Metodología de Trabajo
[cite_start]El equipo de trabajo está formado por 5 estudiantes[cite: 36, 40]. [cite_start]El rol de **Líder de Equipo** será rotativo por cada Sprint para desarrollar habilidades de liderazgo y responsabilidad[cite: 41, 42, 46].

### Roles y Responsabilidades (Sprint 0):
* [cite_start]**Líder (Tú):** Coordinación general, integración del documento final y configuración de herramientas GitHub[cite: 42].
* [cite_start]**Aarón (Verificación Técnica):** Validación de `docker-compose.yml` y cumplimiento de los criterios de licencia MIT[cite: 14, 19].
* [cite_start]**Daniel (Arquitectura de Código):** Delimitación del módulo de Ventas y verificación técnica de la complejidad (>10 KLOC)[cite: 18].
* [cite_start]**Diego (Gestión de Backlog):** Creación del **Product Backlog** inicial con 10-15 Historias de Usuario en **GitHub Issues**[cite: 26].
* [cite_start]**Nero (Cronograma Maestro):** Planificación de los Sprints de 15 días alineados a los hitos del curso[cite: 35].

## 4. Herramientas Tecnológicas
| Herramienta | ¿Para qué sirve en el proyecto? |
| :--- | :--- |
| **GitHub Projects** | [cite_start]Gestionar el Product Backlog, armar Sprints y ver el progreso en tiempo real[cite: 26]. |
| **GitHub Issues** | [cite_start]Registrar historias de usuario, reportar bugs y documentar decisiones técnicas[cite: 26]. |
| **GitHub Actions** | [cite_start]Automatización CI/CD: compilar código, correr pruebas y desplegar a staging[cite: 26]. |
| **GitHub Pages** | [cite_start]Publicar el entorno de staging, la documentación técnica y el burndown chart[cite: 26]. |

## 5. Cronograma de Sprints e Hitos
[cite_start]Cada Sprint tiene una duración establecida de **15 días calendario**[cite: 35].

* [cite_start]**Hito 1 (15% del trabajo): 13.MAY.2026**[cite: 29].
    * [cite_start]**Entregable (Sprint 0):** Plan de proyecto, cronograma y presentación del producto seleccionado (vía GitHub Projects y Pages)[cite: 30].
* [cite_start]**Hito 2 (60% del trabajo): 10.JUN.2026**[cite: 31].
    * [cite_start]**Entregable (Sprint 1-2):** Software funcionando con integración CI/CD DevOps y marco Scrum activo[cite: 32].
* [cite_start]**Hito 3 (100% del trabajo): 13.JUL.2026**[cite: 33].
    * [cite_start]**Entregable (Sprint 3-4):** Mejoras al software, documentación técnica completa y artículo final en formato IEEE[cite: 34].
