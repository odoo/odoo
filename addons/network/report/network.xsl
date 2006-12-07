<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="../../custom/corporate_defaults.xsl"/>
	<xsl:import href="../../base/report/rml_template.xsl"/>
	<xsl:variable name="page_format">a4_letter</xsl:variable>

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
		<xsl:apply-templates select="networks"/>
	</xsl:template>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template match="network">
		<setNextTemplate name="other_pages"/>
		<para>
			<xsl:value-of select="partner/title" />
			<xsl:text> </xsl:text>
			<xsl:value-of select="partner/name"/>
		</para>
		<para>
			<xsl:value-of select="partner/address/name"/>
		</para>
		<para>
			<xsl:value-of select="partner/address/street"/>
		</para>
		<para>
			<xsl:value-of select="partner/address/postcode"/> 
			<xsl:value-of select="partner/address/city"/>
		</para>
		<para>
			<xsl:value-of select="partner/address/country"/>
		</para>
		<nextFrame />
		<para t="1">
			Hello,
		</para>
		<para t="1">
			Here is the list of the software and hardware parts we installed during our last intervention.
		</para>
		<spacer length="1cm" />
		<xsl:apply-templates select="materials/material" />
	</xsl:template>
	
	<xsl:template match="materials">
		<xsl:apply-templates select="material"/>
	</xsl:template>
	
	<xsl:template match="material">
		<blockTable colWidths="16cm">
			<tr>
				<td>
					<para>
						<b t="1">Name</b>: 
						<i><xsl:value-of select="material-name"/></i>
					</para>
					<para>
						<b t="1">Type</b>:
						<i><xsl:value-of select="material-type"/></i>
					</para>
					<para>
						<b t="1">Date</b>:
						<i><xsl:value-of select="material-date"/></i>
					</para>
					<para>
						<b t="1">Warranty date</b>:
						<i><xsl:value-of select="material-warranty" /></i>
					</para>
					<para>
						<b t="1">Your Contact</b>:
						<i><xsl:value-of select="material-user"/></i>
					</para>
				</td>
			</tr>
		</blockTable>
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
			<xsl:apply-templates name="softwares/software"/>
		</blockTable>
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

