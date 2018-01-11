<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="custom_default.xsl"/>
	<xsl:import href="custom_rml.xsl"/>
	<xsl:variable name="page_format">a4_normal</xsl:variable>


	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<!-- stylesheet -->

	<xsl:template name="stylesheet">
		<paraStyle name="title" fontName="Helvetica-Bold" fontSize="15.0" alignment="center"/>
		<paraStyle name="terp_tblheader_General" fontName="Helvetica-Bold" fontSize="8.0" leading="10" alignment="LEFT"/>
		<paraStyle name="terp_default_8" fontName="Helvetica" fontSize="8.0" leading="10" alignment="LEFT" spaceBefore="0.0" spaceAfter="0.0"/>
		<paraStyle name="terp_tblheader_Details_Right" fontName="Helvetica" fontSize="8.0" leading="10" alignment="RIGHT"/>
		<paraStyle name="terp_tblheader_Details_Right_bold" fontName="Helvetica-Bold" fontSize="8.0" leading="10" alignment="RIGHT"/>

		<blockTableStyle id="header">
			<blockValign value="TOP"/>
			 <blockAlignment value="RIGHT"/>
			 <lineStyle kind="LINEBELOW" colorName="#000000" start="0,0" stop="-1,-1"/>
		</blockTableStyle>
		<blockTableStyle id="lines">
			<blockValign value="TOP"/>
			 <blockAlignment value="RIGHT"/>
			 <lineStyle kind="LINEBELOW" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
		</blockTableStyle>
		<blockTableStyle id="total">
			<blockValign value="TOP"/>
			<blockAlignment value="RIGHT"/>
			<lineStyle kind="LINEBELOW" colorName="#FFFFFF" start="0,0" stop="-1,-1"/>
		</blockTableStyle>
		<blockTableStyle id="sub_total">
			<blockValign value="TOP"/>
			 <blockAlignment value="RIGHT"/>
			 <lineStyle kind="LINEBELOW" colorName="#FFFFFF" start="0,0" stop="-1,-1"/>
		</blockTableStyle>
</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="report"/>
	</xsl:template>

	<xsl:template match="report">
		<xsl:apply-templates select="config"/>
		<xsl:apply-templates select="title"/>
		<xsl:apply-templates select="lines"/>
	</xsl:template>

	<xsl:template match="config">
		<para style="title">
		<xsl:value-of select="report-header"/>
		</para>
	</xsl:template>

	<xsl:template match="title">
		<para style="title">
		<xsl:value-of select="."/>
		</para>
		<spacer length="1cm" width="2mm"/>
	</xsl:template>


	<xsl:template match="header">
		<tr>
		<xsl:for-each select="field">
			<td>
			<para style="terp_tblheader_General">
			<xsl:value-of select="."/>
			</para>
			</td>
		</xsl:for-each>
		</tr>
	</xsl:template>

	<xsl:template match="lines">

        <xsl:apply-templates select="title"/>
		<blockTable>
		<xsl:attribute name="style"><xsl:value-of select="@style"/></xsl:attribute>
		 <xsl:attribute name="colWidths">
			 <xsl:value-of select="../config/tableSize"/>
		 </xsl:attribute>

		<xsl:apply-templates select="row"/>

		</blockTable>

		<xsl:if test="@style!='header'">
			<spacer length="2mm" width="2mm"/>

		</xsl:if>
		<xsl:if test="@style='total'">
			<xsl:if test="position() &lt; last()">
				<pageBreak/>
			</xsl:if>
		</xsl:if>

	</xsl:template>

	<xsl:template match="row">
		<tr>
		<xsl:apply-templates select="col"/>
		</tr>
	</xsl:template>

	<xsl:template match="col">
		<td>
			<xsl:choose>
				<xsl:when test="@para='yes'">
					<xsl:choose>
						<xsl:when test="@tree='yes'">
							<para style="terp_default_8">
								<xsl:attribute name="leftIndent"><xsl:value-of select="@space"/></xsl:attribute>
								<xsl:value-of select="."/>
							</para>
						</xsl:when>
						<xsl:otherwise>
							<para style="terp_default_8">
								<xsl:value-of select="."/>
							</para>
						</xsl:otherwise>
					</xsl:choose>
				</xsl:when>
				<xsl:when test="@f='yes'">
					<para style="terp_tblheader_Details_Right">
						<xsl:value-of select="."/>
					</para>
				</xsl:when>
				<xsl:when test="@t='yes'">
					<para style="terp_tblheader_Details_Right_bold">
						<xsl:value-of select="."/>
					</para>
				</xsl:when>
				<xsl:otherwise>
					<para style="terp_tblheader_General">
						<xsl:value-of select="."/>
					</para>
				</xsl:otherwise>
			</xsl:choose>
		</td>
	</xsl:template>

</xsl:stylesheet>
