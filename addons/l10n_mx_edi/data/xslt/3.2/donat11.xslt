<?xml version="1.0" ?><xsl:stylesheet version="1.0" xmlns:donat="http://www.sat.gob.mx/donat" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output encoding="UTF-8" indent="no" method="text" version="1.0"/>
	<!-- Manejador de nodos tipo donat:Donatarias -->
	<xsl:template match="donat:Donatarias">
		<!-- Iniciamos el tratamiento de los atributos de donat:Donatarias -->
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@version"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@noAutorizacion"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@fechaAutorizacion"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@leyenda"/></xsl:call-template>
	</xsl:template>
	
</xsl:stylesheet>