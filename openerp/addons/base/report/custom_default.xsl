<?xml version = '1.0' encoding="utf-8"?>

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">
	<xsl:variable name="signature" select="//corporate-header/signature"/>
	<xsl:variable name="title">OpenERP Report</xsl:variable>
	<xsl:variable name="leftMargin">1cm</xsl:variable>
	<xsl:variable name="rightMargin">1cm</xsl:variable>
	<xsl:variable name="topMargin">1cm</xsl:variable>
	<xsl:variable name="bottomMargin">1cm</xsl:variable>
	<!--:variable name="pageSize">29.7cm,21cm</xsl:variable> Or use default width and height for frame -->
    <xsl:variable name="pageSize">
        <xsl:value-of select="/report/config/PageSize"/>
    </xsl:variable>
	<xsl:variable name="page_format">a4_letter</xsl:variable>

	<xsl:template name="first_page_frames">
		<frame id="column" x1="1.5cm" y1="1.5cm">
			<xsl:attribute name="width">
				<xsl:value-of select="/report/config/PageWidth - 85"/>
			</xsl:attribute> 
			<xsl:attribute name="height">
				<xsl:value-of select="/report/config/PageHeight - 100"/>
			</xsl:attribute> 
		</frame>
	</xsl:template>

	<xsl:template name="other_pages_frames">
		<frame id="column" x1="1.5cm" y1="1.5cm">
			<xsl:attribute name="width">
				<xsl:value-of select="/report/config/PageWidth - 85"/>
			</xsl:attribute> 
			<xsl:attribute name="height">
				<xsl:value-of select="/report/config/PageHeight - 100"/>
			</xsl:attribute> 
		</frame>
	</xsl:template>

</xsl:stylesheet>
