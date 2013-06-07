<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet
  version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:fo="http://www.w3.org/1999/XSL/Format"
  xmlns:office="http://openoffice.org/2000/office"
  xmlns:style="http://openoffice.org/2000/style"
  xmlns:text="http://openoffice.org/2000/text"
  xmlns:table="http://openoffice.org/2000/table"
  xmlns:draw="http://openoffice.org/2000/drawing"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:number="http://openoffice.org/2000/datastyle"
  xmlns:svg="http://www.w3.org/2000/svg"
  xmlns:chart="http://openoffice.org/2000/chart"
  xmlns:dr3d="http://openoffice.org/2000/dr3d"
  xmlns:math="http://www.w3.org/1998/Math/MathML"
  xmlns:form="http://openoffice.org/2000/form"
  xmlns:script="http://openoffice.org/2000/script"
  office:class="text" office:version="1.0"
  exclude-result-prefixes = "xsl fo office style text table draw xlink number svg chart dr3d math form script">

  <!--TODO's: indent, picture cache (trml2pdf) -->

<xsl:output method="xml" indent="yes" />
<xsl:strip-space elements="*"/>

<xsl:key name="text_style" match="style:style[@style:family='text']" use="@style:name" />
<xsl:key name="page_break_before" match="style:style[@style:family='paragraph' and ./style:properties/@fo:break-before='page']" use="@style:name" />
<xsl:key name="page_break_after" match="style:style[@style:family='paragraph' and ./style:properties/@fo:break-after='page']" use="@style:name" />
<xsl:key name="table_column_style" match="style:style[@style:family='table-column']" use="@style:name" />
<xsl:key name="table_cell_style" match="style:style[@style:family='table-cell']" use="@style:name" />
<xsl:key name="paragraph_style" match="style:style[@style:family='paragraph']" use="@style:name" />

<xsl:template match="office:document-content">
  <document filename="test.pdf">
    <xsl:apply-templates select="office:automatic-styles" />
    <xsl:apply-templates select="office:body" />
  </document>
</xsl:template>

<xsl:template name="page_size">
  <xsl:attribute name="pageSize">
    <xsl:text>(</xsl:text>
    <xsl:value-of select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:page-width" />
    <xsl:text>,</xsl:text>
    <xsl:value-of select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:page-height" />
    <xsl:text>)</xsl:text>
  </xsl:attribute>
</xsl:template>

<xsl:template name="fixed_frame">
	<xsl:for-each select="//draw:text-box">
		<frame>
			<xsl:attribute name="id"><xsl:value-of select="./@draw:name" /></xsl:attribute>
			<xsl:attribute name="x1"><xsl:value-of select="./@svg:x" /></xsl:attribute>
			<xsl:attribute name="y1">
				<xsl:value-of
					select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:page-height - ./@svg:y - ./@fo:min-height" />
			</xsl:attribute>
			<xsl:attribute name="width">
				<xsl:value-of select="./@svg:width" />
			</xsl:attribute>
			<xsl:attribute name="height">
				<xsl:value-of select="./@fo:min-height" />
			</xsl:attribute>
		</frame>
	</xsl:for-each>
</xsl:template>

<xsl:template name="margin_sizes">
  <xsl:variable name="margin_left" select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:margin-left" />
  <xsl:variable name="margin_right" select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:margin-right" />
  <xsl:variable name="margin_top" select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:margin-top" />
  <xsl:variable name="margin_bottom" select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:margin-bottom" />
  <xsl:variable name="page_width" select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:page-width" />
  <xsl:variable name="page_height" select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:page-height" />
  <xsl:attribute name="x1"><xsl:value-of select="$margin_left" /></xsl:attribute>
  <xsl:attribute name="y1"><xsl:value-of select="$margin_bottom" /></xsl:attribute>
  <xsl:attribute name="width"><xsl:value-of select="$page_width - $margin_left - $margin_right"/></xsl:attribute>
  <xsl:attribute name="height"><xsl:value-of select="$page_height - $margin_bottom - $margin_top"/></xsl:attribute>
</xsl:template>

