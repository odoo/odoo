<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:ine="http://www.sat.gob.mx/ine">

  <xsl:template match="ine:INE">
    <!--Manejador de nodos tipo INE-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoProceso" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TipoComite" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@IdContabilidad" />
    </xsl:call-template>

    <!--  Iniciamos el manejo de los elementos hijo en la secuencia -->
    <xsl:for-each select="./ine:Entidad">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="ine:Entidad">
    <!--Manejador de nodos tipo Entidad-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ClaveEntidad" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Ambito" />
    </xsl:call-template>

    <!--  Iniciamos el tratamiento de los atributos de ine:Contabilidad-->
    <xsl:for-each select="./ine:Contabilidad">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <!--  Iniciamos el manejo de los elementos hijo en la secuencia Contabilidad-->
  <xsl:template match="ine:Contabilidad">
    <!--  Iniciamos el manejo de los nodos dependientes -->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@IdContabilidad" />
    </xsl:call-template>
  </xsl:template>



</xsl:stylesheet>
