<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="../../custom/corporate_defaults.xsl"/>
	<xsl:import href="../../base/report/rml_template.xsl"/>
	<xsl:variable name="page_format">a4_normal</xsl:variable>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<!-- stylesheet -->

	<xsl:template name="stylesheet">
		<paraStyle name="title" fontName="Helvetica-Bold" fontSize="12" alignment="center"/>
		<blockTableStyle id="headerm">
			<blockBackground colorName="grey" start="0,0" stop="-1,0"/>
			<blockValign value="TOP"/>
			 <blockAlignment value="CENTER"/>
			 <lineStyle kind="GRID" colorName="black"/>
		</blockTableStyle>
		<blockTableStyle id="header">
			<blockBackground colorName="lightgrey" start="0,0" stop="-1,0"/>
			<blockValign value="TOP"/>
			<blockAlignment value="RIGHT" start="-1,0" stop="-1,-1"/>
			<lineStyle kind="GRID" colorName="black"/>
		</blockTableStyle>
</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="report"/>
	</xsl:template>
	
	<xsl:template match="report">
		<xsl:apply-templates select="product"/>
	</xsl:template>

	<xsl:template match="product">
		<blockTable style="headerm" colWidths="15cm">
		<tr>
			<td>
				<para style="title">
					<xsl:value-of select="name"/>
					<xsl:text> (</xsl:text>
					<xsl:value-of select="unit"/>
					<xsl:text>)</xsl:text>
				</para>
			</td>
		</tr>
		</blockTable>
		<xsl:apply-templates select="locations"/>
		<spacer length="5mm" width="5mm"/>
	</xsl:template>

	<xsl:template match="locations">
		<blockTable style="header" colWidths="12cm,3cm">
		<tr>
			<td t="1">Location</td>
			<td t="1">Quantity</td>
		</tr>
		<xsl:apply-templates select="location"/>
		</blockTable>
	</xsl:template>

	<xsl:template match="location">
		<tr>
			<td>
				<para>
					<xsl:value-of select="loc_name"/>
				</para>
			</td>
			<td>
					<xsl:value-of select="loc_qty"/>
			</td>
		</tr>
	</xsl:template>

</xsl:stylesheet>
