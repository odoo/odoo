<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">
	<xsl:import href="corporate_defaults.xsl"/>
	<xsl:template match="/">
		<xsl:apply-templates select="lots"/>
	</xsl:template>

	<xsl:template match="/">
		<document xmlns:fo="http://www.w3.org/1999/XSL/Format">
			<template>
				<pageTemplate id="all">
						<frame id="list" x1="1.0cm" y1="6.0cm" width="25.7cm" height="17cm"/>
						<pageGraphics>
								<xsl:apply-imports/>
						</pageGraphics>
				</pageTemplate>
			</template>

			<stylesheet>
				<paraStyle name="small" fontName="Courier" fontSize="12" spaceBefore="0mm" spaceAfter="0mm"/>
				<paraStyle name="verysmall" fontSize="11" fontName="Courier" spaceBefore="0mm" spaceAfter="0mm"/>
				<paraStyle name="smallest" fontSize="10" fontName="Courier" spaceBefore="-0.5mm" spaceAfter="-0.5mm"/>

				<blockTableStyle id="left">
					<blockValign value="TOP"/>
					<blockAlignment value="LEFT"/>
					<blockFont name="Helvetica-Bold" size="10"/>
					<blockTextColor colorName="black"/>
					<lineStyle kind="LINEABOVE" thickness="0.5" colorName="black" start="0,0" stop="-1,0"/>
					<lineStyle kind="LINEBELOW" thickness="0.5" colorName="black"/>
					<blockBackground colorName="(1,1,1)" start="0,0" stop="-1,-1"/>
					<blockBackground colorName="(0.88,0.88,0.88)" start="0,0" stop="-1,0"/>
				</blockTableStyle>
			</stylesheet>

			<story>
				<blockTable repeatRows="1" style="left" colWidths="1.8cm,11.0cm,2.3cm,10.5cm">
					<tr>
						<td>
							<para style="small"><b t="1">Cat. N.</b></para>
						</td><td>
							<para style="small"><b t="1">Description</b></para>
						</td><td>
							<para style="small"><b t="1">Est.</b></para>
						</td><td>
							<para style="small"><b t="1">Orders</b></para>
						</td>
					</tr>
					<xsl:apply-templates select="lots/lot[count(bid[tocall='1'])>0]"/>
				</blockTable>
			</story>
		</document>
	</xsl:template>

	<xsl:template match="lots/lot[count(bid[tocall='1'])>0]">
		<tr>
			<td>
				<para style="verysmall"><xsl:value-of select="number"/></para>
			</td><td>
				<para style="verysmall"><b><xsl:value-of select="artist"/></b></para>
				<para style="verysmall"><b><xsl:value-of select="title"/></b></para>
				<para style="verysmall"><xsl:value-of select="substring(desc,0,1024)"/></para>
			</td><td>
				<para style="verysmall">
					<xsl:if test="est1 != ''">
						<xsl:value-of select="round(est1)"/>
					</xsl:if>
					<xsl:text>-</xsl:text>
					<xsl:if test="est2 != ''">
						<xsl:value-of select="round(est2)"/>
					</xsl:if>
				</para>
			</td><td>
				<xsl:for-each select="lots/bid[tocall='1']">
					<xsl:sort order="descending" data-type="number" select="price"/>
					<para style="smallest">
						<xsl:value-of select="name"/>

						<xsl:text>(</xsl:text><xsl:value-of select="id"/><xsl:text>)</xsl:text>

						<xsl:if test="round(price)&gt;0">
							<xsl:text> </xsl:text><b><xsl:value-of select="round(price)"/><xsl:text> EUR</xsl:text></b>
						</xsl:if>

						<xsl:if test="tocall='1'">
							<xsl:text t="1">, TEL:</xsl:text><b><xsl:value-of select="contact"/></b>
						</xsl:if>
					</para>
				</xsl:for-each>
			</td>
		</tr>
	</xsl:template>
</xsl:stylesheet>