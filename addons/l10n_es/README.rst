.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License

===============================================
Plan contable e impuestos de España (PGCE 2008)
===============================================

* Define las siguientes plantillas de cuentas:

  * Plan general de cuentas español 2008.
  * Plan general de cuentas español 2008 para pequeñas y medianas empresas.
  * Plan general de cuentas español 2008 para asociaciones.
* Define plantillas de impuestos para compra y venta.
* Define plantillas de códigos de impuestos.
* Define posiciones fiscales para la legislación fiscal española.

**IMPORTANTE:** Ésta es una versión mejorada con respecto al módulo que se
encuentra en la versión estándar de Odoo, por lo que es conveniente instalar
ésta para disponer de los últimos datos actualizados.

Historial
---------

* v5.3: Añadido "IVA soportado no sujeto".
* v5.2: Añadida retención 19,5% arrendamientos.
* v5.1: Renombrado todo lo relacionado con arrendamientos para no incluir la
  palabra "IRPF", ya que no es como tal IRPF.
* v5.0: Se ha rehecho toda la parte de impuestos para dar mayor facilidad de
  consulta de los datos para las declaraciones de la AEAT y para cubrir todas
  las casuísticas fiscales españolas actuales. Éstas son las características
  más destacadas:

  * Desdoblamiento de los impuestos principales para bienes y para servicios.
  * Nuevo árbol de códigos de impuestos orientado a cada modelo de la AEAT.
  * Nuevos códigos para los códigos de impuestos para facilitar su
    actualización.
  * La casilla del modelo viene ahora en la descripción, no en el código.
  * Posiciones fiscales ajustadas para el desdoblamiento.
  * Nuevo impuesto y posición fiscal para retención IRPF 19%.
  * Nuevo impuesto para revendedores con recargo de equivalencia.
  * Nuevas posiciones fiscales para retenciones de arrendamientos.
  * Pequeños ajustes en cuentas contables.
* v4.1: Cambio en el método que obtiene el nombre del impuesto e intercambiados
  los campos descripción/nombre para que no aparezca los códigos en documentos
  impresos ni en pantalla.
* v4.0: Refactorización completa de los planes de cuentas, con las siguientes
  caracteristicas:

  * Creacion de un plan común a los tres planes existentes, que reúne las
    cuentas repetidas entre ellos.
  * Eliminación de la triplicidad de impuestos y de códigos de impuestos.
  * Asignación de códigos a los impuestos para facilitar su actualización.
  * Eliminación de duplicidad de tipos de cuentas.

Instalación
===========

Si en la base de datos a aplicar ya se encuentra instalado el plan contable de
la compañía, será necesario actualizarlo con el módulo *account_chart_update*,
disponible en https://github.com/OCA/account-financial-tools. **AVISO:**
Después de actualizar de una version <5.0, será necesario cambiar el impuesto
de venta por defecto en la pestaña Configuración > Contabilidad, y además
sustituir en los productos el mismo por "x% IVA (servicios)" o
"x% IVA (bienes)" según corresponda en cada caso. Se puede utilizar para ello
el módulo *mass_editing* del repositorio https://github.com/OCA/server-tools.

Por último, si se procede del l10n_es v3.0, serán necesarios ajustes manuales
al actualizar el plan de cuentas, como crear a mano la cuenta 472000.

Créditos
========

Contribuidores
--------------
* Jordi Esteve <jesteve@zikzakmedia.com>
* Dpto. Consultoría Grupo Opentia <consultoria@opentia.es>
* Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>
* Carlos Liébana <carlos.liebana@factorlibre.com>
* Hugo Santos <hugo.santos@factorlibre.com>
* Albert Cabedo <albert@gafic.com>
