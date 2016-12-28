<?xml version="1.0" ?><xsl:stylesheet version="1.0" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:registrofiscal="http://www.sat.gob.mx/registrofiscal" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output encoding="UTF-8" indent="no" method="text" version="1.0"/>

  <!-- Manejador de nodos tipo nomina -->
  <xsl:template match="registrofiscal:CFDIRegistroFiscal">

    <!--Iniciamos el tratamiento de los atributos de RegistroFiscal -->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Folio"/>
    </xsl:call-template>

  </xsl:template>

</xsl:stylesheet>