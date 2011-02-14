<?xml version="1.0" encoding="iso-8859-1"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format"  xmlns:date="http://exslt.org/dates-and-times" extension-element-prefixes="date">


<xsl:template match="report">
<document>

<template>
<!--	<pageTemplate id="first">-->
<!--		<pageGraphics>-->
<!--			<stroke color="(0.6,0.3,0.1)"/>-->
<!--			<fill color="(0.6,0.3,0.1)"/>-->

			<image x="7cm" y="25cm" file="addons/auction/report/images/aeko_logo.jpg"/>
			<image x="7cm" y="25cm" file="addons/auction/report/images/flagey_logo.jpg"/>
			<lines>1cm 3.0cm 20cm 3.0cm</lines>
			<setFont name="Helvetica" size="15"/>
			<drawCentredString x="105mm" y="2.2cm">Hotel des ventes Flagey</drawCentredString>
			<setFont name="Helvetica" size="11"/>
			<drawCentredString x="105mm" y="1.6cm">Rue du Nid, 4 - B-1050 Bruxelles - Tel: 02/644.97.67</drawCentredString>
			<drawCentredString x="105mm" y="1.0cm">Web: Flagey.com - Mail: info@flagey.com - Fax: 02.646.32.35</drawCentredString>

			<fill color="(0.2,0.2,0.2)"/>
			<stroke color="(0.2,0.2,0.2)"/>

<!--		</pageGraphics>-->
<!--		<frame id="column" x1="2.0cm" y1="6cm" width="18cm" height="18cm"/>-->
<!--	</pageTemplate>-->
	<pageTemplate id="first">
		<pageGraphics>
<!--			<image x="1.0cm" y="27.3cm" file="/home/tiny/terp/4.2/server/bin/addons/auction/report/images/flagey_head.png"/>-->
-			<image x="1.0cm" y="26.1cm" file="flagey_logo.jpg"/>
			<drawRightString x="19.0cm" y="26.6cm"> Antiques on sale  <xsl:value-of select="date:day-name(catalog/AuctionDate1)"/> <xsl:value-of select="date:day-in-month(catalog/AuctionDate1)"/><xsl:value-of select="date:month-name(catalog/AuctionDate1)"/> <xsl:value-of select="date:year(catalog/AuctionDate1)"/></drawRightString>
			<lineMode width="1mm"/>
			<setFont name="Helvetica" size="26"/>
<!--			<drawString x="10mm" y="27.8cm">Flagey.com</drawString>-->
			<fill color="(0.2,0.2,0.2)"/>
			<stroke color="#2b24b6"/>
			<lineMode width="0.5mm"/>
			<lines>1cm 1.6cm 20cm 1.6cm</lines>
			<lines>1.0cm 26.1cm 20cm 26.1cm</lines>

			<setFont name="Helvetica" size="12"/>
			<drawString x="10mm" y="1.0cm">www.flagey.com</drawString>
			<drawCentredString x="105mm" y="1.0cm">Tel: 02.644.97.67 - Fax: 02.646.32.35</drawCentredString>
			<drawRightString x="200mm" y="1.0cm">info@flagey.com</drawRightString>
		</pageGraphics>
		<frame id="column" x1="1cm" y1="1.5cm" width="9.4cm" height="25.5cm"/>
		<frame id="column" x1="14.8cm" y1="1.5cm" width="9.4cm" height="25.5cm"/>
	</pageTemplate>
</template>
<stylesheet>
        <paraStyle name="slogan1" fontName="Helvetica-Bold" fontSize="11" alignment="left" spaceBefore="0.0" spaceAfter="0.0"/>
         <paraStyle name="slogan2" fontName="Times-Roman" fontSize="9" alignment="right" spaceBefore="0.0" spaceAfter="0.0"/>
         <paraStyle name="slogan5"  alignment="right" />
		<paraStyle name="slogan" fontName="Times New Roman-Italic" fontSize="11" alignment="left" spaceBefore="0.0" spaceAfter="0.0"/>
         <paraStyle name="slogan3"  xml:lang="en-fr" fontName="Times-Roman" fontSize="16" alignment="center" spaceAfter="0.5" />
          <paraStyle name="slogan4" fontName="Helvetica" fontSize="10" alignment="right" spaceBefore="0.0"/>
        <paraStyle name="footnote" fontName="Helvetica" fontSize="10" alignment="center" />
        <paraStyle name="note" fontName="Helvetica" fontSize="8" leftIndent="3mm"/>
        <paraStyle name="homehead" fontName="Helvetica" fontSize="12" alignment="center"/>
        <paraStyle name="artist" fontName="Helvetica-Bold"/>
        <paraStyle name="prodtitle" fontName="Helvetica-BoldOblique" fontSize="8"/>
         <paraStyle name="P2" rightIndent="13.0" leftIndent="11.0" fontName="Times-Roman" alignment="RIGHT"/>
        <blockTableStyle id="infos">
                <blockValign value="TOP"/>
                <blockTopPadding value="0"/>
                <blockBottomPadding value="0"/>
        </blockTableStyle>
        <blockTableStyle id="imagestyle">

         <blockHalign value="right"/>
     	<blockAlignment value="RIGHT" start="-1,0" stop="-1,-1"/>


        </blockTableStyle>

        <blockTableStyle id="product1">
                <blockValign value="TOP"/>
