<?xml version = '1.0' encoding="utf-8"?>

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">
	<xsl:variable name="signature" select="//corporate-header/user/signature"/>
	<xsl:variable name="title">Open ERP Report</xsl:variable>
	<xsl:variable name="leftMargin">1cm</xsl:variable>
	<xsl:variable name="rightMargin">1cm</xsl:variable>
	<xsl:variable name="topMargin">1cm</xsl:variable>
	<xsl:variable name="bottomMargin">1cm</xsl:variable>
	<xsl:variable name="pageSize">21cm,29.7cm</xsl:variable>

	<xsl:variable name="page_format">a4_letter</xsl:variable>

	<xsl:template name="first_page_graphics_corporation">
		<!--logo-->
		<setFont name="Helvetica" size="14"/>
		<fill color="black"/>
		<stroke color="black"/>
		<drawString x="1cm" y="27.6cm"><xsl:value-of select="//corporate-header/corporation/name"/></drawString>
		<lines>1cm 28.4cm 20cm 28.4cm</lines>
		<lines>1cm 25.4cm 7cm 25.4cm</lines>

		<setFont name="Helvetica" size="10"/>
		<drawRightString x="20cm" y="28.5cm"><xsl:value-of select="//corporate-header/corporation/rml_header1"/></drawRightString>
		<drawString x="1cm" y="27cm"><xsl:value-of select="//corporate-header/corporation/street"/></drawString>
		<drawString x="1cm" y="26.5cm">
			<xsl:value-of select="//corporate-header/corporation/zip"/>
			<xsl:text> </xsl:text>
			<xsl:value-of select="//corporate-header/corporation/city"/>
			<xsl:text> - </xsl:text>
			<xsl:value-of select="//corporate-header/corporation/country"/>
		</drawString>
		<drawString x="1cm" y="26cm">Phone:</drawString>
		<drawRightString x="7cm" y="26cm"><xsl:value-of select="//corporate-header/corporation/phone"/></drawRightString>
		<drawString x="1cm" y="25.5cm">Mail:</drawString>
		<drawRightString x="7cm" y="25.5cm"><xsl:value-of select="//corporate-header/corporation/email"/></drawRightString>


		<!--page bottom-->

		<lines>1.5cm 2.2cm 19.9cm 2.2cm</lines>
		<drawCentredString x="10.5cm" y="1.7cm"><xsl:value-of select="//corporate-header/corporation/rml_footer"/></drawCentredString>
		<drawCentredString x="10.5cm" y="0.8cm">Your contact : <xsl:value-of select="//corporate-header/user/name"/></drawCentredString>

	</xsl:template>


	<xsl:template name="other_pages_graphics_corporation">
		<!--logo-->
		<setFont name="Helvetica" size="14"/>
		<fill color="black"/>
		<stroke color="black"/>
		<drawString x="1cm" y="27.6cm"><xsl:value-of select="//corporate-header/corporation/name"/></drawString>
		<lines>1cm 25.4cm 20cm 25.4cm</lines>
<!--		<lines>1cm 25.7cm 7cm 25.7cm</lines>-->

		<setFont name="Helvetica" size="10"/>
		<drawRightString x="1cm" y="27.5cm"><xsl:value-of select="//corporate-header/corporation/rml_header1"/></drawRightString>
		<drawString x="1cm" y="27cm"><xsl:value-of select="//corporate-header/corporation/street"/></drawString>
		<drawString x="1cm" y="26.5cm">
			<xsl:value-of select="//corporate-header/corporation/zip"/>
			<xsl:text> </xsl:text>
			<xsl:value-of select="//corporate-header/corporation/city"/>
			<xsl:text> - </xsl:text>
			<xsl:value-of select="//corporate-header/corporation/country"/>
		</drawString>
		<drawString x="1cm" y="26cm">Phone:</drawString>
		<drawRightString x="7cm" y="26cm"><xsl:value-of select="//corporate-header/corporation/phone"/></drawRightString>
		<drawString x="1cm" y="25.5cm">Mail:</drawString>
		<drawRightString x="7cm" y="25.5cm"><xsl:value-of select="//corporate-header/corporation/email"/></drawRightString>

		<!--page bottom-->

		<lines>1.5cm 1.2cm 19.9cm 1.2cm</lines>
		<drawCentredString x="10.5cm" y="1.7cm"><xsl:value-of select="//corporate-header/corporation/rml_footer"/></drawCentredString>
<!--		<drawCentredString x="10.5cm" y="0.8cm">Your contact : <xsl:value-of select="//corporate-header/user/name"/></drawCentredString>-->
	</xsl:template>

	<xsl:template name="first_page_frames">
		<xsl:if test="$page_format='a4_normal'">
			<frame id="main" x1="1cm" y1="2.5cm" width="19.0cm" height="22.0cm"/>
		</xsl:if>

		<xsl:if test="$page_format='a4_letter'">
			<frame id="address" x1="11cm" y1="21.5cm" width="6cm" height="4cm"/>
			<frame id="main" x1="1cm" y1="2.5cm" width="19.0cm" height="17.5cm"/>
		</xsl:if>
	</xsl:template>

	<xsl:template name="other_pages_frames">
		<frame id="main" x1="1cm" y1="2.5cm" width="19.0cm" height="22cm"/>
	</xsl:template>

</xsl:stylesheet>
