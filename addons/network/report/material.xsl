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
		<blockTableStyle id="logpass">
			<blockFont name="Helvetica" size="8" start="0,0" stop="-1,-1" />
			<blockBackground colorName="grey" start="0,0" stop="-1,-1" />
		</blockTableStyle>
	</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="materials"/>
	</xsl:template>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template match="materials">
		<xsl:apply-templates select="material"/>
	</xsl:template>

	<xsl:template match="material">
		<setNextTemplate name="other_pages"/>
		<para>
			<b t="1">Name</b>: 
			<i><xsl:value-of select="material-name"/></i>
		</para>
		<para>
			<b t="1">Date</b>:
			<i><xsl:value-of select="material-date"/></i>
		</para>
		<para>
			<b t="1">Type</b>:
			<i><xsl:value-of select="material-type"/></i>
		</para>
		<para>
			<b t="1">Your Contact</b>:
			<i><xsl:value-of select="material-user"/></i>
		</para>
		<para>
			<b t="1">Notes</b>:
		</para>
		<para>
			<i><xsl:value-of select="material-note"/></i>
		</para>
		<spacer length="1cm" width="2mm"/>
		<blockTable colWidths="6cm,3cm,2.5cm,2.5cm" style="products">
			<tr>
				<td t="1">Software</td>
				<td t="1">Type</td>
				<td t="1">Date</td>
				<td t="1">Version</td>
			</tr>
			<xsl:apply-templates name="softwares"/>
		</blockTable>
		<setNextTemplate name="first_page"/>
		<pageBreak/>
	</xsl:template>

	<xsl:template match="software">
		<tr>
			<td>
				<xsl:value-of select="soft-name"/>
			</td>
			<td>
				<xsl:value-of select="soft-type"/>
			</td>
			<td>
				<xsl:value-of select="soft-date"/>
			</td>
			<td>
				<xsl:value-of select="soft-version"/>
			</td>
		</tr>
		<xsl:if test="acces">
			<tr>
				<td></td>
				<td t="1">Login / Password</td>
				<td>
					<blockTable colWidths="2.5cm,2.5cm" style="logpass">
						<xsl:for-each select="acces">
							<tr>
								<td><xsl:value-of select="username" /></td>
								<td><xsl:value-of select="password" /></td>
							</tr>
						</xsl:for-each>
					</blockTable>
				</td>
			</tr>
			<tr></tr>
		</xsl:if>
	</xsl:template>
</xsl:stylesheet>
