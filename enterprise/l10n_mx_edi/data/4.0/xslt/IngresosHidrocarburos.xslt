<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:ieeh="http://www.sat.gob.mx/IngresosHidrocarburos10">

  <xsl:template match="ieeh:IngresosHidrocarburos">
    <!--Manejador de Atributos IngresosHidrocarburos-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumeroContrato" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ContraprestacionPagadaOperador" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Porcentaje" />
    </xsl:call-template>

    <!--  Iniciamos el manejo de los elementos hijo en la secuencia -->
    <xsl:for-each select="./ieeh:DocumentoRelacionado">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="ieeh:DocumentoRelacionado">
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@FolioFiscalVinculado" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@FechaFolioFiscalVinculado" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Mes" />
    </xsl:call-template>

  </xsl:template>


</xsl:stylesheet>