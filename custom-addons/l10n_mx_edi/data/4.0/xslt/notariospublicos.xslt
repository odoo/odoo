<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:notariospublicos="http://www.sat.gob.mx/notariospublicos">

  <!-- Manejador de nodos tipo notariospublicos:NotariosPublicos -->
  <xsl:template match="notariospublicos:NotariosPublicos">

    <!-- Iniciamos el tratamiento de los atributos -->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version"/>
    </xsl:call-template>

    <!-- Iniciamos el manejo de los nodos dependientes -->
    <xsl:apply-templates select="./notariospublicos:DescInmuebles"/>
    <xsl:apply-templates select="./notariospublicos:DatosOperacion"/>
    <xsl:apply-templates select="./notariospublicos:DatosNotario"/>
    <xsl:apply-templates select="./notariospublicos:DatosEnajenante"/>
    <xsl:apply-templates select="./notariospublicos:DatosAdquiriente"/>

  </xsl:template>

    <!-- Manejador de nodos tipo notariospublicos:DescInmuebles -->
    <xsl:template match="notariospublicos:DescInmuebles">

      <!-- Iniciamos el manejo de los nodos dependientes -->
      <xsl:for-each select="./notariospublicos:DescInmueble">
        <xsl:apply-templates select="."/>
      </xsl:for-each>

    </xsl:template>

      <!-- Manejador de nodos tipo notariospublicos:DescInmueble -->
      <xsl:template match="notariospublicos:DescInmueble">

        <!-- Iniciamos el tratamiento de los atributos -->
        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@TipoInmueble"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@Calle"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@NoExterior"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@NoInterior"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@Colonia"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@Localidad"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@Referencia"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@Municipio"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@Estado"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@Pais"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@CodigoPostal"/>
        </xsl:call-template>

      </xsl:template>

    <!-- Manejador de nodos tipo notariospublicos:DatosOperacion -->
    <xsl:template match="notariospublicos:DatosOperacion">

      <!-- Iniciamos el tratamiento de los atributos -->
      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@NumInstrumentoNotarial"/>
      </xsl:call-template>

      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@FechaInstNotarial"/>
      </xsl:call-template>

      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@MontoOperacion"/>
      </xsl:call-template>

      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@Subtotal"/>
      </xsl:call-template>

      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@IVA"/>
      </xsl:call-template>

    </xsl:template>

    <!-- Manejador de nodos tipo notariospublicos:DatosNotario -->
    <xsl:template match="notariospublicos:DatosNotario">

      <!-- Iniciamos el tratamiento de los atributos -->
      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@CURP"/>
      </xsl:call-template>

      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@NumNotaria"/>
      </xsl:call-template>

      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@EntidadFederativa"/>
      </xsl:call-template>

      <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@Adscripcion"/>
      </xsl:call-template>


    </xsl:template>

    <!-- Manejador de nodos tipo notariospublicos:DatosEnajenante -->
    <xsl:template match="notariospublicos:DatosEnajenante">

      <!-- Iniciamos el tratamiento de los atributos -->
      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@CoproSocConyugalE"/>
      </xsl:call-template>

      <!-- Iniciamos el manejo de los nodos dependientes -->
      <xsl:if test="./notariospublicos:DatosUnEnajenante">
        <xsl:apply-templates select="./notariospublicos:DatosUnEnajenante"/>
      </xsl:if>

      <xsl:if test="./notariospublicos:DatosEnajenantesCopSC">
        <xsl:apply-templates select="./notariospublicos:DatosEnajenantesCopSC"/>
      </xsl:if>

    </xsl:template>

      <!-- Manejador de nodos tipo notariospublicos:DatosUnEnajenante -->
      <xsl:template match="notariospublicos:DatosUnEnajenante">

        <!-- Iniciamos el tratamiento de los atributos -->
        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@Nombre"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@ApellidoPaterno"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@ApellidoMaterno"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@RFC"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@CURP"/>
        </xsl:call-template>

      </xsl:template>

      <!-- Manejador de nodos tipo notariospublicos:DatosEnajenantesCopSC -->
      <xsl:template match="notariospublicos:DatosEnajenantesCopSC">

        <!-- Iniciamos el manejo de los nodos dependientes -->
        <xsl:for-each select="./notariospublicos:DatosEnajenanteCopSC">
          <xsl:apply-templates select="."/>
        </xsl:for-each>

      </xsl:template>

        <!-- Manejador de nodos tipo notariospublicos:DatosEnajenanteCopSC -->
        <xsl:template match="notariospublicos:DatosEnajenanteCopSC">

          <!-- Iniciamos el tratamiento de los atributos -->
          <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Nombre"/>
          </xsl:call-template>

          <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="./@ApellidoPaterno"/>
          </xsl:call-template>

          <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="./@ApellidoMaterno"/>
          </xsl:call-template>

          <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@RFC"/>
          </xsl:call-template>

          <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="./@CURP"/>
          </xsl:call-template>

          <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Porcentaje"/>
          </xsl:call-template>

        </xsl:template>

    <!-- Manejador de nodos tipo notariospublicos:DatosAdquiriente -->
    <xsl:template match="notariospublicos:DatosAdquiriente">

      <!-- Iniciamos el tratamiento de los atributos -->
      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@CoproSocConyugalE"/>
      </xsl:call-template>

      <!-- Iniciamos el manejo de los nodos dependientes -->
      <xsl:if test="./notariospublicos:DatosUnAdquiriente">
        <xsl:apply-templates select="./notariospublicos:DatosUnAdquiriente"/>
      </xsl:if>

      <xsl:if test="./notariospublicos:DatosAdquirientesCopSC">
        <xsl:apply-templates select="./notariospublicos:DatosAdquirientesCopSC"/>
      </xsl:if>

    </xsl:template>

      <!-- Manejador de nodos tipo notariospublicos:DatosUnAdquiriente -->
      <xsl:template match="notariospublicos:DatosUnAdquiriente">

        <!-- Iniciamos el tratamiento de los atributos -->
        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@Nombre"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@ApellidoPaterno"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@ApellidoMaterno"/>
        </xsl:call-template>

        <xsl:call-template name="Requerido">
          <xsl:with-param name="valor" select="./@RFC"/>
        </xsl:call-template>

        <xsl:call-template name="Opcional">
          <xsl:with-param name="valor" select="./@CURP"/>
        </xsl:call-template>

      </xsl:template>

      <!-- Manejador de nodos tipo notariospublicos:DatosAdquirientesCopSC -->
      <xsl:template match="notariospublicos:DatosAdquirientesCopSC">

        <!-- Iniciamos el manejo de los nodos dependientes -->
        <xsl:for-each select="./notariospublicos:DatosAdquirienteCopSC">
          <xsl:apply-templates select="."/>
        </xsl:for-each>

      </xsl:template>

        <!-- Manejador de nodos tipo notariospublicos:DatosAdquirienteCopSC -->
        <xsl:template match="notariospublicos:DatosAdquirienteCopSC">

          <!-- Iniciamos el tratamiento de los atributos -->
          <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Nombre"/>
          </xsl:call-template>

          <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="./@ApellidoPaterno"/>
          </xsl:call-template>

          <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="./@ApellidoMaterno"/>
          </xsl:call-template>

          <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@RFC"/>
          </xsl:call-template>

          <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="./@CURP"/>
          </xsl:call-template>

          <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Porcentaje"/>
          </xsl:call-template>

        </xsl:template>

</xsl:stylesheet>
