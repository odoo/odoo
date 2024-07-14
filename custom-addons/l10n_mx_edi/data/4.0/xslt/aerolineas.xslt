<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:aerolineas="http://www.sat.gob.mx/aerolineas">

  <!-- Manejador de nodos tipo aerolineas:Aerolineas --> 
  <xsl:template match="aerolineas:Aerolineas">

    <!-- Iniciamos el tratamiento de los atributos de aerolineas:Aerolineas -->

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TUA"/>
    </xsl:call-template>

    <!-- Iniciamos el manejo de los nodos dependientes -->
    <xsl:apply-templates select="./aerolineas:OtrosCargos"/>

  </xsl:template>

  <!-- Manejador de nodos tipo aerolineas:OtrosCargos -->
  <xsl:template match="aerolineas:OtrosCargos">

    <!-- Iniciamos el tratamiento de los atributos de aerolineas:OtrosCargos -->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TotalCargos"/>
    </xsl:call-template>

    <!-- Iniciamos el manejo de los nodos dependientes -->    
    <xsl:for-each select="./aerolineas:Cargo">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <!-- Manejador de nodos tipo aerolineas:Cargo -->
  <xsl:template match="aerolineas:Cargo">

    <!-- Iniciamos el tratamiento de los atributos de aerolineas:ConceptoConsumoDeCombustibles -->

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@CodigoCargo"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Importe"/>
    </xsl:call-template>

  </xsl:template>

</xsl:stylesheet>
