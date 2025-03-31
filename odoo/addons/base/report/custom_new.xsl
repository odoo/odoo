<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="../../base/report/custom_default_printscreen.xsl"/>
	<xsl:import href="../../base/report/custom_rml_printscreen.xsl"/>
	<xsl:template match="/">
		<xsl:call-template name="rml">
			<xsl:with-param name="pageSize" select="report/config/PageSize"/>
			<xsl:with-param name="page_format" select="report/config/PageFormat"/>
		</xsl:call-template>
	</xsl:template>

	<!-- stylesheet -->

	<xsl:template name="stylesheet">
		<paraStyle name="title" fontName="Helvetica-Bold" fontSize="22" alignment="center"/>
		<paraStyle name="test" alignment="left" />
        <paraStyle name="float_right" alignment="left"/>
        <paraStyle name="tbl_heading" alignment="left"/>
		<blockTableStyle id="products">
			<!--<blockBackground colorName="grey" start="0,0" stop="-1,0"/> -->
			<lineStyle kind="LINEBELOW" colorName="#000000" start="0,0" stop="-1,0"/>
			<blockValign value="TOP"/>
			 <blockAlignment value="RIGHT"/>
			 <lineStyle kind="LINEBELOW" colorName="#e6e6e6" start="0,1" stop="-1,-1"/>
			<!-- <lineStyle kind="GRID" colorName="black"/> -->
		</blockTableStyle>
	</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="report"/>
	</xsl:template>

	<xsl:template match="report">
		<xsl:apply-templates select="config"/>
		<!--<setNextTemplate name="other_pages"/>-->
		<blockTable style="products">
		<xsl:if test="string-length(./config/tableSize)&gt;1">
			<xsl:attribute name="colWidths">
				 <xsl:value-of select="./config/tableSize"/>
			</xsl:attribute>
		</xsl:if>

		<xsl:apply-templates select="header"/>
		<xsl:apply-templates select="lines"/>
		</blockTable>
	</xsl:template>

	<xsl:template match="config">
		<para style="title">
		<xsl:value-of select="report-header"/>
		</para>
		<spacer length="1cm" width="2mm"/>
	</xsl:template>

	<xsl:template match="header">
		<tr>
		<xsl:for-each select="field">
			<td>
			<para style="tbl_heading"><font fontName="Helvetica-Bold" fontSize="9">
			<xsl:value-of select="."/></font>
			</para>
			</td>
		</xsl:for-each>
		</tr>
	</xsl:template>

	<xsl:template match="lines">
		<xsl:apply-templates select="row"/>
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
							<para style="test">
								<xsl:attribute name="leftIndent"><xsl:value-of select="@space"/></xsl:attribute>
								<font fontName="Helvetica" fontSize="9">
								<xsl:value-of select="."/>
								</font>
							</para>
						</xsl:when>
                       <xsl:when test="@tree='float'">
                           <para style="float_right"><font fontName="Helvetica" fontSize="9">
                               <xsl:value-of select="."/>
                               </font></para>
                       </xsl:when>

						<xsl:otherwise>
							<para style="test">
								<font fontName="Helvetica" fontSize="9">
								<xsl:value-of select="."/>
								</font>
							</para>
						</xsl:otherwise>
					</xsl:choose>
				</xsl:when>
				<xsl:when test="@para='group'">
					<xsl:choose>
						<xsl:when test="@tree='yes'">
							<para>
								<xsl:attribute name="leftIndent"><xsl:value-of select="@space"/></xsl:attribute>
								<font fontName="Helvetica-bold" fontSize="9">
								<xsl:value-of select="."/>
								</font>
							</para>
						</xsl:when>
                       <xsl:when test="@tree='float'">
                           <para style="float_right"><font fontName="Helvetica-bold" fontSize="9" color="black">
                               <xsl:value-of select="."/>
                               </font></para>
                       </xsl:when>
                       <xsl:when test="@tree='undefined'">
                            <para>
                                <xsl:attribute name="leftIndent">
                                    <xsl:value-of select="@space"/>
                                </xsl:attribute>
                                <font fontName="Helvetica-Bold" fontSize="9" color="gray">
                                    <xsl:value-of select="."/>
                                </font>
                            </para>
                       </xsl:when>

						<xsl:otherwise>
							<para>
								<font fontName="Helvetica-bold" fontSize="9" color="black">
								<xsl:value-of select="."/>
								</font>
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


<!--	<xsl:template match="col">
		<td>
		<xsl:if test="@tree='yes'">
			<xsl:choose>
				<xsl:when test="@para='yes'">
					<para>
						<xsl:attribute name="leftIndent"><xsl:value-of select="@space"/></xsl:attribute>
						<xsl:value-of select="."/>
					</para>
				</xsl:when>
				<xsl:otherwise>
					<xpre>
						<xsl:value-of select="."/>
					</xpre>
				</xsl:otherwise>
			</xsl:choose>
		</xsl:if>
		<xsl:if test="@tree!='yes'">
			<xpre>
			<xsl:value-of select="."/>
			</xpre>
		</xsl:if>
		</td>
	</xsl:template>
-->
</xsl:stylesheet>
