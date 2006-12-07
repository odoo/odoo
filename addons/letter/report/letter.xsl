<?xml version="1.0" encoding="iso-8859-1"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="custom_default.xsl"/>
	<xsl:import href="custom_rml.xsl"/>
	
	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template name="stylesheet">
	</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="letter"/>
	</xsl:template>

	<xsl:template match="letter">
		<xsl:apply-templates select="paragraphes"/>
	</xsl:template>

	<xsl:template match="paragraphes">
		<xsl:apply-templates select="paragraphe"/>
	</xsl:template>
	
	<xsl:template match="paragraphe">
			<xsl:value-of select="." disable-output-escaping="yes"/>
			<spacer width="4mm" length="4mm"/>
	</xsl:template>
</xsl:stylesheet>
