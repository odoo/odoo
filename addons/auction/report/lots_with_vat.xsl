<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fo="http://www.w3.org/1999/XSL/Format">

    <xsl:import href="corporate_defaults.xsl"/>
    <xsl:import href="rml_template.xsl"/>
    <xsl:variable name="page_format">a4_normal</xsl:variable>

    <xsl:template name="stylesheet">
        <blockTableStyle id="vat_table">
            <blockFont name="Helvetica-BoldOblique" size="10" start="0,0" stop="-1,0"/>
            <blockBackground colorName="grey" start="0,0" stop="-1,0"/>
            <lineStyle kind="LINEAFTER" colorName="grey" start="0,0" stop="-1,-1"/>
            <lineStyle kind="LINEBELOW" colorName="grey" start="0,-1" stop="-1,-1"/>
            <lineStyle kind="LINEBEFORE" colorName="grey" start="0,0" stop="0,-1"/>
            <blockValign value="TOP"/>
        </blockTableStyle>
        <blockTableStyle id="vat_total">
            <blockBackground colorName="lightgrey" start="0,0" stop="-1,0"/>
            <blockBackground colorName="lightgrey" start="0,-1" stop="-1,-1"/>
            <lineStyle kind="LINEAFTER" colorName="grey" start="0,0" stop="-1,-1"/>
            <lineStyle kind="LINEBELOW" colorName="grey" start="0,-1" stop="-1,-1"/>
            <lineStyle kind="LINEBEFORE" colorName="grey" start="0,0" stop="0,-1"/>
            <blockValign value="TOP"/>
        </blockTableStyle>
    </xsl:template>

    <xsl:template match="/">
        <xsl:call-template name="rml" />
    </xsl:template>

	<xsl:template name="story">
		<h3>TVA = 6%</h3>
		<blockTable colWidths="3cm,3cm,3cm,3cm,3cm,3cm" style="vat_table" repeatRows="1">
			<tr>
				<td>Lot number</td>
				<td>Depositer price</td>
				<td>Commission</td>
				<td>Adjudicated</td>
				<td>Expenses</td>
				<td>Buyer price</td>
			</tr>
			<xsl:apply-templates select="/lots/lot[vat='VAT 6%']">
				<xsl:sort select="number" data-type="number" />
			</xsl:apply-templates>
		</blockTable>
		<blockTable colWidths="3cm,3cm,3cm,3cm,3cm,3cm" style="vat_total">
			<tr>
				<td>Total </td>
				<td>

					<xsl:value-of select="sum(/lots/lot[vat='VAT 6%'][adjudicated != '']/adjudicated) + sum(/lots/lot[vat='VAT 6%']/commission/amount)" />
				</td>
				<td>
					<xsl:value-of select="sum(/lots/lot[vat='VAT 6%']/commission/amount)" />
				</td>
				<td>
					<xsl:value-of select="sum(/lots/lot[vat='VAT 6%'][adjudicated != '']/adjudicated)" />
				</td>
				<td>
					<xsl:value-of select="sum(/lots/lot[vat='VAT 6%']/expenses/amount)" />
				</td>
				<td>
					<xsl:value-of select="sum(/lots/lot[vat='VAT 6%'][adjudicated != '']/adjudicated) + sum(/lots/lot[vat='VAT 6%']/expenses/amount)" />
				</td>
			</tr>
		</blockTable>
		<h3>VAT = 21%</h3>
		<blockTable colWidths="3cm,3cm,3cm,3cm,3cm,3cm" style="vat_table" repeatRows="1">
			<tr>
				<td>Lot number</td>
				<td>Depositer price</td>
				<td>Commission</td>
				<td>Adjudicated</td>
				<td>Expenses</td>
				<td>Buyer price</td>
			</tr>
			<xsl:apply-templates select="/lots/lot[vat='VAT 21%']">
				<xsl:sort select="number" data-type="number"/>
			</xsl:apply-templates>
		</blockTable>
		<blockTable colWidths="3cm,3cm,3cm,3cm,3cm,3cm" style="vat_total">
			<tr>
				<td>Total</td>
				<td>
					<xsl:value-of select="sum(/lots/lot[vat='VAT 21%'][adjudicated != '']/adjudicated) + sum(/lots/lot[vat='VAT 21%']/commission/amount)" />
					<xsl:value-of select="vat" />
				</td>
				<td>
					<xsl:value-of select="sum(/lots/lot[vat='VAT 21%']/commission/amount)" />
				</td>
				<td>
					<xsl:value-of select="sum(/lots/lot[vat='VAT 21%'][adjudicated != '']/adjudicated)" />
				</td>
				<td>
					<xsl:value-of select="sum(/lots/lot[vat='VAT 21%']/expenses/amount)" />
				</td>
				<td>
					<xsl:value-of select="sum(/lots/lot[vat='VAT 21%'][adjudicated != '']/adjudicated) + sum(/lots/lot[vat='TVA 21%']/expenses/amount)" />
				</td>
			</tr>
		</blockTable>
    </xsl:template>

	<xsl:template match="lot">
		<tr>

			<td><xsl:value-of select="number" /></td>
			<td>
				<xsl:choose>
					<xsl:when test="adjudicated != ''">
						<xsl:value-of select="number(adjudicated) + sum(commission/amount)" />
					</xsl:when>
					<xsl:otherwise>
						<xsl:text name="adj">0</xsl:text>
					</xsl:otherwise>
				</xsl:choose>
			</td>
			<td>
				<xsl:value-of select="sum(commission/amount)" />
			</td>
			<td>
				<xsl:choose>
					<xsl:when test="adjudicated != ''">
						<xsl:value-of select="adjudicated" />
					</xsl:when>
					<xsl:otherwise>
						<xsl:text name="adj">0</xsl:text>
					</xsl:otherwise>
				</xsl:choose>
			</td>
			<td>
				<xsl:value-of select="sum(expenses/amount)" />
			</td>
			<td>
				<xsl:choose>
					<xsl:when test="adjudicated != ''">
						<xsl:value-of select="number(adjudicated) + sum(expenses/amount)" />
					</xsl:when>
					<xsl:otherwise>
						<xsl:text name="adj">0</xsl:text>
					</xsl:otherwise>
				</xsl:choose>
			</td>
		</tr>
    </xsl:template>
</xsl:stylesheet>

