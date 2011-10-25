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
		<fill color="black"/>
        <stroke color="black"/>
        <setFont name="DejaVu Sans" size="8"/>
        <drawString x="1.3cm" y="28.3cm"><xsl:value-of select="//date"/></drawString>
        <setFont name="DejaVu Sans Bold" size="10"/>
        <drawString x="9.8cm" y="28.3cm"><xsl:value-of select="//company"/></drawString>
        <stroke color="#000000"/>
        <lines>1.3cm 28.1cm 20cm 28.1cm</lines>

	</xsl:template>


	<xsl:template name="other_pages_graphics_corporation">
		<!--logo-->
		<fill color="black"/>
        <stroke color="black"/>
        <setFont name="DejaVu Sans" size="8"/>
        <drawString x="1.3cm" y="28.3cm"><xsl:value-of select="//date"/></drawString>
        <setFont name="DejaVu Sans Bold" size="10"/>
        <drawString x="9.8cm" y="28.3cm"><xsl:value-of select="//company"/></drawString>
        <stroke color="#000000"/>
        <lines>1.3cm 28.1cm 20cm 28.1cm</lines>
 </xsl:template>

	<xsl:template name="first_page_frames">
		<xsl:if test="$page_format='a4_normal'">
			<frame id="main" x1="1cm" y1="2.5cm" width="19.0cm" height="25.0cm"/>
		</xsl:if>

		<xsl:if test="$page_format='a4_letter'">
			<frame id="address" x1="11cm" y1="21.5cm" width="6cm" height="4cm"/>
			<frame id="main" x1="1cm" y1="2.5cm" width="19.0cm" height="17.5cm"/>
		</xsl:if>
	</xsl:template>

	<xsl:template name="other_pages_frames">
		<frame id="main" x1="1cm" y1="2.5cm" width="19.0cm" height="25.0cm"/>
	</xsl:template>

</xsl:stylesheet>
