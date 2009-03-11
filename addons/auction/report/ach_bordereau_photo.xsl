<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="../../base/report/corporate_defaults.xsl"/>
	<xsl:import href="../../base/report/rml_template.xsl"/>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template name="stylesheet">
		<paraStyle name="login-title" fontName="Helvetica" fontSize="12"/>
		<paraStyle name="login" fontName="Helvetica-Bold" fontSize="16"/>

		<blockTableStyle id="objects">
			 <blockFont name="Helvetica-BoldOblique" size="12" start="0,0" stop="-1,0"/>
			 <blockValign value="TOP"/>
			 <blockAlignment value="RIGHT" start="-1,0" stop="-1,-1"/>
			 <lineStyle kind="LINEBELOW" start="0,0" stop="-1,0"/>
		</blockTableStyle>

		<blockTableStyle id="object-totals">
			 <blockValign value="TOP"/>
			 <blockAlignment value="RIGHT"/>
			 <lineStyle kind="LINEABOVE" start="-1,0" stop="-1,0"/>
			 <lineStyle kind="LINEABOVE" start="-1,-1" stop="-1,-1"/>
		</blockTableStyle>
	</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="borderform-list"/>
	</xsl:template>

	<xsl:template match="borderform-list">
		<xsl:apply-templates select="borderform">
			<xsl:sort order="ascending" select="client_info/name"/>
		</xsl:apply-templates>
	</xsl:template>

	<xsl:template match="client_info">
		<para>
			<b>
				<xsl:value-of select="title" />
				<xsl:text> </xsl:text>
				<xsl:value-of select="name"/>
			</b>
		</para>
		<para><xsl:value-of select="street"/></para>
		<para><xsl:value-of select="street2"/></para>
		<para>
			<xsl:value-of select="zip"/>
			<xsl:text> </xsl:text>
			<xsl:value-of select="city"/>
		</para>
<!--		<para><xsl:value-of select="country"/></para>-->
	</xsl:template>

	<xsl:template match="borderform">
		<xsl:apply-templates select="client_info"/>

		<setNextTemplate name="other_pages"/>
		<nextFrame/>

		<para style="login-title" t="1">Plate Number:</para>
		<para style="login"><xsl:value-of select="login"/></para>

		<spacer length="1cm"/>

		<para>
			<b t="1">Document</b>: <xsl:text t="1">Buyer form</xsl:text>
		</para><para>
			<b t="1">Auction</b>: <xsl:value-of select="title"/>
		</para>

		<xsl:if test="client_info">
			<para>
				<b t="1">Customer Contact</b>:
				<xsl:value-of select="client_info/phone"/>
				<xsl:if test="number(string-length(client_info/mobile) &gt; 0) + number(string-length(client_info/phone) &gt; 0) = 2">
					<xsl:text> - </xsl:text>
				</xsl:if>
				<xsl:value-of select="client_info/mobile"/>
			</para><para>
				<b t="1">Customer Reference</b>: <xsl:value-of select="client_info/ref"/>
			</para>
		</xsl:if>

		<spacer length="1cm"/>

		<xsl:apply-templates select="objects"/>

		<setNextTemplate name="first_page"/>
		<pageBreak/>
	</xsl:template>

	<xsl:template match="objects">
		<blockTable colWidths="3.1cm,1.8cm,9.6cm,1.5cm,2.2cm" style="objects">
			<tr>
				<td/>
				<td t="1">Cat. N.</td>
				<td t="1">Description</td>
				<td t="1">Paid</td>
				<td t="1">Adj.(EUR)</td>
			</tr>
			<xsl:apply-templates select="object"/>
		</blockTable>
		<condPageBreak height="3.2cm"/>
		<blockTable colWidths="3.1cm,1.8cm,9.6cm,1.5cm,2.2cm" style="object-totals">
			<tr>
				<td/>
				<td/>
				<td/>
				<td t="1">Subtotal:</td>
				<td><xsl:value-of select="format-number(sum(object[price != '']/price), '#,##0.00')"/></td>
			</tr>
			<xsl:apply-templates select="cost"/>
			<tr>
				<td/>
				<td/>
				<td/>
				<td t="1">Total:</td>
				<td><xsl:value-of select="format-number(sum(object[price != '']/price) + sum(cost/amount), '#,##0.00')"/></td>
			</tr>
		</blockTable>
	</xsl:template>

	<xsl:template match="cost">
		<tr>
			<td/>
			<td/>
			<td/>
			<td><xsl:value-of select="name"/>:</td>
			<td><xsl:value-of select="format-number(amount, '#,##0.00')"/></td>
		</tr>
	</xsl:template>

	<xsl:template match="object">
		<tr>
			<td>
				<xsl:if test="image">
					<image width="2.5cm" height="2.2cm">
						<xsl:attribute name="name"><xsl:value-of select="image"/></xsl:attribute>
					</image>
				</xsl:if>
			</td>
			<td><xsl:value-of select="ref"/></td>
			<td>
				<para>
					<b><xsl:value-of select="title"/><xsl:text>. </xsl:text></b>
					<xsl:value-of select="desc"/>
				</para>
			</td>
			<td><xsl:if test="state='paid'"><xsl:text>X</xsl:text></xsl:if></td>
			<td>
				<xsl:if test="price!=''">
					<xsl:value-of select="format-number(price, '#,##0.00')"/>
				</xsl:if>
			</td>
		</tr>
	</xsl:template>

</xsl:stylesheet>
