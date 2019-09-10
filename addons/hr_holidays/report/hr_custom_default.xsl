<?xml version = '1.0' encoding="utf-8"?>

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">
	<xsl:template name="first_page_graphics_corporation">
		<!--logo-->
		<fill color="black"/>
        <stroke color="black"/>
        <setFont name="DejaVuSans" size="8"/>
        <drawString x="1.3cm" y="19.5cm"><xsl:value-of select="//report/header/date"/></drawString>
        <setFont name="DejaVuSans-Bold" size="10"/>
        <drawString x="13.8cm" y="19.5cm"><xsl:value-of select="//report/header/company"/></drawString>
        <stroke color="#000000"/>
        <lines>1.3cm 19.3cm 28.5cm 19.3cm</lines>
	</xsl:template>

	<xsl:template name="other_pages_graphics_corporation">
		<!--logo-->
		<fill color="black"/>
        <stroke color="black"/>
        <setFont name="DejaVuSans" size="8"/>
        <drawString x="1.3cm" y="19.5cm"><xsl:value-of select="//report/header/date"/></drawString>
        <setFont name="DejaVuSans-Bold" size="10"/>
        <drawString x="27.8cm" y="19.5cm"><xsl:value-of select="//report/header/company"/></drawString>
        <stroke color="#000000"/>
        <lines>1.3cm 19.3cm 28.5cm 19.3cm</lines>
 </xsl:template>

   <xsl:template name="first_page_frames">
			<frame id="col1" x1="2.0cm" y1="2.5cm" width="24.7cm" height="17cm"/>
	</xsl:template>

	<xsl:template name="other_pages_frames">
		<frame id="col1" x1="2.0cm" y1="2.5cm" width="24.7cm" height="17cm"/>
	</xsl:template>

</xsl:stylesheet>