<!--              <blockAlignment value="RIGHT" start="1,0" stop="-1,0"/>-->
				 <blockAlignment value="RIGHT"/>

                <blockTopPadding legnth="0"  start="0,0" stop="0,-1" />
                <blockLeftPadding legnth="0"  start="0,0" stop="0,-1" />


		<blockAlignment value="CENTER" start="0,0" stop="0,-1"/>
        </blockTableStyle>
        <blockTableStyle id="donation">
                <blockFont name="Helvetica-BoldOblique" size="24" start="0,0" stop="-1,0"/>
                <blockAlignment value="RIGHT" start="-1,0" stop="-1,-1"/>
                <lineStyle kind="LINEBELOW" start="0,0" stop="-1,0"/>
        </blockTableStyle>
</stylesheet>
<images>
    <image name="flagey_logo.jpg">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
</image>
  </images>
	<story>
  <para style="P2">
      <font color="white"> </font>
    </para>
<!--<setNextTemplate name="others"/>-->
<!--	<pageBreak/>-->
<spacer length="0.8cm"/>
	<xsl:apply-templates select="catalog/products"/>
</story>
</document>
</xsl:template>


<xsl:template match="products">
			<xsl:apply-templates select="product">
				<xsl:sort order="ascending" data-type="number" select="infos/lot_num"/>
			</xsl:apply-templates>

</xsl:template>

<xsl:template match="product">
<!--        <xsl:if test="newpage">-->
<!--                <condPageBreak height="20cm"/>-->
<!--        </xsl:if>-->

<xsl:choose>
<xsl:when test="string-length(infos/photo) &gt;2  or string-length(infos/photo_small) &gt;2 ">

            <blockTable style="product1" colWidths="6.5cm,2.5cm" >

                 <tr>
                     <td>
                       <para style="slogan1">
	                  <xpre><xsl:value-of select="infos/lot_num"/> &#160;- &#160;<xsl:value-of select="infos/info"/>
						</xpre></para>
						  <spacer length="2.0mm"/>
		     			   <xsl:if test="lot_est1&gt;0">
				           <para style="slogan2">
				           <xpre>
				             Est. <xsl:value-of select="format-number(lot_est1, '#,##0.00')"/>/&#160;<xsl:value-of select="format-number(lot_est2, '#,##0.00')"/> Euro</xpre></para>
				       </xsl:if>
					</td>
						<td>

							<xsl:if test="infos/photo_small" >

									<image x="0" y="0" height="2.5cm" width="2cm" >

									<xsl:value-of select="infos/photo_small"/>

									</image>

							</xsl:if>
				   </td>
		    </tr>
  </blockTable>
</xsl:when>
<xsl:otherwise>
			<!-- photo on the right-->

       <blockTable style="product1" colWidths="9cm">
		       <tr>
		                     <td>
		                       <para style="slogan1">
		                       <xpre>
			                  <xsl:value-of select="infos/lot_num"/>&#160;- &#160; <xsl:value-of select="infos/info"/>
								</xpre></para>
								  <spacer length="2.0mm"/>
				     			   <xsl:if test="lot_est1&gt;0">
						           <para style="slogan2">
						           <xpre>
						            Est. <xsl:value-of select="format-number(lot_est1, '#,##0.00')"/>/&#160;<xsl:value-of select="format-number(lot_est2, '#,##0.00')"/> Euro

						           </xpre>
						            </para>
						       </xsl:if>
							</td>

				  </tr>
  </blockTable>
</xsl:otherwise>
</xsl:choose>

</xsl:template>


</xsl:stylesheet>
