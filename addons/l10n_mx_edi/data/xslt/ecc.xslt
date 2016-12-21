<?xml version="1.0" ?><xsl:stylesheet version="1.0" xmlns:ecc="http://www.sat.gob.mx/ecc" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

	<!-- Manejador de nodos tipo ecc:EstadoDeCuentaCombustible -->
	<xsl:template match="ecc:EstadoDeCuentaCombustible">
		<!-- Iniciamos el tratamiento de los atributos de ecc:EstadoDeCuentaCombustible -->
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@tipoOperacion"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@numeroDeCuenta"/></xsl:call-template>
		<xsl:call-template name="Opcional"><xsl:with-param name="valor" select="./@subTotal"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@total"/></xsl:call-template>
		<!-- Iniciamos el manejo de los nodos dependientes -->
		<xsl:apply-templates select="./ecc:Conceptos"/>
	</xsl:template>

	<!-- Manejador de nodos tipo ecc:Conceptos -->
	<xsl:template match="ecc:Conceptos">
		<!-- Iniciamos el manejo de los nodos dependientes -->
		<xsl:for-each select="./ecc:ConceptoEstadoDeCuentaCombustible"><xsl:apply-templates select="."/></xsl:for-each>
	</xsl:template>
	
	<!-- Manejador de nodos tipo ecc:Traslados -->
	<xsl:template match="ecc:Traslados">
		<!-- Iniciamos el manejo de los nodos dependientes -->
		<xsl:for-each select="./ecc:Traslado"><xsl:apply-templates select="."/></xsl:for-each>
	</xsl:template>
	
	<!-- Manejador de nodos tipo ecc:ConceptoEstadoDeCuentaCombustible -->
	<xsl:template match="ecc:ConceptoEstadoDeCuentaCombustible">
		<!-- Iniciamos el tratamiento de los atributos de ecc:ConceptoEstadoDeCuentaCombustible -->
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@identificador"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@fecha"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@rfc"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@claveEstacion"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@cantidad"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@nombreCombustible"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@folioOperacion"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@valorUnitario"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@importe"/></xsl:call-template>
		<xsl:for-each select="./ecc:Traslados"><xsl:apply-templates select="."/></xsl:for-each>
	</xsl:template>
	
	<!-- Manejador de nodos tipo ecc:Traslado -->
	<xsl:template match="ecc:Traslado">
		<!-- Iniciamos el tratamiento de los atributos de ecc:Traslado -->
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@impuesto"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@tasa"/></xsl:call-template>
		<xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@importe"/></xsl:call-template>
	</xsl:template>
	
</xsl:stylesheet>