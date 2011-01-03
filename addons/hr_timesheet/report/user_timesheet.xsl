<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fo="http://www.w3.org/1999/XSL/Format">

    <xsl:import href="custom_default.xsl"/>
	<xsl:import href="custom_rml.xsl"/>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template name="stylesheet">
				<paraStyle name="normal" fontName="Helvetica" fontSize="6" alignment="left" />
				<paraStyle name="normal-title" fontName="Helvetica" fontSize="6" />
				<paraStyle name="title" fontName="Helvetica" fontSize="18" alignment="center" />
				<paraStyle name="employee" fontName="Helvetica-Oblique" fontSize="10" textColor="blue" />
				<paraStyle name="glande" textColor="red" fontSize="7" fontName="Helvetica"/>
				<paraStyle name="normal_people" textColor="green" fontSize="7" fontName="Helvetica"/>
				<paraStyle name="esclave" textColor="purple" fontSize="7" fontName="Helvetica"/>
				<blockTableStyle id="month">
					<blockAlignment value="CENTER" start="1,0" stop="-1,-1" />
					<blockFont name="Helvetica" size="8" start="0,0" stop="-1,1"/>
					<blockFont name="Helvetica" size="6" start="0,2" stop="-2,-2"/>
					<blockFont name="Helvetica-BoldOblique" size="8" start="0,-1" stop="-1,-1"/>
					<blockBackground colorName="#AAAAAA" start="1,0" stop="-2,1"/>
					<xsl:for-each select="/report/days/day[@weekday=6 or @weekday=7]">
						<xsl:variable name="col" select="attribute::number" />
						<blockBackground>
							<xsl:attribute name="colorName">lightgrey</xsl:attribute>
							<xsl:attribute name="start">
								<xsl:value-of select="$col" />
								<xsl:text>,0</xsl:text>
							</xsl:attribute>
							<xsl:attribute name="stop">
								<xsl:value-of select="$col" />
								<xsl:text>,-1</xsl:text>
							</xsl:attribute>
						</blockBackground>
					</xsl:for-each>
					<lineStyle kind="LINEABOVE" colorName="black" start="0,0" stop="-1,-1" />
					<lineStyle kind="LINEBEFORE" colorName="black" start="0,0" stop="-1,-1"/>
					<lineStyle kind="LINEAFTER" colorName="black" start="-1,0" stop="-1,-1"/>
					<lineStyle kind="LINEBELOW" colorName="black" start="0,-1" stop="-1,-1"/>
					<blockValign value="TOP"/>
				</blockTableStyle>
	</xsl:template>

    <xsl:template name="story">
		<spacer length="1cm" />
		<para style="title" t="1">Timesheet by Employee</para>
		<spacer length="1cm" />
		<para style="employee"><xsl:value-of select="/report/employee" /></para>
		<spacer length="1cm" />
		<blockTable>
			<xsl:attribute name="style">month</xsl:attribute>
			<xsl:attribute name="colWidths"><xsl:value-of select="report/cols" /></xsl:attribute>
            <tr>
				<td><xsl:value-of select="report/date/attribute::year" /></td>
				<xsl:for-each select="report/days/day">
					<td>
						<xsl:value-of select="attribute::name" />
					</td>
				</xsl:for-each>
				<td></td>
            </tr>
            <tr>
				<td><xsl:value-of select="report/date/attribute::month" /></td>
				<xsl:for-each select="report/days/day">
					<td>
						<xsl:value-of select="attribute::number" />
					</td>
				</xsl:for-each>
				<td t="1">Total</td>
            </tr>
			<xsl:apply-templates select="report/account"/>
			<tr>
				<td t="1">Sum</td>
				<xsl:for-each select="report/days/day">
					<xsl:variable name="today" select="attribute::number" />
					<td>
						<para style="normal">
							<xsl:choose>
								<xsl:when test="sum(//time-element[@date=$today]) &lt; 7.5">
									<xsl:attribute name="style">glande</xsl:attribute>
								</xsl:when>
								<xsl:when test="sum(//time-element[@date=$today]) &lt; 8.5 and sum(//time-element[@date=$today]) &gt;= 7.5">
									<xsl:attribute name="style">normal_people</xsl:attribute>
								</xsl:when>
								<xsl:otherwise>
									<xsl:attribute name="style">esclave</xsl:attribute>
								</xsl:otherwise>
							</xsl:choose>
							<xsl:value-of select="format-number(sum(//time-element[@date=$today]),'##.##')" />
						</para>
					</td>
				</xsl:for-each>
				<td>
					<xsl:value-of select="format-number(sum(//time-element),'##.##')" />
				</td>
			</tr>
        </blockTable>
    </xsl:template>

    <xsl:template match="account">
		<xsl:variable name="aid" select="attribute::id" />

		<tr>
			<td>
				<para style="normal-title"><xsl:value-of select="attribute::name" /></para>
			</td>
			<xsl:for-each select="/report/days/day">
				<xsl:variable name="today" select="attribute::number" />
				<td>
					<para style="normal"><xsl:value-of select="//account[@id=$aid]/time-element[@date=$today]" /></para>
				</td>
			</xsl:for-each>
			<td>
				<para style="normal"><xsl:value-of select="format-number(sum(//account[@id=$aid]/time-element),'##.##')" /></para>
			</td>
		</tr>
    </xsl:template>
</xsl:stylesheet>
