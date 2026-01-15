# Manual de Usuario - Auditoría de Eliminaciones en POS

**Módulo:** Auditoría Eliminados POS Restaurante
**Versión:** 16.0.1.0.0
**Desarrollado por:** Jbnegoc SPA

---

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [Configuración Inicial](#configuración-inicial)
3. [Uso Diario del POS](#uso-diario-del-pos)
4. [Consulta de Reportes](#consulta-de-reportes)
5. [Gestión de Justificaciones](#gestión-de-justificaciones)
6. [Preguntas Frecuentes](#preguntas-frecuentes)

---

## Introducción

### ¿Qué es este módulo?

Este módulo permite llevar un registro completo y detallado de todos los productos que se eliminan de las órdenes en el Punto de Venta (POS). Es especialmente útil para restaurantes donde se necesita controlar que todo lo que se ordena en cocina sea facturado y cobrado.

### ¿Para quién es este manual?

Este manual está diseñado para:

- **Meseros/Garzones:** Aprenderán cómo justificar eliminaciones de productos
- **Cajeros:** Entenderán cómo funciona el sistema de auditoría
- **Gerentes/Supervisores:** Sabrán cómo revisar los reportes y configurar el sistema

### Beneficios del Módulo

✅ **Trazabilidad Total:** Cada eliminación queda registrada con usuario, fecha/hora y justificación
✅ **Control de Desperdicios:** Identificar patrones de eliminaciones
✅ **Auditoría Financiera:** Verificar que todo lo preparado sea cobrado
✅ **Mejora de Procesos:** Identificar errores comunes y capacitar al personal

---

## Configuración Inicial

### Para Gerentes y Administradores

#### Paso 1: Habilitar Auditoría para Usuarios

1. Vaya a **Configuración** (ícono de engranaje en la esquina superior derecha)
2. Seleccione **Usuarios y Compañías > Usuarios**
3. Haga clic en el usuario que desea configurar
4. Vaya a la pestaña **"Permisos / Accesos"**
5. Busque el grupo **"Auditoría POS"** (aparece si el usuario tiene permisos de POS)
6. Active las siguientes opciones según corresponda:

   | Opción | Descripción | ¿Quién debería tenerlo? |
   |--------|-------------|------------------------|
   | **Auditar Eliminaciones en POS** | Cuando está activo, el sistema solicitará justificación al eliminar productos | Meseros, cajeros, todos los usuarios del POS |
   | **Puede Eliminar Auditorías POS** | Permite borrar registros de auditoría del sistema | Solo gerentes o supervisores |

7. Haga clic en **Guardar**

**Ejemplo de configuración típica:**

```
👤 Juan Pérez (Mesero)
   ✅ Auditar Eliminaciones en POS: ACTIVADO
   ❌ Puede Eliminar Auditorías POS: DESACTIVADO

👤 María González (Gerente)
   ✅ Auditar Eliminaciones en POS: ACTIVADO
   ✅ Puede Eliminar Auditorías POS: ACTIVADO
```

#### Paso 2: Configurar Justificaciones Predeterminadas

Las justificaciones predeterminadas son frases rápidas que los usuarios pueden seleccionar al eliminar un producto, agilizando el proceso.

1. Vaya a **Punto de Ventas**
2. Menú **Configuración**
3. Seleccione **Justificaciones de Eliminaciones**

**Justificaciones que vienen preconfiguradas:**

- Cliente cambió de opinión
- Error al ingresar el pedido
- Producto no disponible en cocina
- Producto defectuoso o en mal estado
- Cliente canceló el pedido completo
- Tiempo de espera excesivo
- Modificación de la orden por alergias
- Duplicado por error
- Precio incorrecto - ajuste necesario
- Cortesía de la casa

**Para agregar una nueva justificación:**

1. Haga clic en **Crear**
2. Complete los campos:
   - **Justificación:** Texto que aparecerá en el POS (ej: "Porción muy pequeña")
   - **Secuencia:** Orden de aparición (menor número = aparece primero)
   - **Activo:** Marcar para que esté disponible
   - **Descripción:** Nota interna sobre cuándo usar esta justificación
3. Haga clic en **Guardar**

**Para editar o desactivar una justificación:**

1. Haga clic en la justificación que desea modificar
2. Modifique los campos necesarios
3. Para desactivarla (sin borrarla), desmarque **Activo**
4. Guarde los cambios

**Para reordenar justificaciones:**

1. En la vista de lista, use el ícono de "manitas" (⣿) a la izquierda
2. Arrastre las justificaciones al orden deseado

---

## Uso Diario del POS

### Para Meseros y Cajeros

#### Escenario 1: Eliminar un Producto Completo

**Situación:** Un cliente ordenó un café, pero decidió cancelarlo antes de que se prepare.

**Pasos:**

1. **En el POS, seleccione la orden del cliente**

2. **Haga clic en el producto que desea eliminar**
   - En la vista de lista de productos de la orden, haga clic en la "X" o botón eliminar

3. **Aparecerá un popup con el título "Justificación de Eliminación"**

   El popup mostrará:
   ```
   ┌─────────────────────────────────────┐
   │ 🔺 Justificación de Eliminación     │
   ├─────────────────────────────────────┤
   │ Producto: Café Americano            │
   │ Cantidad eliminada: 1.00            │
   ├─────────────────────────────────────┤
   │ Justificaciones rápidas:            │
   │ [Cliente cambió de opinión]         │
   │ [Error al ingresar el pedido]       │
   │ [Producto no disponible]            │
   │ ...más opciones...                  │
   ├─────────────────────────────────────┤
   │ Justificación completa:             │
   │ ┌─────────────────────────────────┐ │
   │ │                                 │ │
   │ │                                 │ │
   │ └─────────────────────────────────┘ │
   ├─────────────────────────────────────┤
   │ ⚠️ Esta eliminación quedará         │
   │ registrada con tu nombre            │
   ├─────────────────────────────────────┤
   │     [Cancelar] [Confirmar]          │
   └─────────────────────────────────────┘
   ```

4. **Seleccione una justificación rápida** (opcional)
   - Haga clic en uno de los botones de justificaciones
   - El texto se agregará automáticamente al cuadro de texto

5. **O escriba una justificación personalizada**
   - Escriba directamente en el cuadro de texto
   - Mínimo 5 caracteres requeridos

6. **Haga clic en "Confirmar Eliminación"**
   - El producto se eliminará de la orden
   - La justificación quedará registrada en el sistema

7. **Si cambia de opinión**
   - Haga clic en "Cancelar"
   - El producto NO se eliminará

#### Escenario 2: Disminuir la Cantidad de un Producto

**Situación:** Un cliente ordenó 3 pizzas, pero solo quiere 2.

**Pasos:**

1. **Seleccione el producto en la orden**

2. **Cambie la cantidad:**
   - Haga clic en el campo de cantidad
   - Escriba "2" (la nueva cantidad)
   - O use los botones +/- para ajustar

3. **Aparecerá el popup de justificación**
   - Mostrará: "Cantidad eliminada: 1.00"
   - Es decir, está eliminando 1 pizza (3 - 2 = 1)

4. **Siga los mismos pasos del Escenario 1** para justificar

**Ejemplos de justificaciones comunes:**

```
✅ Cliente cambió de opinión
✅ Error al ingresar el pedido - cliente pidió 2, no 3
✅ Cliente redujo pedido por presupuesto
✅ Mesa se redujo de 4 a 2 personas
```

#### Consejos para Justificaciones

**✅ BUENAS justificaciones:**

- "Cliente cambió de opinión después de ver el menú"
- "Error mío al ingresar, cliente pidió solo 2 empanadas"
- "Producto no disponible en cocina - se agotó el ingrediente"
- "Cliente tiene alergia al maní, necesita cambiar plato"

**❌ MALAS justificaciones:**

- "no sé" (muy vaga)
- "error" (no explica el error)
- "." (no es una justificación válida)
- "asdf" (sin sentido)

**Importante:**
- Sea honesto en las justificaciones
- Sea específico cuando sea posible
- Use las justificaciones rápidas para agilizar
- No invente justificaciones falsas

#### ¿Qué pasa si cancelo el popup?

Si hace clic en "Cancelar" en el popup:
- ❌ El producto NO se eliminará
- ❌ La cantidad NO cambiará
- ✅ La orden permanecerá como estaba

Esto es útil si se equivocó y no quería eliminar el producto.

#### Usuarios sin Auditoría

Si su usuario NO tiene activada la auditoría (`Auditar Eliminaciones en POS = No`):

- ✅ Puede eliminar productos normalmente
- ❌ NO aparecerá el popup de justificación
- ❌ NO se registrarán las eliminaciones

Esto se usa típicamente para gerentes que hacen correcciones y no necesitan justificarlas.

---

## Consulta de Reportes

### Para Gerentes y Supervisores

#### Acceder al Reporte de Productos Eliminados

1. Vaya a **Punto de Ventas**
2. Menú **Reportes**
3. Seleccione **Productos Eliminados**

#### Vista de Lista

La vista principal muestra todos los productos eliminados en formato de tabla:

| Fecha/Hora | Pedido | Producto | Cantidad | Usuario | Justificación |
|------------|--------|----------|----------|---------|---------------|
| 2026-01-15 14:30 | Order 00003-001-0001 | Café Americano | 1.00 | Juan Pérez | Cliente cambió de... |
| 2026-01-15 14:45 | Order 00003-001-0002 | Pizza Margarita | 2.00 | María López | Error al ingresar... |

**Códigos de Color:**

- 🟡 **Amarillo:** Cantidad eliminada > 2 unidades
- 🔴 **Rojo:** Cantidad eliminada > 5 unidades (alerta)

#### Filtros Rápidos

En la parte superior, puede usar filtros predefinidos:

- **Hoy:** Solo eliminaciones de hoy
- **Esta Semana:** Últimos 7 días
- **Este Mes:** Mes actual (filtro por defecto)
- **Cantidad > 5:** Solo eliminaciones grandes
- **Con Mesa:** Solo registros con mesa asignada (restaurante)

#### Búsquedas Personalizadas

Haga clic en el campo de búsqueda para buscar por:

- Número de pedido
- Nombre del producto
- Usuario que eliminó
- Texto en la justificación
- Punto de venta específico

**Ejemplo:**
```
Buscar: "Juan Pérez"
→ Muestra todas las eliminaciones de Juan

Buscar: "Pizza"
→ Muestra todas las eliminaciones de productos con "Pizza" en el nombre
```

#### Agrupar Resultados

Use el menú "Agrupar por" para analizar los datos:

- **Por Usuario:** Ver quién elimina más productos
- **Por Producto:** Ver qué productos se eliminan más
- **Por Punto de Venta:** Comparar diferentes POS
- **Por Fecha:** Ver tendencias por día/semana/mes

**Ejemplo de uso:**
```
1. Haga clic en "Agrupar por"
2. Seleccione "Usuario"
3. Verá algo como:

   Juan Pérez (15 eliminaciones)
   ↳ Café Americano - 5 veces
   ↳ Pizza Margarita - 10 veces

   María López (8 eliminaciones)
   ↳ Empanada de Queso - 8 veces
```

#### Ver Detalle de un Registro

1. Haga clic en cualquier línea de la lista
2. Se abrirá la vista de detalle con información completa:

   ```
   ┌─────────────────────────────────────────┐
   │ 📄 Detalle de Producto Eliminado        │
   ├─────────────────────────────────────────┤
   │ [Ver Pedido] [Ver Producto]             │
   ├─────────────────────────────────────────┤
   │ INFORMACIÓN DEL PEDIDO                  │
   │ • Pedido: Order 00003-001-0001          │
   │ • Sesión: Apertura mañana 15/01         │
   │ • Punto de Venta: POS Restaurant 1      │
   │ • Mesa: Mesa 5                          │
   │                                         │
   │ INFORMACIÓN DE LA ELIMINACIÓN           │
   │ • Fecha/Hora: 15/01/2026 14:30:25       │
   │ • Usuario: Juan Pérez                   │
   │                                         │
   │ PRODUCTO ELIMINADO                      │
   │ • Producto: Café Americano              │
   │ • Código: CAF-001                       │
   │ • Cantidad: 1.00                        │
   │ • Precio Unit: $ 2,500                  │
   │ • Subtotal: $ 2,500                     │
   │                                         │
   │ JUSTIFICACIÓN COMPLETA                  │
   │ ┌─────────────────────────────────────┐ │
   │ │ Cliente cambió de opinión después   │ │
   │ │ de ver que el café demora 10        │ │
   │ │ minutos y tiene prisa               │ │
   │ └─────────────────────────────────────┘ │
   └─────────────────────────────────────────┘
   ```

3. Desde aquí puede:
   - **Ver Pedido:** Ir al pedido completo del POS
   - **Ver Producto:** Ir a la ficha del producto

#### Eliminar Registros de Auditoría

**Requisito:** Usuario debe tener activado "Puede Eliminar Auditorías POS"

##### Eliminar un Registro Individual

1. Abra el detalle del registro
2. Haga clic en el menú "Acción" (tres puntos verticales)
3. Seleccione "Eliminar"
4. Confirme la eliminación

##### Eliminar Múltiples Registros

1. En la vista de lista, marque los checkboxes de los registros a eliminar
2. Haga clic en el menú "Acción" en la parte superior
3. Seleccione "Eliminar"
4. Confirme la eliminación

**¿Por qué eliminar registros?**
- Para mantener la base de datos limpia
- Después de revisar y aprobar las eliminaciones
- Para eliminar registros de prueba

**Importante:** ⚠️ La eliminación es permanente y no se puede deshacer.

#### Vista de Análisis (Pivot)

Cambie a la vista "Pivot" para análisis avanzados:

1. Haga clic en el ícono de tabla dinámica (cuadrícula) en la parte superior
2. Verá una tabla dinámica con:
   - Filas: Usuarios
   - Columnas: Fechas
   - Valores: Cantidad eliminada, Subtotal

3. Puede arrastrar campos para reorganizar el análisis

**Ejemplo de análisis:**
```
Pregunta: ¿Cuánto dinero en productos se eliminó esta semana?

1. Vista Pivot
2. Agrupar por "Fecha" (día)
3. Ver medida "Subtotal"
4. Resultado: Total de $ semanal en eliminaciones
```

#### Vista de Gráficos

Cambie a la vista "Gráfico" para visualizaciones:

1. Haga clic en el ícono de gráfico (barras) en la parte superior
2. Tipos de gráfico disponibles:
   - Barras
   - Líneas
   - Pastel

**Ejemplo:**
```
Gráfico de barras:
Eje X: Usuarios
Eje Y: Cantidad eliminada

Muestra visualmente quién elimina más productos
```

---

## Gestión de Justificaciones

### Crear Nuevas Justificaciones

Como gerente, puede agregar justificaciones que los usuarios usarán:

1. **Punto de Ventas > Configuración > Justificaciones de Eliminaciones**
2. **Clic en "Crear"**
3. **Complete:**
   - **Justificación:** "Plato devuelto por estar frío"
   - **Secuencia:** 55 (aparecerá en orden 5.5)
   - **Activo:** ✅ Marcado
   - **Descripción:** "Usar cuando el cliente devuelve el plato por temperatura"
4. **Guardar**

### Editar Justificaciones Existentes

Puede editar directamente en la lista:

1. Haga clic en el campo que desea cambiar
2. Modifique el texto
3. Presione Enter o haga clic fuera para guardar

### Desactivar Justificaciones

Si una justificación ya no se usa:

1. Desmarque el campo "Activo" (toggle)
2. La justificación desaparecerá del POS pero los registros históricos se mantienen

### Buenas Prácticas para Justificaciones

**✅ Recomendado:**
- Frases claras y específicas
- Cubrir los casos más comunes
- Máximo 10-15 justificaciones activas (para no saturar)
- Usar lenguaje neutral y profesional

**❌ Evitar:**
- Justificaciones demasiado genéricas ("Error", "Problema")
- Demasiadas opciones que confundan al usuario
- Frases muy largas (máximo 50 caracteres recomendado)

---

## Preguntas Frecuentes

### Preguntas de Usuarios (Meseros/Cajeros)

**P: ¿Qué pasa si me equivoco en la justificación?**

R: No puede editar la justificación una vez confirmada. Si fue un error grave, comuníquese con su gerente quien puede revisar y eliminar el registro si es necesario.

---

**P: ¿Puedo eliminar varios productos a la vez?**

R: Sí, cada eliminación solicitará su propia justificación individual. Si elimina 3 productos diferentes, aparecerá el popup 3 veces.

---

**P: ¿El popup me bloquea el trabajo?**

R: Sí, mientras el popup esté abierto no puede continuar con otras acciones. Esto es intencional para asegurar que toda eliminación tenga justificación. Es muy rápido: seleccione una justificación predeterminada y confirme.

---

**P: ¿Qué pasa si hay un corte de internet?**

R: El sistema funciona offline. Las justificaciones se guardarán en el dispositivo y se sincronizarán automáticamente cuando finalice la orden y haya conexión.

---

**P: ¿Mis justificaciones son privadas?**

R: No, las justificaciones son visibles para gerentes y supervisores en los reportes. Son parte del sistema de auditoría de la empresa.

---

### Preguntas de Gerentes

**P: ¿Cómo identifico patrones de eliminación problemáticos?**

R: Use la vista de análisis:
1. Reporte > Vista Pivot
2. Agrupar por Usuario y Producto
3. Identificar usuarios con muchas eliminaciones del mismo producto
4. Revisar las justificaciones para ver si hay un patrón

---

**P: ¿Puedo exportar los datos a Excel?**

R: Sí:
1. Vista de lista de Productos Eliminados
2. Clic en "Acción" (menú superior)
3. Seleccione "Exportar"
4. Elija los campos a exportar
5. Descargue el archivo Excel

---

**P: ¿Cómo capacito a nuevos empleados?**

R: Sugerencia de capacitación:
1. Explique la importancia del control de eliminaciones
2. Muestre cómo aparece el popup (haga una demo en vivo)
3. Explique que deben ser honestos en las justificaciones
4. Practique 2-3 escenarios comunes
5. Recuerde que pueden usar justificaciones rápidas

---

**P: ¿Puedo desactivar la auditoría temporalmente?**

R: Sí, pero por usuario:
1. Configuración > Usuarios
2. Desactive "Auditar Eliminaciones en POS" para ese usuario
3. El usuario podrá eliminar sin popup
4. Reactive cuando sea necesario

No es recomendable desactivar para todos, solo en casos muy específicos.

---

**P: ¿Cuánto espacio ocupan los registros de auditoría?**

R: Muy poco. Cada registro ocupa aproximadamente 1-2 KB. Con 1000 eliminaciones al mes = ~2 MB.

Recomendación: Limpiar registros cada 6-12 meses después de revisarlos.

---

**P: ¿El módulo afecta la velocidad del POS?**

R: No. El popup aparece instantáneamente y la sincronización es en segundo plano. No hay impacto perceptible en el rendimiento.

---

## Mejores Prácticas de Uso

### Para Meseros

1. ✅ **Sea rápido:** Use las justificaciones predeterminadas cuando apliquen
2. ✅ **Sea honesto:** Las justificaciones sirven para mejorar, no para castigar
3. ✅ **Sea específico:** Si escribe personalizado, explique brevemente el motivo
4. ✅ **Revise antes de eliminar:** Asegúrese de que realmente quiere eliminar el producto

### Para Gerentes

1. ✅ **Revise reportes semanalmente:** Identifique patrones y problemas
2. ✅ **Capacite basándose en datos:** Use los reportes para detectar necesidades de capacitación
3. ✅ **Mantenga justificaciones actualizadas:** Agregue nuevas según necesidades reales
4. ✅ **No use como castigo:** Use la información para mejorar procesos
5. ✅ **Limpie registros periódicamente:** Después de revisar, elimine registros antiguos

### Para el Restaurante

1. ✅ **Comunicación cocina-mesero:** Reducir eliminaciones por productos no disponibles
2. ✅ **Capacitación continua:** Reducir errores de ingreso
3. ✅ **Análisis de tendencias:** Identificar productos problemáticos
4. ✅ **Feedback al personal:** Compartir estadísticas positivas y áreas de mejora

---

## Ejemplos de Casos de Uso Reales

### Caso 1: Identificar Producto Problemático

**Situación:** El gerente nota muchas eliminaciones de "Ensalada César"

**Análisis:**
1. Reportes > Productos Eliminados
2. Agrupar por Producto
3. Ver que "Ensalada César" tiene 25 eliminaciones este mes
4. Revisar justificaciones: Mayoría dicen "Producto muy pequeño" o "Cliente esperaba más cantidad"

**Acción:**
- Revisar el tamaño de la porción
- Ajustar precio o cantidad
- Actualizar foto del menú
- Capacitar a meseros para explicar el tamaño al cliente

**Resultado:** Eliminaciones de ese producto disminuyen

---

### Caso 2: Detectar Necesidad de Capacitación

**Situación:** Un nuevo mesero tiene muchas eliminaciones con justificación "Error al ingresar el pedido"

**Análisis:**
1. Filtrar por Usuario: "Pedro Nuevo"
2. Ver 15 eliminaciones en 1 semana
3. Todas por errores de ingreso

**Acción:**
- Sesión de capacitación 1-a-1 con el mesero
- Repasar cómo usar correctamente el POS
- Asignarle un mentor por 1 semana

**Resultado:** Errores disminuyen significativamente

---

### Caso 3: Auditoría Financiera

**Situación:** El dueño quiere saber cuánto dinero se "pierde" en eliminaciones

**Análisis:**
1. Reportes > Productos Eliminados
2. Vista Pivot
3. Ver medida "Subtotal"
4. Período: Este Mes

**Resultado:**
```
Enero 2026:
- Total eliminaciones: $145,000
- Principal causa: "Cliente cambió de opinión" (60%)
- Estrategia: Implementar política de confirmación verbal antes de enviar a cocina
```

---

## Soporte y Contacto

### ¿Necesita Ayuda?

**Soporte Técnico:**
- Email: info@jbnegoc.cl
- Web: https://www.jbnegoc.cl/soporte

**Capacitación:**
- Solicite sesiones de capacitación para su equipo
- Material adicional disponible en nuestro sitio web

**Desarrollo por:**
Jbnegoc SPA - Soluciones ERP para Restaurantes

---

**Fin del Manual de Usuario**

Versión del documento: 1.0
Fecha: Enero 2026

© 2026 Jbnegoc SPA - Todos los derechos reservados