<xsl:template name="text_width">
  <!-- You need this for the workaround to make primitive outlines-->
  <xsl:variable name="margin_left" select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:margin-left" />
  <xsl:variable name="margin_right" select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:margin-right" />
  <xsl:variable name="page_width" select="//transferredfromstylesxml/style:page-master[1]/style:properties/@fo:page-width" />
  <xsl:value-of select="$page_width - $margin_left - $margin_right - 18"/>
</xsl:template>



<xsl:template match="office:automatic-styles">
  <!--<template pageSize="(21cm, 29.7cm)" leftMargin="1.0cm" rightMargin="2.0cm" topMargin="1.0cm" bottomMargin="1.0cm" title="Test" author="Martin Simon" allowSplitting="20">-->
  <template pageSize="(21cm, 29.7cm)" title="Test" author="Martin Simon" allowSplitting="20">
    <xsl:call-template name="page_size" />
    <pageTemplate id="first">
	  <xsl:call-template name="fixed_frame" />
      <frame id="first" x1="2cm" y1="2cm" width="17cm" height="26cm">
        <xsl:call-template name="margin_sizes" />
      </frame>
    </pageTemplate>
  </template>
  <stylesheet>
    <!--A table style to simulate primitive outlines -till the <addOutline> tag is implemented in trml2pdf -->
    <blockTableStyle id="Standard_Outline">
      <blockAlignment value="LEFT"/>
      <blockValign value="TOP"/>
    </blockTableStyle>
    <!--use two standard table grid styles like PyOpenOffice "Old Way": with and without a grid-->
    <!--TODO insert table cell colors here, not within the <td> tag - otherwise
         it will not work with flowables as cell content-->
    <xsl:call-template name="make_blocktablestyle" />
    <initialize>
      <paraStyle name="all" alignment="justify" />
    </initialize>
    <xsl:apply-templates select="style:style" />
  </stylesheet>
</xsl:template>

<xsl:template name="make_blocktablestyle">
  <xsl:for-each select="//table:table">
    <xsl:variable name="test">
      <xsl:value-of select="./@table:name" />
    </xsl:variable>
    <xsl:if test="not(boolean(count(preceding-sibling::table:table[@table:name=$test])))">
      <!--Test if this is the first table with this style, nested tables not counted-->
      <blockTableStyle id="{@table:name}">
	    <xsl:if test=".//draw:image">
	      <blockTopPadding value="0"/>
	      <blockBottomPadding value="0"/>
	    </xsl:if>
        <blockAlignment value="LEFT" />
        <blockValign value="TOP" />
        <xsl:call-template name="make_linestyle" />
        <xsl:call-template name="make_tablebackground" />
      </blockTableStyle>
    </xsl:if>
  </xsl:for-each>
</xsl:template>

