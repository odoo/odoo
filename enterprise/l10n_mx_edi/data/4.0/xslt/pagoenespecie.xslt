<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:pagoenespecie="http://www.sat.gob.mx/pagoenespecie">
  <xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>

  <!-- Manejador de nodos tipo pago en especie-->
  <xsl:template match="pagoenespecie:PagoEnEspecie">

    <!--Iniciamos el tratamiento de los atributos de PagoEnEspecie -->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@CvePIC"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@FolioSolDon"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@PzaArtNombre"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@PzaArtTecn"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@PzaArtAProd"/>
    </xsl:call-template>

    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@PzaArtDim"/>
    </xsl:call-template>

  </xsl:template>

</xsl:stylesheet>
