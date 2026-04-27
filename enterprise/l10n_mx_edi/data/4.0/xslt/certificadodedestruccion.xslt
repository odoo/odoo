<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:destruccion="http://www.sat.gob.mx/certificadodestruccion">
  <xsl:template match="destruccion:certificadodedestruccion">
    <!--Manejador de nodos tipo certificadodedestruccion-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Serie" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumFolDesVeh" />
    </xsl:call-template>
    <!--  Iniciamos el manejo de los nodos dependientes -->
    <xsl:apply-templates select="./destruccion:VehiculoDestruido" />
    <xsl:apply-templates select="./destruccion:InformacionAduanera" />
  </xsl:template>
  <xsl:template match="destruccion:VehiculoDestruido">
    <!--  Iniciamos el tratamiento de los atributos de destruccion:VehiculoDestruido-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Marca" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipooClase" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Año" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Modelo" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NIV" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumSerie" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumPlacas" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumMotor" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumFolTarjCir" />
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="destruccion:InformacionAduanera">
    <!--  Iniciamos el tratamiento de los atributos de destruccion:InformaciónAduanera-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumPedImp" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Fecha" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Aduana" />
    </xsl:call-template>
  </xsl:template>
 </xsl:stylesheet>