<xsl:template name="make_linestyle">
	<xsl:for-each select=".//table:table-row">
		<xsl:variable name="row" select="position() - 1"/>
		<xsl:for-each select=".//table:table-cell">
			<xsl:variable name="col" select="position() - 1"/>
			<xsl:variable name="linebefore">
				<xsl:value-of select="key('table_cell_style',@table:style-name)/style:properties/@fo:border-left"/>
			</xsl:variable>
			<xsl:if test="not($linebefore='') and not($linebefore='none')">
				<xsl:variable name="colorname">
					<xsl:value-of select="substring-after($linebefore,'#')"/>
				</xsl:variable>
				<lineStyle kind="LINEBEFORE" colorName="#{$colorname}" start="{$col},{$row}" stop="{$col},-1"/>
			</xsl:if>
			<xsl:variable name="lineafter">
				<xsl:value-of select="key('table_cell_style',@table:style-name)/style:properties/@fo:border-right"/>
			</xsl:variable>
			<xsl:if test="not($lineafter='') and not($lineafter='none')">
				<xsl:variable name="colorname">
					<xsl:value-of select="substring-after($lineafter,'#')"/>
				</xsl:variable>
				<lineStyle kind="LINEAFTER" colorName="#{$colorname}" start="{$col},{$row}" stop="{$col},-1"/>
			</xsl:if>
			<xsl:variable name="lineabove">
				<xsl:value-of select="key('table_cell_style',@table:style-name)/style:properties/@fo:border-top"/>
			</xsl:variable>
			<xsl:if test="not($lineabove='') and not($lineabove='none')">
				<xsl:variable name="colorname">
					<xsl:value-of select="substring-after($lineabove,'#')"/>
				</xsl:variable>
				<lineStyle kind="LINEABOVE" colorName="#{$colorname}" start="{$col},{$row}" stop="{$col},{$row}"/>
			</xsl:if>
			<xsl:variable name="linebelow">
				<xsl:value-of select="key('table_cell_style',@table:style-name)/style:properties/@fo:border-bottom"/>
			</xsl:variable>
			<xsl:if test="not($linebelow='') and not($linebelow='none')">
				<xsl:variable name="colorname">
					<xsl:value-of select="substring-after($linebelow,'#')"/>
				</xsl:variable>
				<lineStyle kind="LINEBELOW" colorName="#{$colorname}" start="{$col},{-1}" stop="{$col},{-1}"/>
			</xsl:if>
			<xsl:variable name="grid">
				<xsl:value-of select="key('table_cell_style',@table:style-name)/style:properties/@fo:border"/>
			</xsl:variable>
			<xsl:if test="not($grid='') and not($grid='none')">
				<xsl:variable name="colorname">
					<xsl:value-of select="substring-after($grid,'#')"/>
				</xsl:variable>
				<!-- Don't use grid because we don't need a line between each rows -->
				<lineStyle kind="LINEBEFORE" colorName="#{$colorname}" start="{$col},{$row}" stop="{$col},-1"/>
				<lineStyle kind="LINEAFTER" colorName="#{$colorname}" start="{$col},{$row}" stop="{$col},-1"/>
				<lineStyle kind="LINEABOVE" colorName="#{$colorname}" start="{$col},{$row}" stop="{$col},{$row}"/>
				<lineStyle kind="LINEBELOW" colorName="#{$colorname}" start="{$col},{-1}" stop="{$col},{-1}"/>
			</xsl:if>
		</xsl:for-each>
	</xsl:for-each>
</xsl:template>

<!-- Was needed to simulate bulleted lists:
<xsl:template match="text:ordered-list|text:unordered-list">
  <xsl:variable name = "text_width">
    <xsl:call-template name="text_width" />
  </xsl:variable>
  <blockTable style="Standard_Outline" colWidths="18,{$text_width}">
  <xsl:apply-templates match="text:list-item" />
</blockTable>
</xsl:template>

<xsl:template match="text:list-item">
  <tr>
    <td><para><font face="Helvetica-Bold" size="10">*</font></para></td>
    <td>
      <xsl:apply-templates />
    </td>
  </tr>
</xsl:template>

-->


<xsl:template match="office:body">
  <story>
    <xsl:apply-templates />
	<xsl:for-each select="//draw:text-box">
		<currentFrame>
			<xsl:attribute name="name">
				<xsl:value-of select="./@draw:name" />
			</xsl:attribute>
		</currentFrame>
		<xsl:apply-templates>
			<xsl:with-param name="skip_draw" select="0" />
		</xsl:apply-templates>
		<frameEnd />
	</xsl:for-each>
	<xsl:for-each select="//text:ordered-list">
		<para><seqReset id="{./@text:style-name}"/></para>
	</xsl:for-each>
  </story>
</xsl:template>

<xsl:template match="table:table">
  <blockTable>
    <xsl:attribute name="colWidths">
      <xsl:call-template name="make_columns" />
    </xsl:attribute>
    <xsl:call-template name="make_tableheaders" />
    <xsl:attribute name="style">
      <xsl:value-of select="@table:name" />
    </xsl:attribute>
    <xsl:apply-templates />
  </blockTable>
</xsl:template>

<xsl:template name="make_tableheaders">
  <xsl:if test="boolean(count(table:table-header-rows))">
    <xsl:attribute name="repeatRows">1</xsl:attribute>
  </xsl:if>
</xsl:template>

<xsl:template name="make_tablebackground">
  <xsl:for-each select=".//table:table-row">
    <!--Be careful when there are table:table-header-rows as
         parent node of table:table-row -->
    <xsl:variable name="row" select="position() - 1" />
    <xsl:for-each select="./table:table-cell">
      <xsl:variable name="col" select="position() - 1" />
      <xsl:variable name="background">
        <xsl:value-of select="key('table_cell_style',@table:style-name)/style:properties/@fo:background-color" />
      </xsl:variable>
      <xsl:if test="not($background='') and boolean(key('table_cell_style',@table:style-name)/style:properties/@fo:background-color) and starts-with($background,'#')">
        <!--only RGB hexcolors are accepted -->
		<blockBackground colorName="{$background}" start="{$col},{$row}" stop="{$col},-1" />
      </xsl:if>
     </xsl:for-each>
   </xsl:for-each>
