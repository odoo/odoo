<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="custom_default.xsl"/>
	<xsl:import href="custom_rml.xsl"/>
	
	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<!-- stylesheet -->

	<xsl:template name="stylesheet">
		<paraStyle name="title" fontName="Helvetica-Bold" fontSize="22" alignment="center"/>
		
		<blockTableStyle id="header">
			<blockBackground colorName="grey" start="0,0" stop="-1,0"/>
			<blockValign value="TOP"/>
			 <blockAlignment value="RIGHT"/>
			 <lineStyle kind="GRID" colorName="black"/>
		</blockTableStyle>
		<blockTableStyle id="lines">
			<blockValign value="TOP"/>
			 <blockAlignment value="RIGHT"/>
			 <lineStyle kind="GRID" colorName="black"/>
		</blockTableStyle>
		<blockTableStyle id="total">
			<blockBackground colorName="grey" start="0,0" stop="-1,0"/>
			<blockValign value="TOP"/>
			<blockAlignment value="RIGHT"/>
			<lineStyle kind="GRID" colorName="black"/>
		</blockTableStyle>
		<blockTableStyle id="sub_total">
			<blockBackground colorName="lightgrey" start="0,0" stop="-1,0"/>
			<blockValign value="TOP"/>
			 <blockAlignment value="RIGHT"/>
		</blockTableStyle>
</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="report"/>
	</xsl:template>
	
	<xsl:template match="report">
		<xsl:apply-templates select="config"/>
		<blockTable style="header">
		 <xsl:attribute name="colWidths">
			 <xsl:value-of select="./config/tableSize"/>
		 </xsl:attribute>
		
		<xsl:apply-templates select="header"/>
		</blockTable>
		<xsl:apply-templates select="title"/>
		<xsl:apply-templates select="lines"/>
	</xsl:template>

	<xsl:template match="config">
		<xpre style="title">
		<xsl:value-of select="report-header"/>
		</xpre>
		<spacer length="1cm" width="2mm"/>
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
			<para>
			<xsl:value-of select="."/>
			</para>
			</td>
		</xsl:for-each>
		</tr>
	</xsl:template>

	<xsl:template match="lines">
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
							<para>
								<xsl:attribute name="leftIndent"><xsl:value-of select="@space"/></xsl:attribute>
								<xsl:value-of select="."/>
							</para>
						</xsl:when>
						<xsl:otherwise>
							<para>
								<xsl:value-of select="."/>
							</para>
						</xsl:otherwise>
					</xsl:choose>
				</xsl:when>
				<xsl:otherwise>
					<xpre>
						<xsl:value-of select="."/>
					</xpre>
				</xsl:otherwise>
			</xsl:choose>
		</td>
	</xsl:template>

</xsl:stylesheet>
