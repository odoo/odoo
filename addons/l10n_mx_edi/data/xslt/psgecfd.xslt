<?xml version="1.0" ?><xsl:stylesheet version="1.0" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:psgecfd="http://www.sat.gob.mx/psgecfd" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<!-- Manejador de nodos tipo psgecfd:PrestadoresDeServiciosDeCFD -->
	<xsl:template match="psgecfd:PrestadoresDeServiciosDeCFD">
		<!-- Iniciamos el tratamiento de los atributos de psgecfd:PrestadoresDeServiciosDeCFD -->
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@nombre"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@rfc"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@noCertificado"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@fechaAutorizacion"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@noAutorizacion"/></xsl:call-template>
	</xsl:template>
</xsl:stylesheet>