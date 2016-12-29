<?xml version="1.0" ?><xsl:stylesheet version="1.0" xmlns:divisas="http://www.sat.gob.mx/divisas" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<!-- Manejador de nodos tipo divisas:Divisas -->
	<xsl:template match="divisas:Divisas">
		<!-- Iniciamos el tratamiento de los atributos de divisas:Divisas -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@version"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@tipoOperacion"/>
		</xsl:call-template>
	</xsl:template>
</xsl:stylesheet>