<?xml version="1.0" ?><xsl:stylesheet version="1.0" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:spei="http://www.sat.gob.mx/spei" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output encoding="UTF-8" indent="no" method="text" version="1.0"/>
	
	<!-- Manejador de nodos tipo Complemento_SPEI-->
	<xsl:template match="spei:Complemento_SPEI">
		<!--Iniciamos el tratamiento del complemento SPEI-->
		<xsl:for-each select="./spei:SPEI_Tercero">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	
	<!-- Manejador de atributos de SPEI_Tercero-->	
	<xsl:template match="spei:SPEI_Tercero">
		<!-- Manejo de los atributos del Ordenante-->
		<xsl:call-template name="Requerido">	
			<xsl:with-param name="valor" select="./@FechaOperacion"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Hora"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@ClaveSPEI"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@sello"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@numeroCertificado"/>
		</xsl:call-template>	
		<xsl:apply-templates select="./spei:Ordenante"/>
		<xsl:apply-templates select="./spei:Beneficiario"/>
		
	</xsl:template>
	
	<!-- Manejador de nodos tipo SPEI-->
	<xsl:template match="spei:Ordenante">
		<!-- Manejo de los atributos del Ordenante-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@BancoEmisor"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Nombre"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoCuenta"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Cuenta"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@RFC"/>
		</xsl:call-template>
	</xsl:template>
	<xsl:template match="spei:Beneficiario">
		<!-- Manejo de los atributos del Beneficiario-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@BancoReceptor"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Nombre"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoCuenta"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Cuenta"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@RFC"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Concepto"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@IVA"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@MontoPago"/>
		</xsl:call-template>
	</xsl:template>
</xsl:stylesheet>