<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fo="http://www.w3.org/1999/XSL/Format">
   <xsl:import href="../../base/report/corporate_defaults.xsl" />
    <xsl:template match="/">
		<xsl:call-template name="rml" />
    </xsl:template>


    <xsl:template name="rml" match="/">
		<document filename="example.pdf">
			<template>
				<pageTemplate id="first">
					<frame id="first" x1="1cm" y1="2.5cm" width="19.0cm" height="23.0cm"/>
					<pageGraphics>
						<xsl:apply-imports />
					</pageGraphics>
				</pageTemplate>
			</template>
			<stylesheet>
				<paraStyle name="normal" fontName="Times-Roman" fontSize="12"  />
				<paraStyle name="title" fontName="Times-Bold" fontSize="15" alignment="center" />
				<paraStyle name="table_title" fontName="Times-Bold" fontSize="12" alignment="center" />
				<paraStyle name="product1" fontName="Times-Roman" fontSize="8" />
				<paraStyle name="categ" fontName="Times-Bold" fontSize="10"  textColor="blue"/>
				<paraStyle name="price" fontName="Times-Roman" fontSize="8" alignment="right" />

				<blockTableStyle id="main_title">
					<blockAlignment value="CENTER" />
					<lineStyle kind="GRID" colorName="black"/>
					<blockBackground colorName="#e6e6e6" />
					<blockValign value="TOP"/>
				</blockTableStyle>

				<blockTableStyle id="product">
					<blockAlignment value="LEFT" />
					<xsl:for-each select="/report/title">
						<xsl:variable name="col" select="attribute::number" />
						<blockBackground>
							<xsl:attribute name="colorName">#e6e6e6</xsl:attribute>
							<xsl:attribute name="start">
								<xsl:value-of select="$col" />
								<xsl:text>,0</xsl:text>
							</xsl:attribute>
							<xsl:attribute name="stop">
								<xsl:value-of select="$col" />
								<xsl:text>,0</xsl:text>
							</xsl:attribute>
						</blockBackground>
					</xsl:for-each>
					<lineStyle kind="LINEABOVE" colorName="black" start="0,0" stop="-1,-1" />
					<lineStyle kind="LINEBEFORE" colorName="black" start="0,0" stop="-1,-1"/>
					<lineStyle kind="LINEAFTER" colorName="black" start="-1,0" stop="-1,-1"/>
					<lineStyle kind="LINEBELOW" colorName="black" start="0,-1" stop="-1,-1"/>
					<blockValign value="TOP"/>
				</blockTableStyle>
			</stylesheet >
			<story>
				<xsl:call-template name="story"/>
			</story>
		</document>
    </xsl:template>

    <xsl:template name="story">
 		<spacer length="1cm" />
  		<blockTable   rowHeights="1cm">
			<xsl:attribute name="style">main_title</xsl:attribute>
			<tr> <td> <para style="title" t="1">Products Price List</para> </td> </tr>
		</blockTable>
 		<spacer length="1cm" />
		<para style="normal" t="1">Price List Name :<xsl:value-of select="report/pricelist" /></para>
		<para style="normal" t="1">Currency : <xsl:value-of select="report/currency" /></para>
		<para style="normal" t="1">Printing Date : <xsl:value-of select="report/date" /></para>
 		<spacer length="0.7cm" />
		<blockTable>
			<xsl:attribute name="style">product</xsl:attribute>
			<xsl:attribute name="colWidths"><xsl:value-of select="report/cols" /></xsl:attribute>
			<tr>
				<xsl:for-each select="report/title" >
    	        	<td><para style="table_title"> <xsl:value-of select="attribute::name" /> </para></td>
        	    </xsl:for-each>
            </tr>

			<xsl:for-each select="report/product/pro" >
	        <tr>
	            <xsl:choose>
					<xsl:when test="@categ">
						<td> <para style="categ"><xsl:value-of select="attribute::name" /> </para> </td>
					</xsl:when>
					<xsl:otherwise>
			            <td> <para style="product1">   <xsl:value-of select="attribute::name" /> </para> </td>

			        </xsl:otherwise>
				</xsl:choose>
	            <xsl:for-each select="price" >
            		<td><para style="price"> <xsl:value-of select="attribute::name" /> </para> </td>
            	</xsl:for-each>
	        </tr>
		</xsl:for-each>
    	</blockTable>
 </xsl:template>

</xsl:stylesheet>
