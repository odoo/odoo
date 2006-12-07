<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="../../custom/corporate_defaults.xsl"/>
	<xsl:import href="../../base/report/rml_template.xsl"/>
	<xsl:variable name="page_format">a4_normal</xsl:variable>

	<xsl:template name="stylesheet">
		<blockTableStyle id="products">
			<blockFont name="Helvetica-BoldOblique" size="12"
				start="0,0" stop="-1,0"/>
			<blockBackground colorName="yellow" start="0,0" stop="-1,0"/>
			<blockValign value="TOP"/>
		</blockTableStyle>
	</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="employees"/>
	</xsl:template>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template match="employees">
		<xsl:apply-templates select="employee"/>
	</xsl:template>

	<xsl:template match="employee">
		<setNextTemplate name="other_pages"/>
		<para>
			<b t="1">Name</b>: 
			<i><xsl:value-of select="name"/></i>
		</para>
		<para>
			<b t="1">Address</b>:
			<i><xsl:value-of select="address"/></i>
		</para>
		<spacer length="1cm" width="2mm"/>
		<blockTable colWidths="3cm,2.5cm,2.5cm" style="products">
			<tr>
				<td>Date</td>
				<td>Action</td>
				<td>Hour</td>
			</tr>
			<xsl:apply-templates name="attendances"/>
		</blockTable>
		<setNextTemplate name="first_page"/>
		<pageBreak/>
	</xsl:template>

	<xsl:template match="attendance">
		<tr>
			<td>
				<xsl:value-of select="substring(date,1,10)"/>
			</td>
			<td>
				<xsl:value-of select="action"/>
			</td>
			<td>
				<xsl:value-of select="substring(date,12,5)"/>
			</td>
		</tr>
	</xsl:template>
</xsl:stylesheet>
