<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:catalogocuentas="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/CatalogoCuentas">
<!--En esta sección se define la inclusión de las plantillas de utilerías para colapsar espacios -->
  <xsl:include href="utilerias.xslt"/>
	<!-- Con el siguiente método se establece que la salida deberá ser en texto -->
	<xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>
  <!-- Aquí iniciamos el procesamiento de la cadena original con su | inicial y el terminador || -->
  <xsl:template match="/">|<xsl:apply-templates select="/catalogocuentas:Catalogo"/>||</xsl:template>
  
	<xsl:template match="catalogocuentas:Catalogo">
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Version"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@RFC"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Mes"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Anio"/>
		</xsl:call-template>
		<xsl:apply-templates select="./catalogocuentas:Ctas"/>
	</xsl:template>
	<xsl:template match="catalogocuentas:Ctas">
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@CodAgrup"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NumCta"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Desc"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@SubCtaDe"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Nivel"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Natur"/>
		</xsl:call-template>
	</xsl:template>
	
   </xsl:stylesheet>
