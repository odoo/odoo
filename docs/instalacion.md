---
layout: default
title: Instalación con Docker Compose
---

[Volver al portal](../index.html)

# Instalación con Docker Compose

Esta guía levanta Odoo 19 y PostgreSQL 15 con la configuración versionada en [`docker-config/docker-compose.yml`](../docker-config/docker-compose.yml).

## Requisitos

- Git.
- Docker Engine en ejecución.
- Docker Compose v2, disponible mediante el comando `docker compose`.
- Puerto TCP `8069` libre.

## 1. Obtener el repositorio

```bash
git clone https://github.com/odooIPS-team/odooIPS.git
cd odooIPS
```

Si el repositorio ya está disponible, ejecute los pasos siguientes desde su raíz.

## 2. Descargar y levantar los servicios

```bash
docker compose -f docker-config/docker-compose.yml pull
docker compose -f docker-config/docker-compose.yml up -d
```

Compruebe el estado y, si fuera necesario, revise el arranque de Odoo:

```bash
docker compose -f docker-config/docker-compose.yml ps
docker compose -f docker-config/docker-compose.yml logs -f web
```

Cuando el servicio esté listo, abra `http://localhost:8069` en un navegador.

## 3. Crear la base de datos

En el administrador inicial de Odoo:

1. Indique una contraseña maestra para administrar bases de datos.
2. Cree una base de datos, por ejemplo `odoo_ventas`.
3. Defina el correo y la contraseña del usuario administrador.
4. Seleccione el idioma y el país requeridos; los datos de demostración son opcionales.

## 4. Instalar la mejora de descuentos

El directorio versionado [`addons`](../addons) se monta como `/mnt/extra-addons` dentro del contenedor.

1. Abra **Aplicaciones** en Odoo.
2. Actualice la lista de aplicaciones si el módulo no aparece.
3. Busque e instale **Validación de Descuento Comercial Máximo - MVP** (`validacion_descuento_maximo`).

También puede instalarlo desde la terminal después de crear la base de datos:

```bash
docker compose -f docker-config/docker-compose.yml exec web \
  /entrypoint.sh odoo -d odoo_ventas -i validacion_descuento_maximo \
  --stop-after-init --http-port=8070
docker compose -f docker-config/docker-compose.yml restart web
```

Sustituya `odoo_ventas` si utilizó otro nombre de base de datos.

## 5. Detener el entorno

```bash
docker compose -f docker-config/docker-compose.yml down
```

Los datos permanecen en volúmenes Docker. Para reiniciar desde cero, use `down -v`; esta variante elimina permanentemente la base de datos y los archivos persistidos por Odoo.
