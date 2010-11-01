<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">
	<xsl:import href="corporate_defaults.xsl"/>
	<xsl:import href="rml_template.xsl"/>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template name="stylesheet">
		<blockTableStyle id="accounts">
			<blockAlignment value="RIGHT" start="-1,0" stop="-1,-1"/>
			<lineStyle kind="LINEABOVE" start="-1,-2" stop="-1,-2"/>
		</blockTableStyle>

		<paraStyle name="conditions" fontName="Helvetica" fontSize="8" alignment="justify"/>
		<paraStyle name="name" fontName="Helvetica-Bold"/>
		<blockTableStyle id="products">
			 <blockFont name="Helvetica-BoldOblique" size="12" start="0,0" stop="-1,0"/>
			 <blockBackground colorName="grey" start="0,0" stop="-1,0"/>
			 <blockTextColor colorName="white" start="0,0" stop="-1,0"/>
			 <blockValign value="TOP"/>
			 <blockAlignment value="RIGHT" start="-2,0" stop="-1,-1"/>
			 <lineStyle kind="LINEBELOW" colorName="black" start="0,0" stop="-1,0"/>
		</blockTableStyle>
	</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="deposit-form"/>
	</xsl:template>

	<xsl:template match="deposit-form">
		<xsl:apply-templates select="deposit"/>
	</xsl:template>

	<xsl:template match="deposit">
		<xsl:apply-templates select="deposit-to"/>

		<nextFrame/>
		<setNextTemplate name="other_pages"/>

		<para>
			<b t="1">Inventory</b>: <i><xsl:value-of select="deposit-name"/></i>
		</para><para>
			<b t="1">Document type</b>: <i t="1">Deposit Form</i>
		</para><para>
			<b t="1">Document Number</b>: <i><xsl:value-of select="deposit-id"/></i>
		</para><para>
			<b t="1">Date</b>: <i><xsl:value-of select="deposit-date"/></i>
		</para>

		<spacer length="1cm" width="1mm"/>

		<xsl:apply-templates select="deposit-lines"/>

		<setNextTemplate name="first_page"/>
		<pageBreak/>
	</xsl:template>

	<xsl:template match="deposit-to">
		<para style="name">
			<xsl:value-of select="corporation/title"/>
			<xsl:text> </xsl:text>
			<xsl:value-of select="corporation/name"/>
		</para>
		<para style="name">
			<xsl:value-of select="person/title"/>
			<xsl:text> </xsl:text>
			<xsl:value-of select="person/name"/>
		</para>
		<para><xsl:value-of select="person/address/street"/></para>
		<para><xsl:value-of select="person/address/street2"/></para>
		<para><xsl:value-of select="person/address/postcode"/><xsl:text> </xsl:text><xsl:value-of select="person/address/city"/></para>
<!--		<para><xsl:value-of select="person/address/state"/></para>-->
		<para><xsl:value-of select="person/address/country"/></para>

		<spacer length="0.4cm" width="1mm"/>

		<para><b t="1">VAT</b>: <xsl:value-of select="person/vat"/></para>
	</xsl:template>

	<xsl:template match="deposit-lines">
		<blockTable colWidths="1.8cm,9cm,2.3cm,1.5cm,2.3cm" style="products">
			<tr>
				<td t="1">Num</td>
				<td t="1">Description</td>
				<td t="1">Auction</td>
				<td t="1">Limit</td>
				<td t="1">Estimate</td>
			</tr>
			<xsl:for-each select="deposit-line">
				<xsl:sort order="ascending" data-type="number" select="lot-num"/>
				<tr>
					<td><para><xsl:value-of select="lot-num"/></para></td>
					<td><para><xsl:value-of select="name"/></para></td>
					<td><para><xsl:value-of select="lot-date"/></para></td>
					<td>
						<xsl:if test="lot-limit != ''">
							<xsl:value-of select="round(lot-limit)"/>
						</xsl:if>
					</td>
					<td>
						<xsl:if test="lot-est1 != ''">
							<xsl:value-of select="round(lot-est1)"/>
						</xsl:if>
						<xsl:text> / </xsl:text>
						<xsl:if test="lot-est2 != ''">
							<xsl:value-of select="round(lot-est2)"/>
						</xsl:if>
					</td>
				</tr>
			</xsl:for-each>
		</blockTable>
	</xsl:template>

</xsl:stylesheet>
