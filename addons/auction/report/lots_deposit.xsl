<?xml version="1.0" encoding="iso-8859-1"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">
	<xsl:import href="corporate_defaults.xsl"/>
	<xsl:import href="rml_template.xsl"/>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template name="stylesheet">
		<paraStyle name="date" fontName="Helvetica" fontSize="12" alignment="RIGHT"/>
		<paraStyle name="text" fontName="Helvetica" fontSize="12" alignment="JUSTIFY"/>
		<paraStyle name="name" fontName="Helvetica" fontSize="11"/>
		<paraStyle name="signature" fontName="Helvetica" fontSize="12" alignment="RIGHT"/>

		<blockTableStyle id="products">
			 <blockFont name="Helvetica-BoldOblique" size="12" start="0,0" stop="-1,0"/>
			 <blockBackground colorName="grey" start="0,0" stop="-1,0"/>
			 <blockTextColor colorName="white" start="0,0" stop="-1,0"/>
			 <blockValign value="TOP"/>
			 <blockAlignment value="RIGHT" start="-1,0" stop="-1,-1"/>
			 <lineStyle kind="LINEBELOW" colorName="black" start="0,0" stop="-1,0"/>
		</blockTableStyle>
	</xsl:template>

	<xsl:template name="first_page_frames">
		<frame id="address" x1="11cm" y1="21.5cm" width="6cm" height="4cm"/>
		<frame id="main" x1="2cm" y1="2.5cm" width="17.0cm" height="19cm"/>
	</xsl:template>

<!--	<xsl:template name="other_pages_frames">-->
<!--		<frame id="main" x1="2cm" y1="2.5cm" width="17.0cm" height="23cm"/>-->
<!--	</xsl:template>-->

	<xsl:template name="story">
		<xsl:apply-templates select="deposit-form"/>


	</xsl:template>

	<xsl:template match="deposit-form">
		<xsl:apply-templates select="deposit"/>


	</xsl:template>

	<xsl:template match="deposit">
		<xsl:apply-templates select="deposit-infos"/>

		<nextFrame/>
<!--		<setNextTemplate name="other_pages"/>-->

		<para style="date">Bruxelles, le <xsl:value-of select="//date"/></para>

		<spacer length="2cm" width="1mm"/>

		<para style="text" t="1">Madame, Monsieur</para>

		<spacer length="1cm" width="1mm"/>

		<para style="text"><xsl:text t="1">
		Veuillez trouver - ci-dessous - la liste des articles que vous avez déposés pour la vente publique du </xsl:text><xsl:value-of select="//auction-date"/>.
		</para>

		<spacer length="3mm" width="1mm"/>

		<para style="text" t="1">
		Les lots que vous avez déposés mais qui ne sont pas marqués ci-dessous passeront dans une vente prochaine.</para>

		<spacer length="3mm" width="1mm"/>

		<para style="text" t="1">
		En restant à votre disposition, je vous prie d'agréer, Madame, Monsieur, l'assurance de mes sentiments distingués.
		</para>

		<spacer length="1cm" width="1mm"/>

		<para style="signature"><xsl:value-of select="$signature"/></para>

		<spacer length="1cm" width="1mm"/>

		<xsl:apply-templates select="deposit-lines"/>

		<spacer length="0.5cm" width="1mm"/>

<!--		<setNextTemplate name="first_page"/>-->
<!--		<pageBreak/>-->
	</xsl:template>

	<xsl:template match="deposit-infos">
		<xsl:apply-templates select="deposit-to"/>
	</xsl:template>

	<xsl:template match="deposit-to">
		<para style="name"><xsl:value-of select="corporation/title"/><xsl:text> </xsl:text><xsl:value-of select="corporation/name"/></para>
		<para><xsl:value-of select="person/title"/><xsl:text> </xsl:text><xsl:value-of select="person/name"/></para>
		<para><xsl:value-of select="person/street"/></para>
		<para><xsl:value-of select="person/street2"/></para>
		<para><xsl:value-of select="person/postcode"/><xsl:text> </xsl:text><xsl:value-of select="person/city"/></para>
		<para><xsl:value-of select="person/state"/></para>
		<para><xsl:value-of select="person/country"/></para>
		<xsl:if test="corporation/vat != ''">
			<spacer length="0.4cm" width="1mm"/>
			<para><b t="1">VAT</b>: <xsl:value-of select="corporation/vat"/></para>
		</xsl:if>
	</xsl:template>

	<xsl:template match="deposit-lines">
		<blockTable colWidths="2cm,4cm,2cm,10cm,2cm" style="products" repeatRows="1">
			<tr>
				<td t="1">Cat. N.</td>
				<td t="1">Deposit Inventory</td>
				<td t="1">List N.</td>
				<td t="1">Description</td>
				<td t="1">Estimate</td>
			</tr>
			<xsl:for-each select="deposit-line">
				<xsl:sort order="ascending" data-type="number" select="lot-num"/>
				<tr>
					<td><para><xsl:value-of select="obj-num"/></para></td>
					<td><para><xsl:value-of select="bord-vnd-id"/></para></td>
					<td><para><xsl:value-of select="lot-num"/></para></td>
					<td>
						<para>
							<xsl:if test="artist != ''">
								<b><xsl:value-of select="artist"/></b><xsl:text>: </xsl:text>
							</xsl:if>
							<xsl:value-of select="name"/>
						</para>
					</td>
					<td>
						<xsl:value-of select="round(lot-est1)"/>
						<xsl:text> / </xsl:text>
						<xsl:value-of select="round(lot-est2)"/>
					</td>
				</tr>
			</xsl:for-each>
		</blockTable>
	</xsl:template>
</xsl:stylesheet>