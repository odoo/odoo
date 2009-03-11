<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="../../base/report/corporate_defaults.xsl"/>
	<xsl:import href="../../base/report/rml_template.xsl"/>
	
	<xsl:template name="first_page_frames">
		<frame id="main" x1="1cm" y1="2.5cm" width="19.0cm" height="23cm"/>
	</xsl:template>
	
	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<!-- stylesheet -->

	<xsl:template name="stylesheet">
		<blockTableStyle id="products">
			 <blockFont name="Helvetica-Bold" size="10" start="0,0" stop="-1,0"/>
			 <blockBackground colorName="grey" start="0,0" stop="-1,0"/>
			 <blockTextColor colorName="white" start="0,0" stop="-1,0"/>
			 <blockValign value="TOP"/>
			 <blockAlignment value="CENTER" start="0,0" stop="-1,0"/>
			 <blockAlignment value="RIGHT" start="1,1" stop="-1,-1"/>
			 <lineStyle kind="GRID" colorName="black"/>
		</blockTableStyle>
	</xsl:template>
	
	<xsl:template name="story">
		<xsl:apply-templates select="lotlist"/>
	</xsl:template>
	
	<xsl:template name="lotlist">
		<nextFrame/>
		<setNextTemplate name="other_pages"/>
		<xsl:apply-templates select="lot"/>
	</xsl:template>
	
	<xsl:template match="lot">
		
		<spacer length="1cm"/>

		<blockTable colWidths="8cm,2.5cm,2cm,2cm,2cm,2.5cm" style="products" repeatRows="1">
			<tr>
				<td t="1">Product</td><td t="1">Variants</td><td t="1">Amount</td><td t="1">UoM</td><td t="1">Unit Price</td><td t="1">Value</td>
			</tr>
			<xsl:apply-templates select="product"/>
		</blockTable>
		
		<setNextTemplate name="other_pages"/>
		<pageBreak/>
<!--
		<setNextTemplate name="first_page"/>
		<nextFrame/>
-->
	</xsl:template>
	
	<xsl:template match="product">
		<tr>
			<td><para><xsl:value-of select="name"/></para></td>
			<td><para><xsl:value-of select="variants"/></para></td>
			<td><xsl:value-of select="amount"/></td>
			<td><xsl:value-of select="uom"/></td>
			<td><xsl:value-of select="price"/></td>
			<td><xsl:value-of select="amount * price"/></td>
<!--		<td><xsl:value-of select="//product_amount[id=$product_id]/amount"/></td>
			<td><xsl:value-of select="//product_amount[id=$product_id]/amount * price"/></td> -->
		</tr>
	</xsl:template>

</xsl:stylesheet>
