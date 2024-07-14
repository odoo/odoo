<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:valesdedespensa="http://www.sat.gob.mx/valesdedespensa">  

  <!-- Manejador de nodos tipo valesdedespensa:ValesDeDespensa --> 
  <xsl:template match="valesdedespensa:ValesDeDespensa">

    <!-- Iniciamos el tratamiento de los atributos de valesdedespensa:ValesDeDespensa -->

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@version"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@tipoOperacion"/>
    </xsl:call-template>
     <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@registroPatronal"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@numeroDeCuenta"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@total"/>
    </xsl:call-template>

    <!-- Iniciamos el manejo de los nodos dependientes -->
    <xsl:apply-templates select="./valesdedespensa:Conceptos"/>

  </xsl:template>

  <!-- Manejador de nodos tipo valesdedespensa:Conceptos -->
  <xsl:template match="valesdedespensa:Conceptos">

    <!-- Iniciamos el manejo de los nodos dependientes -->

    <xsl:for-each select="./valesdedespensa:Concepto">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <!-- Manejador de nodos tipo valesdedespensa:Concepto -->
  <xsl:template match="valesdedespensa:Concepto">

    <!-- Iniciamos el tratamiento de los atributos de valesdedespensa:Concepto -->

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
      <xsl:with-param name="valor" select="./@curp"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@nombre"/>
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@numSeguridadSocial"/>
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@importe"/>
    </xsl:call-template>

  </xsl:template>

</xsl:stylesheet>
