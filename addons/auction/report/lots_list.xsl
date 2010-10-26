<?xml version="1.0" encoding="utf-8"?>

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">
	<xsl:import href="corporate_defaults.xsl"/>
	<xsl:template match="/">
		<xsl:apply-templates select="lots"/>
	</xsl:template>

	<xsl:template match="/">
		<document xmlns:fo="http://www.w3.org/1999/XSL/Format">
			<template >
				<pageTemplate id="all">
					<frame id="list" x1="1.0cm" y1="0.0cm" width="19.0cm" height="24cm"/>
					<pageGraphics>
						<xsl:apply-imports/>
					</pageGraphics>
				</pageTemplate>
			</template>

			<stylesheet>
				<paraStyle name="small" fontName="Courier" fontSize="12" spaceBefore="0mm" spaceAfter="0mm"/>
				<paraStyle name="verysmall" fontSize="10" fontName="Courier" spaceBefore="0mm" spaceAfter="0mm"/>
				<paraStyle name="smallest" fontSize="8" fontName="Courier" spaceBefore="-1mm" spaceAfter="-1Mm"/>

				<blockTableStyle id="left">
					<blockValign value="TOP"/>
					<blockAlignment value="LEFT"/>
					<blockFont name="Helvetica-Bold" size="10"/>
					<blockTextColor colorName="black"/>
					<lineStyle kind="LINEABOVE" thickness="0.5" colorName="black" start="0,0" stop="-1,0"/>
					<lineStyle kind="LINEABOVE" thickness="0.5" colorName="black" start="0,0" stop="-1,0"/>
					<lineStyle kind="LINEBELOW" thickness="0.5" colorName="black"/>
					<lineStyle kind="LINEBEFORE" thickness="0.5" colorName="black" start="0,0" stop="-1,-1"/>
					<lineStyle kind="LINEBEFORE" thickness="0.5" colorName="black" start="0,0" stop="0,-1"/>
					<lineStyle kind="LINEAFTER" thickness="0.5" colorName="black" start="-1,0" stop="-1,-1"/>
					<blockBackground colorName="(1,1,1)" start="0,0" stop="-1,-1"/>
					<blockBackground colorName="(0.88,0.88,0.88)" start="0,0" stop="-1,0"/>
				</blockTableStyle>
			</stylesheet>

			<story>
				<blockTable repeatRows="1" style="left" colWidths="1.8cm,10.0cm,2.0cm,1.6cm,2.3cm,2cm">
					<tr>
						<td>
							<para style="small"><b t="1">Cat. N.</b></para>
						</td><td>
							<para style="small"><b t="1">Description and bids</b></para>
						</td><td>
							<para style="small"><b t="1">Est.</b></para>
						</td><td>
							<para style="small"><b t="1">Limit</b></para>
						</td><td>
							<para style="small"><b t="1">Inv, Name</b></para>
						</td><td>
							<para style="small"><b t="1">Buyer, Price</b></para>
						</td>
					</tr>
					<xsl:apply-templates select="lots/lot"/>
				</blockTable>
			</story>
		</document>
	</xsl:template>

	<xsl:template match="lots/lot">
		<tr>
			<td>
				<para style="verysmall"><xsl:value-of select="lot_num"/></para>
			</td><td>
				<para style="verysmall">
				    <b><xsl:value-of select="artist"/></b>
				</para>
				<para style="verysmall">
				    <xsl:value-of select="lot_desc"/>
				</para>
				<xsl:for-each select="bid">
					<xsl:sort order="descending" select="bid_prix"/>
					<para style="smallest">
						<xsl:choose>
							<xsl:when test="bid_tel_ok='1'">
								<b t="1">TEL:</b>
							</xsl:when>
							<xsl:otherwise t="1">
								BID:
							</xsl:otherwise>
						</xsl:choose>

						<xsl:value-of select="bid_name"/>
						<xsl:text>(</xsl:text><xsl:value-of select="bid_id"/><xsl:text>)</xsl:text>
						<xsl:if test="round(bid_prix)&gt;0">
							<xsl:text> </xsl:text><b><xsl:value-of select="round(bid_prix)"/><xsl:text> EUR</xsl:text></b>
						</xsl:if>
						<xsl:if test="bid_tel_ok='1'">
							<b><xsl:text t="1">, TEL:</xsl:text><xsl:value-of select="bid_tel"/></b>
						</xsl:if>
					</para>
				</xsl:for-each>
			</td><td>
				<para style="verysmall">
					<xsl:if test="lot_est1 != ''">
						<xsl:value-of select="round(lot_est1)"/>
					</xsl:if>
					<xsl:text>-</xsl:text>
					<xsl:if test="lot_est2 != ''">
						<xsl:value-of select="round(lot_est2)"/>
					</xsl:if>
				</para>
			</td><td>
				<xsl:if test="lot_limit != ''">
					<para style="verysmall">
						<b><xsl:value-of select="round(lot_limit)"/></b>
					</para>
				</xsl:if>
				<xsl:if test="lot_limit_net != ''">
					<para style="verysmall">
						<b t="1">NET</b>
					</para>
				</xsl:if>
			</td><td>
				<para style="verysmall"><xsl:value-of select="deposit_num"/>
					<xsl:text> </xsl:text><xsl:value-of select="substring(lot_seller_ref,0,5)"/>
					<xsl:text> </xsl:text><xsl:value-of select="substring(lot_seller,0,9)"/>
				</para>
			</td><td>
				<para style="verysmall">
					<xsl:value-of select="buyer_login"/>
					<xsl:if test="obj_price &gt; 0">
						<xsl:text>, </xsl:text>
						<xsl:value-of select="obj_price"/>
					</xsl:if>
				</para>
			</td>
		</tr>
	</xsl:template>
</xsl:stylesheet>
