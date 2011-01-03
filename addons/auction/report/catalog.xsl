<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="corporate_defaults.xsl"/>
	<xsl:import href="rml_template.xsl"/>
	<xsl:variable name="page_format">a4_normal</xsl:variable>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template name="stylesheet">
		<paraStyle name="name" fontName="Helvetica-Bold" fontSize="16" alignment="center"/>
		<blockTableStyle id="result">
			 <blockValign value="TOP"/>
			 <blockAlignment value="RIGHT" start="-1,0" stop="-1,-1"/>
			 <blockFont name="Helvetica-BoldOblique" size="12" start="0,0" stop="-1,0"/>
			 <blockBackground colorName="grey" start="0,0" stop="-1,0"/>
			 <blockTextColor colorName="white" start="0,0" stop="-1,0"/>
			 <lineStyle kind="LINEBELOW" start="0,0" stop="-1,0"/>
		</blockTableStyle>
	</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="catalog"/>
	</xsl:template>

	<xsl:template match="catalog">
		<xsl:apply-templates select="auction"/>
		<xsl:apply-templates select="lines"/>
	</xsl:template>

	<xsl:template match="auction">
		<para style="name"><xsl:value-of select="name"/></para>
	</xsl:template>

	<xsl:template match="lines">
		<spacer length="1cm"/>
		<blockTable colWidths="1.8cm,12.5cm,3cm" repeatRows="1" style="result">
		<tr>
			<td t="1">Cat. N.</td>
			<td t="1">Description</td>
			<td t="1">Estimate</td>
		</tr>
			<xsl:apply-templates select="line"/>
		</blockTable>
		<pageBreak/>
	</xsl:template>

	<xsl:template match="line">
		<tr>
			<td><xsl:value-of select="lot-number"/></td>
			<td>
				<para>
					<xsl:if test="lot-author != ''">
						<b><xsl:value-of select="lot-author"/></b>
						<xsl:text>: </xsl:text>
					</xsl:if>
					<b><xsl:value-of select="lot-title"/></b>
					<xsl:text>. </xsl:text>
					<xsl:value-of select="lot-info"/>
				</para>
			</td>
			<td>
				<xsl:if test="lot-est1!=''">
					<xsl:value-of select="round(lot-est1)"/>
				</xsl:if>
				<xsl:text> / </xsl:text>
				<xsl:if test="lot-est2!=''">
					<xsl:value-of select="round(lot-est2)"/>
				</xsl:if>
			</td>
		</tr>
	</xsl:template>

</xsl:stylesheet>