</xsl:template>

<xsl:template name="make_columns">
  <xsl:variable name="columns" >
    <xsl:for-each select="table:table-column">
      <xsl:value-of select="key('table_column_style',@table:style-name)/style:properties/@style:column-width" />
      <xsl:text>,</xsl:text>
    </xsl:for-each>
  </xsl:variable>
  <xsl:value-of select="substring($columns,1,string-length($columns) - 1)" />
  <!--strip the last comma-->
</xsl:template>

<xsl:template match="table:table-row">
  <tr>
    <xsl:apply-templates />
  </tr>
</xsl:template>

<xsl:template match="table:table-cell">
  <td>
    <xsl:apply-templates />
  </td>
</xsl:template>

<xsl:template match="text:section">
  <section>
    <xsl:apply-templates />
  </section>
</xsl:template>


<xsl:template match="text:span">
  <font>
    <xsl:call-template name="make_fontnames_span" />
    <xsl:call-template name="make_fontsize_span" />
    <xsl:apply-templates />
  </font>
</xsl:template>

<xsl:template name="make_fontsize_span">
  <xsl:variable name ="fontsize">
    <xsl:value-of select="key('text_style',@text:style-name)/style:properties/@fo:font-size" />
  </xsl:variable>
  <xsl:if test="not($fontsize='') and boolean(key('text_style',@text:style-name)/style:properties/@fo:font-size)" >
    <xsl:attribute name="size">
      <xsl:value-of select="$fontsize" />
    </xsl:attribute>
  </xsl:if>
</xsl:template>

<xsl:template name="make_fontnames_span">
  <xsl:attribute name="face">
    <xsl:call-template name="make_fontnames">
      <xsl:with-param name="fontName" select="key('text_style',@text:style-name)/style:properties/@style:font-name"  />
      <xsl:with-param name="fontWeight" select="key('text_style',@text:style-name)/style:properties/@fo:font-weight"  />
      <xsl:with-param name="fontStyle" select="key('text_style',@text:style-name)/style:properties/@fo:font-style" />
    </xsl:call-template>
  </xsl:attribute>
</xsl:template>

<xsl:template name="make_image">
  <illustration height="{.//draw:image/@svg:height}" width="{.//draw:image/@svg:width}">
    <image x="0" y="0" file="{substring-after(.//draw:image/@xlink:href,'#Pictures/')}" height="{.//draw:image/@svg:height}" width="{.//draw:image/@svg:width}" />
  </illustration>
</xsl:template>

<xsl:template name="empty_paragraph">
  <xsl:if test="not(boolean(count(descendant::node())))">
    <xsl:call-template name="distance_point">
      <xsl:with-param name="background" select="key('paragraph_style',@text:style-name)/style:properties/@fo:background-color" />
    </xsl:call-template>
  </xsl:if>
</xsl:template>

<xsl:template name="distance_point">
  <xsl:param name="background" />
  <xsl:param name="tab_stop"></xsl:param>
  <xsl:variable name="local_back">
    <xsl:choose>
      <xsl:when test="not(boolean($background)) or not(contains($background,'#'))">
        <!-- Do not accept OO colors like "transparent", only hex-colors -->
        <xsl:text>white</xsl:text>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="$background" />
      </xsl:otherwise>
    </xsl:choose>
  </xsl:variable>
  <font color="{$local_back}">
    <xsl:text> </xsl:text>
    <xsl:if test="boolean($tab_stop)">
      <!-- simulate a tabstop with white/background-color points -->
      <xsl:text>.........</xsl:text>
    </xsl:if>
  </font>
</xsl:template>

<xsl:template match="text:ordered-list">
  <xsl:apply-templates />

  <!-- Reset the counter. seqreset is not a trml2pdf tag, but a Platypus Intra Paragraph Markup,
       so it needs a dummy paragraph to enclose it -->
