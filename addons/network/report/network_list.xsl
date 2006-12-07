<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="../../custom/corporate_defaults.xsl"/>
	<xsl:import href="../../base/report/rml_template.xsl"/>
	<xsl:variable name="page_format">a4_normal</xsl:variable>

	<xsl:template name="stylesheet">
		<blockTableStyle id="network_list">
			<blockFont name="Helvetica-BoldOblique" size="12"
				start="0,0" stop="-1,0"/>
			<blockBackground colorName="yellow" start="0,0" stop="-1,0"/>
			<blockValign value="TOP"/>
		</blockTableStyle>
	</xsl:template>

	<xsl:template name="first_page_frames">
		<frame id="main" x1="1cm" y1="3.5cm" width="19.0cm" height="21.5cm" />
	</xsl:template>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template name="story">
		<blockTable colWidths="5cm,5cm,5cm" style="network_list">
			<tr>
				<td t="1">Partner</td>
				<td t="1">Network name</td>
				<td t="1">Onsite contact</td>
			</tr>
			<xsl:for-each select="/networks/network">
				<tr>
					<td>
						<xsl:value-of select="partner/name" />
					</td>
					<td>
						<xsl:value-of select="network-name" />
					</td>
					<td>
						<xsl:value-of select="onsite/name" />
					</td>
				</tr>
			</xsl:for-each>
		</blockTable>
		<xsl:apply-templates select="networks"/>
	</xsl:template>

</xsl:stylesheet>

