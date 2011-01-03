<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="../../base/report/corporate_defaults.xsl"/>

	<xsl:template match="/">
		<xsl:apply-templates select="report"/>
  	</xsl:template>

	<xsl:template match="/">
		<document filename="example_5.pdf">
		<template >
			<pageTemplate id="main">
				<frame id="mainbox" x1="2cm" y1="2cm" width="19cm" height="24cm"/>
				<pageGraphics>
					<xsl:apply-imports/>
				</pageGraphics>
			</pageTemplate>
		</template>


		<stylesheet>
			<paraStyle name="section" fontName="Helvetica-Bold" fontSize="16" spaceAfter="0.5cm" spaceBefore="1.5cm"/>
		</stylesheet>
		<story>
			<spacer length="2cm"/>
			<para t="1">Date printing: <xsl:value-of select="report/date"/></para>
			<para style="section" t="1">
				Auction
			</para>
			<xsl:apply-templates select="report/auction"/>
			<para style="section" t="1">
				Items
			</para>
			<xsl:apply-templates select="report/objects"/>
			<para style="section" t="1">
				Buyers
			</para>
			<xsl:apply-templates select="report/buyer"/>
			<para style="section" t="1">
				Sellers
			</para>
			<xsl:apply-templates select="report/seller"/>
		</story>
		</document>
	</xsl:template>

	<xsl:template match="report/buyer">
		<blockTable colWidths="4cm,14.9cm">
		<tr>
			<td t="1"># of buyers:</td>
			<td><xsl:value-of select="buy_nbr"/></td>
		</tr><tr>
			<td t="1"># of paid items:</td>
			<td><xsl:value-of select="paid_nbr"/></td>
		</tr><tr>
			<td t="1"># commissions:</td>
			<td><xsl:value-of select="comm_nbr"/></td>
		</tr><tr>
			<td t="1"># of items taken away:</td>
			<td><xsl:value-of select="taken_nbr"/></td>
		</tr><tr>
			<td t="1">Credit:</td>
			<td><xsl:value-of select="credit"/> EUR</td>
		</tr><tr>
			<td t="1">Paid:</td>
			<td><xsl:value-of select="paid"/> EUR</td>
		</tr>
		</blockTable>
	</xsl:template>

	<xsl:template match="report/auction">
		<blockTable colWidths="4cm,14.9cm">
		<tr>
			<td t="1">Auction:</td>
			<td><xsl:value-of select="title"/></td>
		</tr><tr>
			<td t="1">Date:</td>
			<td><xsl:value-of select="date"/></td>
		</tr>
		</blockTable>
	</xsl:template>

	<xsl:template match="/report/seller">
		<blockTable colWidths="4cm,14.9cm">
		<tr>
			<td t="1"># of sellers:</td>
			<td><xsl:value-of select="sell_nbr"/></td>
		</tr><tr>
			<td t="1">Debit:</td>
			<td><xsl:value-of select="debit"/> EUR</td>
		</tr>
		</blockTable>
	</xsl:template>

	<xsl:template match="/report/objects">
		<blockTable colWidths="4cm,14.9cm">
		<tr>
			<td t="1"># of items:</td>
			<td><xsl:value-of select="obj_nbr"/></td>
		</tr><tr>
			<td t="1">Min Estimate:</td>
			<td><xsl:value-of select="est_min"/></td>
		</tr><tr>
			<td t="1">Max Estimate:</td>
			<td><xsl:value-of select="est_max"/></td>
		</tr><tr>
			<td t="1"># of unsold items:</td>
			<td><xsl:value-of select="unsold"/></td>
		</tr><tr>
			<td t="1">Adjudication:</td>
			<td><xsl:value-of select="obj_price"/> EUR</td>
		</tr>
		</blockTable>
	</xsl:template>

</xsl:stylesheet>