</xsl:template>

<xsl:template name="make_listitem">
  <xsl:if test="(name(..)='text:list-item')">
    <xsl:attribute name="leftIndent">15</xsl:attribute>
    <xsl:attribute name="bulletIndent">0</xsl:attribute>
    <xsl:choose>
      <xsl:when test="(name(../..)='text:unordered-list')">
        <xsl:variable name="fontsize">
          <xsl:value-of select="number(key('paragraph_style',@text:style-name)/style:properties/@fo:font-size)" />
        </xsl:variable>
        <xsl:choose>
          <xsl:when test="$fontsize='NaN'">
            <!-- you should exclude non-numerical values for bulletFontSize. <== Sometimes the preprocessing went wrong.-->
            <!--use a default bullet font size-->
            <xsl:attribute name="bulletFontSize">6</xsl:attribute>
          </xsl:when>
          <xsl:otherwise>
            <xsl:attribute name="bulletFontSize"><xsl:value-of select="floor(($fontsize div 2) + 1)" /></xsl:attribute>
          </xsl:otherwise>
        </xsl:choose>
        <xsl:attribute name="bulletFontName">ZapfDingbats</xsl:attribute>
        <xsl:attribute name="bulletText">l</xsl:attribute>
      </xsl:when>
      <xsl:otherwise>
        <!-- Generate the numbers for an ordered list -->
        <xsl:variable name="size">
          <xsl:value-of select="key('paragraph_style',@text:style-name)/style:properties/@fo:font-size" />
        </xsl:variable>
        <!-- For ordered lists we use the bullet tag from Platypus Intra Paragraph Markup -->
        <bullet>
          <xsl:if test="not($size='') and boolean(key('paragraph_style',@text:style-name)/style:properties/@fo:font-size)">
            <xsl:attribute name="size">
              <!-- adapt the fontsize to the fontsize of the current paragraph -->
              <xsl:value-of select="$size" />
            </xsl:attribute>
          </xsl:if>
          <seq id="{../../@text:style-name}"/></bullet>

      </xsl:otherwise>
    </xsl:choose>
  </xsl:if>
</xsl:template>

<xsl:template match="text:drop-down">
    <xsl:value-of select="text:label[2]/@text:value" />
</xsl:template>


<xsl:template match="text:p|text:h">
	<xsl:param name="skip_draw" select="1" />
  <xsl:if test="boolean(key('page_break_before',@text:style-name))" >
    <pageBreak />
  </xsl:if>
  <xsl:choose>
    <xsl:when test="boolean(.//draw:image)">
      <xsl:call-template name="make_image" />
    </xsl:when>
	<xsl:when test="boolean(name(..) = 'draw:text-box') and boolean($skip_draw)">
	</xsl:when>
    <xsl:otherwise>
      <para>
        <xsl:attribute name="style">
          <xsl:value-of select="@text:style-name" />
        </xsl:attribute>
        <xsl:call-template name="make_listitem" />
        <xsl:apply-templates />
        <xsl:call-template name="empty_paragraph" />
      </para>
    </xsl:otherwise>
  </xsl:choose>
  <xsl:if test="boolean(key('page_break_after',@text:style-name))" >
    <pageBreak />
  </xsl:if>
</xsl:template>

<xsl:template match="text:p/text:tab-stop">
  <!-- simulate a tabstop -->
  <xsl:call-template name="distance_point">
    <xsl:with-param name="background" select="key('paragraph_style',@text:style-name)/style:properties/@fo:background-color" />
    <xsl:with-param name="tab_stop">yes</xsl:with-param>
  </xsl:call-template>
</xsl:template>

<!-- experimental - switched off
<xsl:template match="text:h">
  <para>
    <xsl:attribute name="style">
      <xsl:value-of select="@text:style-name" />
    </xsl:attribute>
    <xsl:call-template name="make_number" />
    <xsl:apply-templates />
    <xsl:call-template name="empty_paragraph" />
  </para>
</xsl:template>

<xsl:template name="make_number">
  <xsl:choose>
    <xsl:when test="@text:level='1'">
      <xsl:number format="1. " />
    </xsl:when>
    <xsl:when test="@text:level='2'">
      <xsl:number count="text:h[@text:level='1']|text:h[text:level='2']" level="any" format="1.1." />
    </xsl:when>
  </xsl:choose>
