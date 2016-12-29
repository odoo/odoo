<?xml version="1.0" ?><xsl:stylesheet version="1.0" xmlns:ecb="http://www.sat.gob.mx/ecb" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output encoding="UTF-8" indent="no" method="text" version="1.0"/>
	<!-- Manejador de nodos tipo ECB -->
	<xsl:template match="ecb:EstadoDeCuentaBancario">
		<!-- Iniciamos el tratamiento de los atributos de EstadoDeCuentaBancario -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@version"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@numeroCuenta"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@nombreCliente"/>
		</xsl:call-template>
		<xsl:for-each select="ecb:Movimientos/ecb:MovimientoECBFiscal">
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@fecha"/>
			</xsl:call-template>
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@RFCenajenante"/>
			</xsl:call-template>
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@Importe"/>
			</xsl:call-template>
		</xsl:for-each>
	</xsl:template>
</xsl:stylesheet>