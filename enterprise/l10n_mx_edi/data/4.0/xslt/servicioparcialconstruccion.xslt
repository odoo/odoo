<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:servicioparcial="http://www.sat.gob.mx/servicioparcialconstruccion">
  <xsl:template match="servicioparcial:parcialesconstruccion">
    <!--Manejador de nodos tipo parcialesconstruccion-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumPerLicoAut" />
    </xsl:call-template>
    <!--  Iniciamos el manejo de los nodos dependientes -->
    <xsl:apply-templates select="./servicioparcial:Inmueble" />
  </xsl:template>
  <xsl:template match="servicioparcial:Inmueble">
    <!--  Iniciamos el tratamiento de los atributos de servicioparcial:Inmueble-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Calle" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NoExterior" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NoInterior" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Colonia" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Localidad" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Referencia" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Municipio" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Estado" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@CodigoPostal" />
    </xsl:call-template>
  </xsl:template>
</xsl:stylesheet>