</xsl:template>

-->

<xsl:template match="style:style[@style:family='paragraph']">
  <paraStyle>
    <xsl:attribute name="name">
      <xsl:value-of select="@style:name" />
    </xsl:attribute>
    <xsl:call-template name="make_indent_paragraph" />
    <xsl:call-template name="make_fontnames_paragraph" />
    <xsl:call-template name="make_fontsize" />
    <!--<xsl:call-template name="make_parent" /> not necessary -
         parent styles processed by PyOpenOffice -->
    <xsl:call-template name="make_alignment" />
    <xsl:call-template name="make_background" />
    <xsl:call-template name="make_space_beforeafter" />
    <xsl:call-template name="make_fontcolor" />
  </paraStyle>
</xsl:template>

<xsl:template name="make_indent_paragraph">
  <xsl:variable name="right_indent"><xsl:value-of select="style:properties/@fo:margin-right" /></xsl:variable>
  <xsl:variable name="left_indent"><xsl:value-of select="style:properties/@fo:margin-left" /></xsl:variable>
  <xsl:if test="not($right_indent='') and boolean(style:properties/@fo:margin-right)">
    <xsl:attribute name="rightIndent">
      <xsl:value-of select="$right_indent" />
    </xsl:attribute>
  </xsl:if>
  <xsl:if test="not($left_indent='') and boolean(style:properties/@fo:margin-left)">
    <xsl:attribute name="leftIndent">
      <xsl:value-of select="$left_indent" />
    </xsl:attribute>
  </xsl:if>
</xsl:template>

<xsl:template name="make_background">
  <xsl:variable name="background">
    <xsl:value-of select="style:properties/@fo:background-color" />
  </xsl:variable>
  <xsl:if test="not($background='') and boolean(style:properties/@fo:background-color) and starts-with($background,'#')" >
    <xsl:attribute name="backColor">
      <xsl:value-of select="$background" />
    </xsl:attribute>
  </xsl:if>
</xsl:template>

<xsl:template name="make_space_beforeafter">
  <xsl:variable name="before">
    <xsl:value-of select="style:properties/@fo:margin-top" />
  </xsl:variable>
  <xsl:variable name="after">
    <xsl:value-of select="style:properties/@fo:margin-bottom" />
  </xsl:variable>
  <xsl:if test="not($before='') and boolean(style:properties/@fo:margin-top)" >
    <xsl:attribute name="spaceBefore">
      <xsl:value-of select="$before" />
    </xsl:attribute>
  </xsl:if>
  <xsl:if test="not($after='') and boolean(style:properties/@fo:margin-bottom)" >
    <xsl:attribute name="spaceAfter">
      <xsl:value-of select="$after" />
    </xsl:attribute>
  </xsl:if>
</xsl:template>

<xsl:template name="make_fontsize">
  <xsl:variable name="fontSize">
    <xsl:value-of select="style:properties/@fo:font-size" />
  </xsl:variable>
  <xsl:if test="not($fontSize='') and boolean(style:properties/@fo:font-size)">
    <xsl:attribute name="fontSize">
      <xsl:value-of select="$fontSize" />
    </xsl:attribute>
    <xsl:attribute name="leading">
      <xsl:value-of select="$fontSize + floor($fontSize div 5) + 1" />
      <!--use a standard leading related to the font size -->
    </xsl:attribute>
  </xsl:if>
</xsl:template>

<!--this template is not needed anymore for "normalized" sxw files -->
<xsl:template name="make_parent">
  <xsl:variable name="parent">
    <xsl:value-of select="@style:parent-style-name" />
  </xsl:variable>
  <xsl:if test="not($parent='') and boolean(@style:parent-style-name)">
    <xsl:attribute name="parent">
      <xsl:value-of select="$parent" />
    </xsl:attribute>
  </xsl:if>
</xsl:template>

