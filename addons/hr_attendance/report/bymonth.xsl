<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fo="http://www.w3.org/1999/XSL/Format">

    <xsl:import href="hr_custom_default.xsl"/>
	<xsl:import href="hr_custom_rml.xsl"/>

    <xsl:template match="/">
        <xsl:call-template name="rml" />
    </xsl:template>


	<xsl:template name="stylesheet">
                <paraStyle name="title" fontName="Helvetica-Bold" fontSize="15.0" leading="17" alignment="CENTER" spaceBefore="12.0" spaceAfter="6.0"/>
				<paraStyle name="terp_header_Centre" fontName="Helvetica-Bold" fontSize="14.0" leading="17" alignment="CENTER" spaceBefore="12.0" spaceAfter="6.0"/>
				<paraStyle name="name" fontName="Helvetica" textColor="green" fontSize="7"/>
				<paraStyle name="normal" fontName="Helvetica" fontSize="6"/>
				<blockTableStyle id="week">
					<blockFont name="Helvetica-BoldOblique" size="6" alignment="center"  start="0,0" stop="-1,1"/>
					<blockFont name="Helvetica" size="5"  alignment="center"  start="0,1" stop="-1,-1"/>
					<blockBackground colorName="#AAAAAA" start="1,0" stop="-1,1"/>
					<lineStyle kind="LINEABOVE" colorName="black" start="0,0" stop="-1,0" />
					<lineStyle kind="LINEBEFORE" colorName="black" start="0,0" stop="-1,-1"/>
					<lineStyle kind="LINEAFTER" colorName="black" start="-1,0" stop="-1,-1"/>
					<lineStyle kind="LINEBELOW" colorName="black" start="0,0" stop="-1,-1"/>
					<blockValign value="TOP"/>
				</blockTableStyle>
	</xsl:template>

    <xsl:template name="story">
		<spacer length="1cm" />
		<xsl:apply-templates select="report/title"/>
		<spacer length="1cm" />
        <blockTable>
			<xsl:attribute name="style">week</xsl:attribute>
			<xsl:attribute name="colWidths"><xsl:value-of select="report/cols" /></xsl:attribute>
            <tr>
				<td><xsl:value-of select="/report/year" /></td>
				<xsl:for-each select="report/days/dayy">
					<td>
						<xsl:value-of select="attribute::name" />
					</td>
				</xsl:for-each>
            </tr>
            <tr>
				<td><xsl:value-of select="/report/month" /></td>
				<xsl:for-each select="report/days/dayy">
					<td>
						<xsl:value-of select="attribute::number" />
					</td>
				</xsl:for-each>
            </tr>
			<xsl:apply-templates select="report/user"/>
      </blockTable>
    </xsl:template>
    
    <xsl:template match="title">
        <para style="title">
            <xsl:value-of select="."/>
        </para>
        <spacer length="1cm"/>
    </xsl:template>
    
    <xsl:template match="user">
<!--		<tr></tr>-->
		<tr>
			<td>
				<para style="name"><xsl:value-of select="name" /></para>
			</td>
			<xsl:for-each select="day">
				<td><xsl:value-of select="wh" /></td>
			</xsl:for-each>
		</tr>

<!--		<tr>-->
<!--			<td>Worked</td>-->
<!--			-->
<!--		</tr>-->
    </xsl:template>
</xsl:stylesheet>
