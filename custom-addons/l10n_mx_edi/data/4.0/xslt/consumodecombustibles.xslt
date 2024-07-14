<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:consumodecombustibles="http://www.sat.gob.mx/consumodecombustibles">  

  <!-- Manejador de nodos tipo consumodecombustibles:ConsumoDeCombustibles --> 
  <xsl:template match="consumodecombustibles:ConsumoDeCombustibles">

    <!-- Iniciamos el tratamiento de los atributos de consumodecombustibles:ConsumoDeCombustibles -->

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@version"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@tipoOperacion"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@numeroDeCuenta"/>
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@subTotal"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@total"/>
    </xsl:call-template>

    <!-- Iniciamos el manejo de los nodos dependientes -->
    <xsl:apply-templates select="./consumodecombustibles:Conceptos"/>

  </xsl:template>

  <!-- Manejador de nodos tipo consumodecombustibles:Conceptos -->
  <xsl:template match="consumodecombustibles:Conceptos">

    <!-- Iniciamos el manejo de los nodos dependientes -->

    <xsl:for-each select="./consumodecombustibles:ConceptoConsumoDeCombustibles">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <!-- Manejador de nodos tipo consumodecombustibles:ConceptoConsumoDeCombustibles -->
  <xsl:template match="consumodecombustibles:ConceptoConsumoDeCombustibles">

    <!-- Iniciamos el tratamiento de los atributos de consumodecombustibles:ConceptoConsumoDeCombustibles -->

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@identificador"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@fecha"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@rfc"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@claveEstacion"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@cantidad"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@nombreCombustible"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@folioOperacion"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@valorUnitario"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@importe"/>
    </xsl:call-template>

    <xsl:for-each select="./consumodecombustibles:Determinados">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <!-- Manejador de nodos tipo consumodecombustibles:Determinados -->
  <xsl:template match="consumodecombustibles:Determinados">

    <!-- Iniciamos el manejo de los nodos dependientes -->

    <xsl:for-each select="./consumodecombustibles:Determinado">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <!-- Manejador de nodos tipo consumodecombustibles:Determinado -->
  <xsl:template match="consumodecombustibles:Determinado">

    <!-- Iniciamos el tratamiento de los atributos de consumodecombustibles:Determinado -->

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@impuesto"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@tasa"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@importe"/>
    </xsl:call-template>

  </xsl:template>

</xsl:stylesheet>