<xsl:template name="make_alignment">
  <xsl:variable name="alignment">
    <xsl:value-of select="style:properties/@fo:text-align" />
  </xsl:variable>
  <xsl:if test="not($alignment='') and boolean(style:properties/@fo:text-align)">
    <xsl:choose>
      <xsl:when test="$alignment='start'">
        <xsl:attribute name="alignment">LEFT</xsl:attribute>
      </xsl:when>
      <xsl:when test="$alignment='center'">
        <xsl:attribute name="alignment">CENTER</xsl:attribute>
      </xsl:when>
      <xsl:when test="$alignment='end'">
        <xsl:attribute name="alignment">RIGHT</xsl:attribute>
      </xsl:when>
      <xsl:when test="$alignment='justify'">
        <xsl:attribute name="alignment">JUSTIFY</xsl:attribute>
      </xsl:when>
    </xsl:choose>
  </xsl:if>
</xsl:template>

<xsl:template name="make_fontnames_paragraph">
  <xsl:attribute name="fontName">
    <xsl:call-template name="make_fontnames">
      <xsl:with-param name="fontName" select="style:properties/@style:font-name" />
      <xsl:with-param name="fontWeight" select="style:properties/@fo:font-weight" />
      <xsl:with-param name="fontStyle" select="style:properties/@fo:font-style" />
    </xsl:call-template>
  </xsl:attribute>
</xsl:template>

<xsl:template name="make_fontnames">
  <!--much too verbose, needs improvement-->
<xsl:param name="fontName" />
<xsl:param name="fontWeight" />
<xsl:param name="fontStyle" />
<xsl:choose>
<xsl:when test="not($fontName='') and boolean($fontName)">
  <xsl:choose>
    <xsl:when test="contains($fontName,'Courier')">
      <xsl:choose>
        <xsl:when test="($fontWeight='bold') and ($fontStyle='italic')">
          <xsl:text>Courier-BoldOblique</xsl:text>
        </xsl:when>
        <xsl:when test="($fontWeight='bold') and not ($fontStyle='italic')">
          <xsl:text>Courier-Bold</xsl:text>
        </xsl:when>
        <xsl:when test="not($fontWeight='bold') and ($fontStyle='italic')">
          <xsl:text>Courier-Oblique</xsl:text>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>Courier</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:when>
    <xsl:when test="contains($fontName,'Helvetica') or contains($fontName,'Arial') or contains($fontName,'Sans')">
      <xsl:choose>
        <xsl:when test="($fontWeight='bold') and ($fontStyle='italic')">
          <xsl:text>Helvetica-BoldOblique</xsl:text>
        </xsl:when>
        <xsl:when test="($fontWeight='bold') and not ($fontStyle='italic')">
          <xsl:text>Helvetica-Bold</xsl:text>
        </xsl:when>
        <xsl:when test="not($fontWeight='bold') and ($fontStyle='italic')">
          <xsl:text>Helvetica-Oblique</xsl:text>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>Helvetica</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:when>
    <xsl:otherwise>
      <xsl:choose>
        <xsl:when test="($fontWeight='bold') and ($fontStyle='italic')">
          <xsl:text>Helvetica-BoldOblique</xsl:text>
        </xsl:when>
        <xsl:when test="($fontWeight='bold') and not ($fontStyle='italic')">
          <xsl:text>Helvetica-Bold</xsl:text>
        </xsl:when>
        <xsl:when test="not($fontWeight='bold') and ($fontStyle='italic')">
          <xsl:text>Helvetica-Oblique</xsl:text>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>Helvetica</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:otherwise>
  </xsl:choose>
</xsl:when>
<xsl:otherwise>
  <!--Use this as default -->
  <xsl:text>Helvetica</xsl:text>
</xsl:otherwise>
</xsl:choose>
</xsl:template>
<xsl:template name="make_fontcolor">
  <xsl:variable name="textColor">
    <xsl:value-of select="style:properties/@fo:color"/>
  </xsl:variable>
  <xsl:if test="not($textColor='') and boolean(style:properties/@fo:color)">
  <xsl:attribute name="textColor">
      <xsl:value-of select="$textColor" />
   </xsl:attribute>
  </xsl:if>
</xsl:template>

<!--
This stylesheet is part of:
PyOpenOffice Version 0.4
Copyright (C) 2005: Martin Simon
Homepage: www.bezirksreiter.de

GNU LESSER GENERAL PUBLIC LICENSE Version 2.1, February 1999
-->

</xsl:stylesheet>


