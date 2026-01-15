# Guía de Instalación y Configuración
## Auditoría de Eliminaciones en POS

**Módulo:** pos_audit_deleted_items
**Versión:** 16.0.1.0.0
**Desarrollado por:** Jbnegoc SPA

---

## Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Instalación del Módulo](#instalación-del-módulo)
3. [Configuración Inicial](#configuración-inicial)
4. [Verificación de la Instalación](#verificación-de-la-instalación)
5. [Configuración de Usuarios](#configuración-de-usuarios)
6. [Personalización de Justificaciones](#personalización-de-justificaciones)
7. [Pruebas Funcionales](#pruebas-funcionales)
8. [Desinstalación](#desinstalación)
9. [Solución de Problemas](#solución-de-problemas)

---

## Requisitos Previos

### Versión de Odoo

✅ **Requerido:** Odoo 16.0 Community Edition o Enterprise Edition

Para verificar su versión de Odoo:

1. Vaya a la página principal de Odoo
2. En la esquina inferior derecha verá: "Powered by Odoo - v16.0"

O desde terminal:
```bash
./odoo-bin --version
# Debe mostrar: Odoo Server 16.0
```

### Módulos Dependientes

El módulo requiere que los siguientes módulos estén instalados:

| Módulo | Estado | Descripción |
|--------|--------|-------------|
| `point_of_sale` | ✅ Obligatorio | Módulo base del POS |
| `pos_restaurant` | ⭕ Opcional | Para funcionalidad de restaurante con mesas |

**Verificar módulos instalados:**

1. Vaya a **Apps** (Aplicaciones)
2. Elimine el filtro "Apps" en el buscador
3. Busque "point_of_sale" - debe estar instalado
4. Busque "pos_restaurant" - instalado solo si tiene restaurante

### Permisos de Usuario

Necesita ser **Administrador** para instalar el módulo.

### Requisitos Técnicos

- **Python:** No se requieren librerías adicionales de Python
- **JavaScript:** El navegador debe soportar ES5 (todos los navegadores modernos)
- **Base de Datos:** Cualquier BD soportada por Odoo 16 (PostgreSQL recomendado)

---

## Instalación del Módulo

### Método 1: Instalación desde Archivo (Recomendado)

#### Paso 1: Copiar el Módulo

1. **Copie la carpeta completa del módulo** a su directorio de addons de Odoo:

   ```bash
   # Si Odoo está en /opt/odoo/
   cp -r pos_audit_deleted_items /opt/odoo/addons/

   # O si usa una instalación personalizada
   cp -r pos_audit_deleted_items /path/to/your/odoo/addons/
   ```

2. **Verifique la estructura:**

   ```bash
   ls -la /opt/odoo/addons/pos_audit_deleted_items/

   # Debe ver:
   # __init__.py
   # __manifest__.py
   # models/
   # static/
   # views/
   # security/
   # data/
   ```

3. **Asigne permisos correctos:**

   ```bash
   # El usuario que ejecuta Odoo debe tener permisos de lectura
   chown -R odoo:odoo /opt/odoo/addons/pos_audit_deleted_items
   chmod -R 755 /opt/odoo/addons/pos_audit_deleted_items
   ```

#### Paso 2: Actualizar Lista de Aplicaciones

1. **Reinicie el servidor de Odoo:**

   ```bash
   # Con systemd
   sudo systemctl restart odoo

   # O si usa el script directamente
   sudo service odoo restart
   ```

2. **Active el Modo Desarrollador:**

   - Vaya a **Configuración** (ícono de engranaje)
   - En la parte inferior, haga clic en "Activate the developer mode"
   - O agregue `?debug=1` a la URL

3. **Actualice la lista de aplicaciones:**

   - Vaya a **Apps** (Aplicaciones)
   - Haga clic en el menú superior derecho (tres puntos)
   - Seleccione **"Actualizar lista de Apps"**
   - Haga clic en **"Actualizar"** en el popup

   ![Actualizar Apps](https://via.placeholder.com/600x200/4CAF50/FFFFFF?text=Apps+>+Actualizar+Lista)

#### Paso 3: Instalar el Módulo

1. **Busque el módulo:**

   - En **Apps**, elimine el filtro "Apps" del buscador
   - Escriba: "Auditoría Eliminados POS" o "pos_audit"

2. **Instale:**

   - Haga clic en el botón **"Instalar"** del módulo
   - Espere a que complete (puede tomar 30-60 segundos)

3. **Confirme la instalación:**

   - Verá un mensaje de éxito
   - El módulo aparecerá marcado como "Instalado"

### Método 2: Instalación desde Terminal (Avanzado)

Si tiene acceso al terminal del servidor:

```bash
# Copiar módulo
cp -r pos_audit_deleted_items /opt/odoo/addons/

# Instalar módulo directamente
./odoo-bin -c /etc/odoo/odoo.conf -d nombre_base_datos -i pos_audit_deleted_items --stop-after-init

# Reiniciar servicio
sudo systemctl restart odoo
```

---

## Configuración Inicial

### Paso 1: Verificar Instalación de Datos Iniciales

El módulo crea automáticamente:

- ✅ 10 justificaciones predeterminadas
- ✅ Grupos de seguridad
- ✅ Reglas de acceso

**Verificar justificaciones creadas:**

1. Vaya a **Punto de Ventas > Configuración > Justificaciones de Eliminaciones**
2. Debe ver 10 justificaciones como:
   - Cliente cambió de opinión
   - Error al ingresar el pedido
   - Producto no disponible en cocina
   - etc.

Si no aparecen, puede deberse a que los datos no se cargaron. Solución:

```bash
# Reinstalar con actualización de datos
./odoo-bin -c odoo.conf -d nombre_bd -u pos_audit_deleted_items --stop-after-init
```

### Paso 2: Configurar Permisos de Base (Primer Uso)

#### Configurar Usuario Gerente

1. **Vaya a Configuración > Usuarios y Compañías > Usuarios**

2. **Seleccione su usuario (o un usuario gerente)**

3. **Pestaña "Permisos / Accesos":**

   - Busque el grupo **"Auditoría POS"**
   - Active ambas opciones:
     - ✅ Auditar Eliminaciones en POS
     - ✅ Puede Eliminar Auditorías POS

4. **Guarde** el usuario

#### Configurar Usuario de Prueba

Para hacer pruebas, configure un usuario con auditoría habilitada:

1. Cree o edite un usuario de prueba
2. Asigne permisos de POS:
   - Punto de Venta / Usuario
3. En "Auditoría POS":
   - ✅ Auditar Eliminaciones en POS
   - ❌ Puede Eliminar Auditorías POS (desactivado)

---

## Verificación de la Instalación

### Checklist de Verificación

Marque cada ítem para confirmar que todo está correcto:

#### ✅ Backend (Odoo)

- [ ] El módulo aparece como "Instalado" en Apps
- [ ] Menú **"Punto de Ventas > Configuración"** muestra "Justificaciones de Eliminaciones"
- [ ] Menú **"Punto de Ventas > Reportes"** muestra "Productos Eliminados"
- [ ] Vista de usuarios muestra campos de "Auditoría POS" en la pestaña de permisos
- [ ] Existen 10 justificaciones predeterminadas creadas

#### ✅ Frontend (POS)

- [ ] El POS carga normalmente sin errores
- [ ] No hay errores en la consola del navegador (F12)
- [ ] Los datos del POS se cargan completamente

**Para verificar el frontend:**

1. Abra el POS: **Punto de Ventas > Dashboard > [Su POS] > Nueva Sesión**
2. Presione **F12** para abrir la consola del navegador
3. Busque el mensaje: `POS Audit Deleted Items: Module loaded successfully`
4. Si no aparece, revise errores en la consola

### Prueba Rápida de Funcionamiento

Realice esta prueba rápida para confirmar que todo funciona:

1. **Abra el POS** con un usuario que tenga `pos_audit_enabled = True`

2. **Agregue un producto** a una orden (cualquier producto)

3. **Intente eliminar el producto:**
   - Haga clic en la X del producto

4. **Debe aparecer el popup** "Justificación de Eliminación"

5. **Seleccione una justificación** y confirme

6. **El producto debe eliminarse**

7. **Cierre la orden** (cree un cliente y pague si es necesario)

8. **Verifique el registro:**
   - Backend: Punto de Ventas > Reportes > Productos Eliminados
   - Debe aparecer el registro de la eliminación

**Si todo funciona correctamente:** ✅ Instalación exitosa

**Si hay problemas:** Ver sección [Solución de Problemas](#solución-de-problemas)

---

## Configuración de Usuarios

### Escenarios Comunes de Configuración

#### Escenario 1: Mesero/Cajero Regular

**Usuario:** Juan Pérez (Mesero)

**Configuración:**

```
Permisos / Accesos:
├─ Punto de Venta
│  └─ Usuario ✅
└─ Auditoría POS
   ├─ Auditar Eliminaciones en POS ✅
   └─ Puede Eliminar Auditorías POS ❌
```

**Resultado:**
- ✅ Puede usar el POS
- ✅ Se le solicitará justificación al eliminar
- ❌ No puede borrar registros de auditoría

#### Escenario 2: Gerente / Supervisor

**Usuario:** María González (Gerente)

**Configuración:**

```
Permisos / Accesos:
├─ Punto de Venta
│  └─ Administrador ✅
└─ Auditoría POS
   ├─ Auditar Eliminaciones en POS ✅
   └─ Puede Eliminar Auditorías POS ✅

Además:
└─ Grupos / Auditoría POS: Eliminar Registros ✅
```

**Resultado:**
- ✅ Puede usar el POS
- ✅ Se le solicitará justificación (opcional: puede desactivarlo)
- ✅ Puede ver y eliminar registros de auditoría
- ✅ Puede configurar justificaciones

#### Escenario 3: Administrador/Contador (Sin Auditoría)

**Usuario:** Carlos Admin (Contador)

**Configuración:**

```
Permisos / Accesos:
├─ Punto de Venta
│  └─ Administrador ✅
└─ Auditoría POS
   ├─ Auditar Eliminaciones en POS ❌
   └─ Puede Eliminar Auditorías POS ✅
```

**Resultado:**
- ✅ Puede usar el POS
- ❌ NO se le solicitará justificación (elimina libremente)
- ✅ Puede ver y eliminar registros de auditoría

### Configuración Masiva de Usuarios

Si necesita configurar muchos usuarios:

1. **Cree un grupo personalizado:**
   - Configuración > Usuarios y Compañías > Grupos
   - Cree "Meseros con Auditoría"
   - Asigne los permisos necesarios

2. **Asigne usuarios al grupo:**
   - Seleccione múltiples usuarios
   - Acción > Agregar a Grupo

### Cambiar Configuración en Tiempo Real

**Importante:** Los cambios en `pos_audit_enabled` requieren:

1. Guardar el usuario
2. El usuario debe cerrar y reabrir el POS
3. O reiniciar la sesión del POS

No es necesario reiniciar el servidor Odoo.

---

## Personalización de Justificaciones

### Agregar Justificaciones Personalizadas

Según su negocio, agregue justificaciones relevantes:

#### Ejemplo: Pizzería

```
Justificaciones adicionales:
1. Pizza quemada en el horno
2. Masa defectuosa
3. Cliente alérgico al gluten (cambio de última hora)
4. Error en el tipo de queso solicitado
5. Tiempo de cocción excedido
```

#### Ejemplo: Cafetería

```
Justificaciones adicionales:
1. Leche cortada
2. Café demasiado cargado/suave
3. Bebida derramada antes de servir
4. Cliente cambió leche normal por vegetal
5. Error en temperatura (frío/caliente)
```

#### Ejemplo: Restaurante de Comida Rápida

```
Justificaciones adicionales:
1. Combo incompleto - falta producto
2. Pan en mal estado
3. Porción incorrecta
4. Cliente pidió sin algún ingrediente (error al ingresar)
5. Producto caído al piso
```

### Organizar Justificaciones por Prioridad

Use el campo **Secuencia** para ordenar por frecuencia de uso:

```
Secuencia 10: Cliente cambió de opinión (más común)
Secuencia 20: Error al ingresar el pedido
Secuencia 30: Producto no disponible
...
Secuencia 90: Producto defectuoso (menos común)
Secuencia 100: Otros casos
```

### Justificaciones Temporales

Para eventos especiales:

1. Cree la justificación
2. Use cuando sea necesaria
3. Desactívela después del evento (no eliminar, solo desactivar)

**Ejemplo:**
```
"Promoción 2x1 - ajuste de precio"
Usar solo durante la promoción
```

---

## Pruebas Funcionales

### Suite de Pruebas Recomendadas

Antes de poner en producción, realice estas pruebas:

#### Test 1: Eliminación Simple

1. Agregar 1 producto
2. Eliminar el producto
3. Verificar que aparece popup
4. Cancelar popup → producto NO se elimina
5. Eliminar nuevamente
6. Justificar y confirmar → producto SÍ se elimina
7. Verificar registro en backend

**Resultado esperado:** ✅ Popup funciona, cancelar no elimina, confirmar sí elimina

#### Test 2: Disminución de Cantidad

1. Agregar producto con cantidad 5
2. Cambiar cantidad a 3
3. Verificar popup muestra "Cantidad eliminada: 2.00"
4. Justificar y confirmar
5. Verificar que la cantidad ahora es 3
6. Verificar registro en backend muestra qty_deleted = 2

**Resultado esperado:** ✅ Detecta disminución correctamente

#### Test 3: Aumento de Cantidad (No Audita)

1. Agregar producto con cantidad 2
2. Cambiar cantidad a 5
3. Verificar que NO aparece popup
4. Cantidad cambia directamente a 5

**Resultado esperado:** ✅ NO solicita justificación en incrementos

#### Test 4: Usuario sin Auditoría

1. Configurar usuario con `pos_audit_enabled = False`
2. Abrir POS con ese usuario
3. Eliminar cualquier producto
4. Verificar que NO aparece popup
5. Producto se elimina directamente

**Resultado esperado:** ✅ Usuarios sin auditoría funcionan normal

#### Test 5: Múltiples Eliminaciones

1. Agregar 3 productos diferentes
2. Eliminar los 3
3. Verificar que aparece popup 3 veces (una por producto)
4. Justificar cada uno con razones diferentes
5. Cerrar orden y verificar 3 registros en backend

**Resultado esperado:** ✅ Cada eliminación se registra independientemente

#### Test 6: Sincronización Offline/Online

1. Abrir POS
2. Desconectar internet
3. Realizar eliminaciones (deben funcionar offline)
4. Cerrar orden (queda en cola)
5. Reconectar internet
6. Orden se sincroniza automáticamente
7. Verificar registros en backend

**Resultado esperado:** ✅ Funciona offline, sincroniza cuando hay conexión

#### Test 7: Permisos de Eliminación de Registros

1. Usuario CON permiso `pos_audit_can_delete = True`
2. Ir a Productos Eliminados
3. Intentar eliminar registro → debe permitir

4. Usuario SIN permiso `pos_audit_can_delete = False`
5. Ir a Productos Eliminados
6. Intentar eliminar registro → debe mostrar error

**Resultado esperado:** ✅ Permisos funcionan correctamente

#### Test 8: Restaurante con Mesas

Si tiene `pos_restaurant` instalado:

1. Abrir POS
2. Seleccionar una mesa
3. Agregar productos
4. Eliminar un producto
5. Justificar y confirmar
6. Cerrar orden
7. Verificar en backend que el registro tiene `table_id` asociado

**Resultado esperado:** ✅ Mesa se registra correctamente

### Checklist Final de Pruebas

Marque antes de poner en producción:

- [ ] Test 1: Eliminación Simple
- [ ] Test 2: Disminución de Cantidad
- [ ] Test 3: Aumento de Cantidad
- [ ] Test 4: Usuario sin Auditoría
- [ ] Test 5: Múltiples Eliminaciones
- [ ] Test 6: Sincronización Offline/Online
- [ ] Test 7: Permisos de Eliminación
- [ ] Test 8: Restaurante con Mesas (si aplica)
- [ ] Todos los usuarios configurados correctamente
- [ ] Justificaciones personalizadas creadas
- [ ] Gerentes capacitados en uso de reportes
- [ ] Meseros/cajeros capacitados en uso del popup

---

## Desinstalación

Si necesita desinstalar el módulo (no recomendado, pero incluido por completitud):

### Pasos para Desinstalar

1. **Backup de datos:**

   ```
   Punto de Ventas > Reportes > Productos Eliminados
   Acción > Exportar (si desea conservar los datos)
   ```

2. **Desinstalar módulo:**

   - Apps > Buscar "Auditoría Eliminados POS"
   - Clic en el módulo
   - Botón "Desinstalar"
   - Confirmar

3. **Limpiar datos residuales (opcional):**

   Los registros de auditoría quedarán en la base de datos pero inaccesibles.
   Para eliminarlos completamente, ejecute desde terminal:

   ```python
   # Conectarse a la base de datos y ejecutar
   DELETE FROM pos_audit_deleted;
   DELETE FROM pos_deletion_reason;
   ```

⚠️ **Advertencia:** La desinstalación eliminará:
- Todos los registros de auditoría
- Todas las justificaciones personalizadas
- Los campos agregados a res.users

Esto NO es reversible sin un backup.

---

## Solución de Problemas

### Problema 1: El módulo no aparece en Apps

**Síntomas:**
- Buscando "Auditoría" o "pos_audit" no aparece nada

**Causas posibles:**
1. La carpeta no está en el directorio de addons correcto
2. No se actualizó la lista de aplicaciones
3. Hay un error en el `__manifest__.py`

**Solución:**

```bash
# 1. Verificar ubicación
ls /opt/odoo/addons/ | grep pos_audit

# 2. Verificar que __manifest__.py existe y es válido
cat /opt/odoo/addons/pos_audit_deleted_items/__manifest__.py

# 3. Reiniciar Odoo
sudo systemctl restart odoo

# 4. Actualizar lista de apps desde la interfaz
# Apps > Menú > Actualizar lista de Apps

# 5. Si persiste, verificar logs
tail -f /var/log/odoo/odoo-server.log
```

### Problema 2: Error al instalar - "Dependencias no satisfechas"

**Síntomas:**
- Error: "El módulo pos_restaurant no está disponible"

**Causa:**
- El módulo depende de `pos_restaurant` pero no está instalado

**Solución:**

1. **Opción A:** Instalar pos_restaurant primero
   ```
   Apps > Buscar "Restaurant" > Instalar "Point of Sale - Restaurant"
   Luego instalar pos_audit_deleted_items
   ```

2. **Opción B:** Remover dependencia si no usa restaurante
   ```python
   # Editar __manifest__.py
   'depends': [
       'point_of_sale',
       # 'pos_restaurant',  # Comentar esta línea
   ],
   ```

### Problema 3: El popup no aparece

**Síntomas:**
- Puedo eliminar productos pero no aparece el popup

**Diagnóstico:**

1. Verificar configuración del usuario:
   ```
   Configuración > Usuarios > [Su usuario]
   Permisos / Accesos > Auditoría POS
   ¿Está activado "Auditar Eliminaciones en POS"?
   ```

2. Verificar consola del navegador (F12):
   ```
   ¿Hay errores de JavaScript?
   ¿Aparece el mensaje "POS Audit Deleted Items: Module loaded successfully"?
   ```

3. Verificar que el usuario en el POS tiene la configuración:
   ```javascript
   // En consola del navegador
   console.log(pos.user.pos_audit_enabled);
   // Debe mostrar: true
   ```

**Solución:**

```bash
# Si el JS no se cargó, limpiar assets
./odoo-bin -c odoo.conf -d nombre_bd -u pos_audit_deleted_items --stop-after-init

# Limpiar cache del navegador (Ctrl + F5)

# Reiniciar sesión del POS
```

### Problema 4: Los registros no se guardan en el backend

**Síntomas:**
- El popup aparece y funciona
- Pero en "Productos Eliminados" no hay registros

**Diagnóstico:**

1. Verificar logs de Odoo:
   ```bash
   tail -f /var/log/odoo/odoo-server.log | grep -i audit
   ```

2. Verificar que la orden se sincronizó:
   ```
   Punto de Ventas > Órdenes
   Buscar la orden
   ¿Tiene estado "Pagado" o "Publicado"?
   ```

3. Verificar permisos:
   ```
   El usuario puede crear registros en pos.audit.deleted?
   ```

**Solución:**

```bash
# Verificar permisos en ir.model.access.csv
cat security/ir.model.access.csv | grep pos_audit

# Reinstalar con actualización
./odoo-bin -c odoo.conf -d nombre_bd -u pos_audit_deleted_items --stop-after-init

# Si el problema persiste, verificar método create_audit_records_from_ui
# en pos_order.py
```

### Problema 5: Error "No tiene permisos para eliminar"

**Síntomas:**
- Al intentar eliminar un registro de auditoría aparece:
  "No tiene permisos para eliminar registros de auditoría"

**Causa:**
- El usuario no tiene `pos_audit_can_delete = True`

**Solución:**

1. Ir a Configuración > Usuarios
2. Editar usuario
3. Pestaña Permisos / Accesos
4. Activar "Puede Eliminar Auditorías POS"
5. Guardar
6. Además, asignar al grupo "Auditoría POS: Eliminar Registros"

### Problema 6: Justificaciones no aparecen en el popup

**Síntomas:**
- El popup aparece pero no hay botones de justificaciones predeterminadas

**Diagnóstico:**

```javascript
// Consola del navegador en el POS
console.log(pos.deletion_reasons);
// Debe mostrar un array con justificaciones

// Si está vacío o undefined, no se cargaron
```

**Solución:**

1. Verificar que existen justificaciones activas:
   ```
   Punto de Ventas > Configuración > Justificaciones de Eliminaciones
   ¿Hay registros con "Activo" = ✅?
   ```

2. Reinstalar datos:
   ```bash
   ./odoo-bin -c odoo.conf -d nombre_bd -u pos_audit_deleted_items --stop-after-init
   ```

3. Reiniciar sesión del POS

### Obtener Soporte Adicional

Si los problemas persisten:

1. **Recopilar información:**
   - Versión de Odoo: `./odoo-bin --version`
   - Logs de error: últimas 100 líneas del log
   - Pasos para reproducir el problema

2. **Contactar soporte:**
   - Email: info@jbnegoc.cl
   - Asunto: "Soporte pos_audit_deleted_items - [Descripción breve]"
   - Incluir información recopilada

---

## Recursos Adicionales

### Documentación

- **Manual de Usuario:** `README_USUARIO.md` - Para meseros y gerentes
- **Documentación Técnica:** `README_TECHNICAL.md` - Para desarrolladores
- **Este archivo:** `INSTALL.md` - Instalación y configuración

### Videos de Capacitación

*(Disponibles en el sitio web de Jbnegoc SPA)*

- Video 1: Instalación del módulo (5 min)
- Video 2: Configuración inicial (10 min)
- Video 3: Uso diario para meseros (8 min)
- Video 4: Reportes y análisis para gerentes (15 min)

### Soporte

**Jbnegoc SPA**
- Web: https://www.jbnegoc.cl
- Email: info@jbnegoc.cl
- Teléfono: [Incluir teléfono]

**Horario de soporte:**
- Lunes a Viernes: 9:00 - 18:00 (Hora de Chile)
- Soporte de emergencia: [Incluir contacto de emergencia]

---

## Información de Licencia

**Licencia:** LGPL-3
**© 2026 Jbnegoc SPA - Todos los derechos reservados**

Este módulo es software libre: puede redistribuirlo y/o modificarlo bajo los términos de la Licencia Pública General Reducida de GNU (LGPL) versión 3.

---

**Fin de la Guía de Instalación**

¡Gracias por elegir nuestro módulo!
