<?xml version="1.0" encoding="utf-8"?>

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">
	<xsl:import href="../../base/report/corporate_defaults.xsl"/>
	<xsl:import href="../../base/report/rml_template.xsl"/>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template name="stylesheet">
		<paraStyle name="nospace" fontName="Courier" fontSize="9" spaceBefore="0" spaceAfter="0"/>
		<paraStyle name="nospace2" fontName="Courier" fontSize="10" spaceBefore="0" spaceAfter="0"/>
		<paraStyle name="bigspace" fontName="Courier" fontSize="10" spaceBefore="0" spaceAfter="20"/>

		<blockTableStyle id="bid">
			<blockValign value="TOP"/>
			<blockAlignment value="LEFT"/>
			<lineStyle kind="LINEABOVE" colorName="black" start="0,0" stop="-1,0"/>
			<lineStyle kind="LINEBELOW" colorName="black" start="0,0" stop="-1,0"/>
			<lineStyle kind="LINEBELOW" colorName="black" start="0,-1" stop="-1,-1"/>
			<lineStyle kind="LINEBEFORE" colorName="black" start="0,0" stop="-1,-1"/>
			<lineStyle kind="LINEBEFORE" colorName="black" start="0,0" stop="0,-1"/>
			<lineStyle kind="LINEAFTER" colorName="black" start="-1,0" stop="-1,-1"/>
			<blockBackground colorName="(0.85,0.85,0.85)" start="0,0" stop="-1,0"/>
		</blockTableStyle>
	</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="bids"/>
	</xsl:template>

	<xsl:template match="bids">
		<xsl:apply-templates select="bid"/>
		<pageBreak/>
	</xsl:template>

<!---	<xsl:template match="bid"> make a chaange a data of all the bidders-->
	<xsl:template match="/">
		<para style="nospace2"><xsl:value-of select="client_info/partner_name"/></para>
		<para style="nospace2"><xsl:value-of select="client_info/street"/></para>
		<para style="nospace2"><xsl:value-of select="client_info/street2"/></para>
		<para style="nospace2">
			<xsl:value-of select="client_info/zipcode"/><xsl:text> </xsl:text>
			<xsl:value-of select="client_info/city"/>
		</para>
		<nextFrame/>
		<setNextTemplate name="other_pages"/>
		<para style="nospace">
			<b><xsl:text t="1">Title: </xsl:text></b>
			<xsl:value-of select="bids_name"/>
		</para>
		<para style="nospace">
			<b><xsl:text t="1">Contact: </xsl:text></b>
			<xsl:value-of select="client_info/contact"/>
		</para>
		<para style="bigspace">
			<b><xsl:text t="1">Item: </xsl:text></b>
			<xsl:text t="1">BID, </xsl:text>
			<xsl:value-of select="auction"/>
		</para>
		<xsl:apply-templates select="bid_lines"/>
		<nextFrame/>
		<setNextTemplate name="first_page"/>
	</xsl:template>

	<xsl:template match="bid_lines">
		<blockTable repeatRows="1" style="bid" colWidths="2.0cm,12.5cm,2.0cm,1.5cm">
			<tr>
				<td>
					<para style="nospace"><b><xsl:text t="1">Cat. N.</xsl:text></b></para>
				</td>

				<td>
					<para style="nospace"><b><xsl:text t="1">Description</xsl:text></b></para>
				</td>

				<td>
					<para style="nospace"><b><xsl:text t="1">Price</xsl:text></b></para>
				</td>

				<td>
					<para style="nospace"><b><xsl:text t="1">Tel?</xsl:text></b></para>
				</td>
			</tr>
			<xsl:apply-templates select="bid_line"/>
		</blockTable>
	</xsl:template>

	<xsl:template match="bid_line">
		<tr>
			<td>
				<para style="nospace"><xsl:value-of select="lot_id"/></para>
			</td>

			<td>
				<para style="nospace"><xsl:value-of select="lot_desc"/></para>
			</td>

			<td>
				<para style="nospace"><xsl:value-of select="lot_price"/></para>
			</td>

			<td>
				<para style="nospace">
					<xsl:choose>
						<xsl:when test="call=1">
							<xsl:text t="1">yes</xsl:text>
						</xsl:when>
						<xsl:otherwise>
							<xsl:text t="1">no</xsl:text>
						</xsl:otherwise>
					</xsl:choose>
				</para>
			</td>
		</tr>
	</xsl:template>
</xsl:stylesheet>
