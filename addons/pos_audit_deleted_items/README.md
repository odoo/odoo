# Auditoría de Eliminaciones en POS

![Odoo Version](https://img.shields.io/badge/Odoo-16.0-blue)
![License](https://img.shields.io/badge/license-LGPL--3-green)
![Status](https://img.shields.io/badge/status-stable-brightgreen)

## Descripción

Módulo completo de auditoría para rastrear y justificar todas las eliminaciones de productos en el Punto de Venta (POS) de Odoo 16.0. Diseñado especialmente para restaurantes que necesitan asegurar que todo lo que se ordena en cocina y barra sea facturado y cobrado.

### Características Principales

✅ **Control Granular por Usuario**
- Habilitar/deshabilitar auditoría individualmente
- Permisos específicos para eliminar registros

✅ **Popup Interactivo en Tiempo Real**
- Aparece automáticamente al eliminar productos
- Justificaciones predeterminadas configurables
- Campo de texto para justificaciones personalizadas

✅ **Trazabilidad Completa**
- Número de pedido
- Producto y cantidad eliminada
- Usuario que eliminó
- Fecha y hora exacta
- Justificación completa

✅ **Reportes y Análisis**
- Vista de lista con filtros avanzados
- Análisis pivot y gráficos
- Exportación a Excel
- Agrupación por usuario, producto, fecha

✅ **Compatible con**
- POS estándar
- POS Restaurant (incluye mesa)
- Modo offline
- Multi-compañía

---

## Capturas de Pantalla

### Popup de Justificación
*(Al eliminar un producto en el POS)*

```
┌─────────────────────────────────────────┐
│ 🔺 Justificación de Eliminación         │
├─────────────────────────────────────────┤
│ Producto: Café Americano                │
│ Cantidad eliminada: 1.00                │
├─────────────────────────────────────────┤
│ Justificaciones rápidas:                │
│ [Cliente cambió de opinión]             │
│ [Error al ingresar el pedido]           │
│ [Producto no disponible]                │
├─────────────────────────────────────────┤
│ Justificación completa:                 │
│ ┌─────────────────────────────────────┐ │
│ │ [Escriba aquí...]                   │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│     [Cancelar] [Confirmar]              │
└─────────────────────────────────────────┘
```

### Reporte de Productos Eliminados

Vista de lista con todos los registros de auditoría, filtros, búsquedas y análisis.

---

## Documentación

- 📘 **[Guía de Instalación](INSTALL.md)** - Instalación paso a paso y configuración inicial
- 📗 **[Manual de Usuario](README_USUARIO.md)** - Para meseros, cajeros y gerentes
- 📕 **[Documentación Técnica](README_TECHNICAL.md)** - Para desarrolladores y técnicos

---

## Instalación Rápida

### Requisitos

- Odoo 16.0 Community o Enterprise
- Módulo `point_of_sale` instalado
- Módulo `pos_restaurant` (opcional, para restaurantes)

### Pasos

1. **Copiar el módulo a tu carpeta de addons:**

   ```bash
   cp -r pos_audit_deleted_items /path/to/odoo/addons/
   ```

2. **Reiniciar Odoo:**

   ```bash
   sudo systemctl restart odoo
   ```

3. **Actualizar lista de aplicaciones:**
   - Apps > Menú > Actualizar lista de Apps

4. **Instalar el módulo:**
   - Apps > Buscar "Auditoría Eliminados POS" > Instalar

5. **Configurar usuarios:**
   - Configuración > Usuarios > [Usuario] > Permisos
   - Activar "Auditar Eliminaciones en POS"

**¡Listo!** El módulo está funcionando.

Para detalles completos, ver [INSTALL.md](INSTALL.md)

---

## Uso Básico

### Para Meseros/Cajeros

1. Trabaje normalmente en el POS
2. Al eliminar un producto, aparecerá un popup
3. Seleccione una justificación rápida o escriba una personalizada
4. Confirme la eliminación
5. ¡Listo! El registro queda guardado automáticamente

### Para Gerentes

1. **Ver reportes:**
   - Punto de Ventas > Reportes > Productos Eliminados

2. **Configurar justificaciones:**
   - Punto de Ventas > Configuración > Justificaciones de Eliminaciones

3. **Configurar permisos de usuarios:**
   - Configuración > Usuarios > [Usuario] > Permisos / Accesos

---

## Configuración

### Habilitar Auditoría para un Usuario

1. Vaya a **Configuración > Usuarios**
2. Seleccione el usuario
3. Pestaña **"Permisos / Accesos"**
4. Grupo **"Auditoría POS"**:
   - ✅ **Auditar Eliminaciones en POS:** Solicita justificación al eliminar
   - ✅ **Puede Eliminar Auditorías POS:** Permite borrar registros de auditoría

### Agregar Justificaciones Personalizadas

1. **Punto de Ventas > Configuración > Justificaciones de Eliminaciones**
2. Clic en **"Crear"**
3. Complete:
   - **Justificación:** Texto que aparecerá en el POS
   - **Secuencia:** Orden de aparición (menor = primero)
   - **Activo:** ✅ Marcado
4. **Guardar**

---

## Preguntas Frecuentes

**P: ¿Funciona sin internet?**
R: Sí, el módulo funciona completamente offline. Los registros se sincronizan cuando hay conexión.

**P: ¿Puedo desactivar la auditoría temporalmente?**
R: Sí, desactive "Auditar Eliminaciones en POS" para usuarios específicos.

**P: ¿Afecta el rendimiento del POS?**
R: No, el impacto es mínimo y imperceptible.

**P: ¿Puedo exportar los datos?**
R: Sí, desde el reporte use Acción > Exportar.

**P: ¿Es compatible con otros módulos del POS?**
R: Sí, está diseñado para ser compatible con módulos estándar y de terceros.

Para más preguntas, ver [README_USUARIO.md](README_USUARIO.md#preguntas-frecuentes)

---

## Soporte

### Desarrollado por

**Jbnegoc SPA**
- Web: https://www.jbnegoc.cl
- Email: info@jbnegoc.cl

### Reportar Problemas

Si encuentra un bug o tiene una sugerencia:

1. Recopile información del error
2. Contacte a info@jbnegoc.cl con:
   - Versión de Odoo
   - Descripción del problema
   - Pasos para reproducir
   - Logs de error (si aplica)

---

## Licencia

**LGPL-3**

© 2026 Jbnegoc SPA - Todos los derechos reservados

Este módulo es software libre: puede redistribuirlo y/o modificarlo bajo los términos de la Licencia Pública General Reducida de GNU (LGPL) versión 3.

---

## Changelog

### v16.0.1.0.0 (2026-01-15)

**Características:**
- ✅ Sistema completo de auditoría de eliminaciones
- ✅ Popup interactivo con justificaciones
- ✅ Justificaciones predeterminadas configurables
- ✅ Reportes y análisis completos
- ✅ Control granular de permisos por usuario
- ✅ Compatible con POS estándar y Restaurant
- ✅ Funcionamiento offline
- ✅ Multi-compañía

**Inicial Release**
- Primera versión estable del módulo
- Documentación completa incluida
- 10 justificaciones predeterminadas
- Probado en producción

---

## Agradecimientos

Gracias a la comunidad de Odoo por el framework y la documentación.

---

**¡Gracias por elegir nuestro módulo!**

Si le ha sido útil, considere:
- ⭐ Dejar una reseña
- 📧 Recomendarnos a colegas
- 💬 Compartir feedback para mejoras

---

*Última actualización: 15 de Enero, 2026*
