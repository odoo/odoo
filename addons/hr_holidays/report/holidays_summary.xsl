<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fo="http://www.w3.org/1999/XSL/Format">

    <xsl:import href="hr_custom_default.xsl"/>
    <xsl:import href="hr_custom_rml.xsl"/>

    <xsl:template match="/">
        <xsl:call-template name="rml" />
    </xsl:template>

    <xsl:template name="stylesheet">
                <paraStyle name="normal" fontName="Helvetica" fontSize="6" alignment="left" />
                <paraStyle name="normal-title" fontName="Helvetica" fontSize="10" alignment="center"/>
                <paraStyle name="digits" fontName="Helvetica" fontSize="6" alignment="left"/>
                <paraStyle name="title" fontName="Helvetica" fontSize="18" alignment="center" />
                <paraStyle name="dept" fontName="Helvetica-Bold" fontSize="8" alignment="left" />
                <paraStyle name="employee" fontName="Helvetica-Bold" fontSize="6" textColor="black" />
                <paraStyle name="leaveid" fontName="Helvetica" fontSize="6" alignment="center" />
                <paraStyle name="print-date" fontName="Helvetica" fontSize="11" alignment="right" />
                <paraStyle name="sum" fontName="Helvetica-BoldOblique" fontSize="6" alignment="left" />
                <paraStyle name="company" textColor="purple" fontName="Helvetica-Bold" fontSize="11" alignment="left"/>
                <blockTableStyle id="header">
                       <blockAlignment value="LEFT" start="0,0" stop="-1,-1"/>
                       <blockFont name="Helvetica" size="8" start="0,0" stop="-1,-1"/>
                      <blockValign value="TOP"/>
                   </blockTableStyle>
                <blockTableStyle id="products">
                     <blockAlignment value="CENTER" start="1,0" stop="-1,-1"/>
                     <lineStyle kind="LINEABOVE" colorName="black" start="0,0" stop="-1,-1" />
                     <lineStyle kind="LINEBEFORE" colorName="black" start="0,0" stop="-1,-1"/>
                     <lineStyle kind="LINEAFTER" colorName="black" start="-1,0" stop="-1,-1"/>
                     <lineStyle kind="LINEBELOW" colorName="black" start="0,-1" stop="-1,-1"/>
                     <blockFont name="Helvetica-Bold" size="8" start="0,-1" stop="-1,-1"/>
                     <blockValign value="TOP"/>
                </blockTableStyle>
                <blockTableStyle id="legend">
                    <blockAlignment value="CENTER" start="0,0" stop="-1,-1" />
                    <blockFont name="Helvetica" size="7" start="0,0" stop="-1,-1"/>
                    <lineStyle kind="LINEABOVE" colorName="black" start="0,0" stop="-1,-1" />
                    <lineStyle kind="LINEBEFORE" colorName="black" start="0,0" stop="-1,-1"/>
                    <lineStyle kind="LINEAFTER" colorName="black" start="-1,0" stop="-1,-1"/>
                    <lineStyle kind="LINEBELOW" colorName="black" start="0,-1" stop="-1,-1"/>
                    <blockBackground colorName="#FFFFFF" start="0,0" stop="-1,-1"/>
                    <xsl:for-each select="/report/legend">
                        <blockBackground>
                            <xsl:attribute name="colorName">
                            <xsl:value-of select="attribute::color" />
                            </xsl:attribute>
                            <xsl:attribute name="start">
                                <xsl:text>0,</xsl:text>
                                <xsl:value-of select="attribute::row" />
                            </xsl:attribute>
                            <xsl:attribute name="stop">
                                <xsl:text>0,</xsl:text>
                                <xsl:value-of select="attribute::row" />
                            </xsl:attribute>
                        </blockBackground>
                    </xsl:for-each>
                    <blockValign value="TOP"/>
                </blockTableStyle>
                <blockTableStyle id="month">
                    <blockAlignment value="CENTER" start="1,0" stop="-1,-1" />
                    <blockFont name="Helvetica" size="5" start="0,0" stop="-1,-1"/>
                    <blockFont name="Helvetica-BoldOblique" size="4.5" start="-1,0" stop="-1,-1"/>
                    <blockBackground colorName="#FFFFFF" start="1,0" stop="-2,1"/>
                    <xsl:for-each select="/report/days/dayy[@name='Sat' or @name='Sun']">
                        <xsl:variable name="col" select="attribute::cell" />
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
                    <xsl:for-each select="/report/info">
                        <xsl:variable name="val" select="attribute::val" />
                        <xsl:variable name="col" select="attribute::number" />
                        <xsl:variable name="row" select="attribute::id" />
                        <xsl:for-each select="/report/legend">
                            <xsl:variable name="val_id" select="attribute::id" />
                            <xsl:variable name="color" select="attribute::color" />
                            <xsl:if test="$val_id = $val ">
                                <blockBackground>
                                    <xsl:attribute name="colorName"><xsl:value-of select="$color" /></xsl:attribute>
                                    <xsl:attribute name="start">
                                        <xsl:value-of select="$col" />
                                        <xsl:text>,</xsl:text>
                                        <xsl:value-of select="$row + 1" />
                                    </xsl:attribute>
                                    <xsl:attribute name="stop">
                                        <xsl:value-of select="$col" />
                                        <xsl:text>,</xsl:text>
                                        <xsl:value-of select="$row + 1" />
                                    </xsl:attribute>
                                </blockBackground>
                            </xsl:if>
                        </xsl:for-each>
                    </xsl:for-each>
                    <xsl:for-each select="report/employee">
                        <xsl:variable name="dept" select="attribute::id" />
                        <xsl:variable name="row" select="attribute::row" />
                        <xsl:if test="$dept = 1">
                            <blockBackground>
                                <xsl:attribute name="colorName">lightgrey</xsl:attribute>
                                <xsl:attribute name="start">
                                    <xsl:text>0,</xsl:text>
                                    <xsl:value-of select="$row +1" />
                                </xsl:attribute>
                                <xsl:attribute name="stop">
                                    <xsl:text>0,</xsl:text>
                                    <xsl:value-of select="$row +1" />
                                </xsl:attribute>
                            </blockBackground>
                        </xsl:if>
                    </xsl:for-each>
                    <lineStyle kind="LINEABOVE" colorName="black" start="0,0" stop="-1,-1" />
                    <lineStyle kind="LINEBEFORE" colorName="black" start="0,0" stop="-1,-1"/>
                    <lineStyle kind="LINEAFTER" colorName="black" start="-1,0" stop="-1,-1"/>
                    <lineStyle kind="LINEBELOW" colorName="black" start="0,-1" stop="-1,-1"/>
                    <blockValign value="TOP"/>
                </blockTableStyle>
    </xsl:template>

    <xsl:template name="story">
    <xsl:variable name="cols_header">
            <xsl:text>13.7cm,13.7cm</xsl:text>
    </xsl:variable>
    <blockTable>
            <xsl:attribute name="style">header</xsl:attribute>
            <xsl:attribute name="colWidths"><xsl:value-of select="$cols_header"/></xsl:attribute>
            <tr>
                <xsl:for-each select="report/res">
                    <td>
                    <para>
                    </para>
                    </td>
                    <td>
                    <para>
                    </para>
                    </td>
                </xsl:for-each>
            </tr>
        </blockTable>
        <spacer length="1.0cm" />
        <para style="title" t="1">Leaves Summary <xsl:value-of select="report/name" /></para>
        <spacer length="0.5cm" />
        <para style="normal-title" t="1">Analyze from <u><xsl:value-of select="report/from" /></u> to <u> <xsl:value-of select="report/to" /> </u> of the <u><xsl:value-of select="report/type" /></u> leaves. </para>
        <spacer length="1.0cm" />
        <xsl:variable name="cols_legend">
            <xsl:text>0.7cm,5.0cm</xsl:text>
        </xsl:variable>
        <blockTable>
            <xsl:attribute name="style">products</xsl:attribute>
            <xsl:attribute name="colWidths"><xsl:value-of select="report/cols_months"/></xsl:attribute>
            <tr>
                 <td>Month</td>
                <xsl:for-each select="report/months">
                    <td>
                        <xsl:value-of select="attribute::name" />
                    </td>
                </xsl:for-each>
                <td> </td>
            </tr>
        </blockTable>

        <blockTable>
            <xsl:attribute name="style">month</xsl:attribute>
            <xsl:attribute name="colWidths"><xsl:value-of select="report/cols" /></xsl:attribute>
            <tr>
                <td> </td>
                <xsl:for-each select="report/days/dayy">
                    <td>
                        <xsl:value-of select="attribute::name" />
                    </td>
                </xsl:for-each>
                <td> </td>
            </tr>
            <tr>
                <td><para>
                        <xsl:attribute name="style">employee</xsl:attribute>
                                Departments and Employees
                    </para>
                </td>
                <xsl:for-each select="report/days/dayy">
                    <td><para><xsl:attribute name="style">digits</xsl:attribute>
                        <xsl:value-of select="attribute::number" /></para>
                    </td>
                </xsl:for-each>
                <td>Sum</td>
            </tr>
            <xsl:apply-templates select="report/employee"/>
            <xsl:for-each select="report/employee">
                <xsl:variable name="id" select="attribute::id"/>
                <xsl:variable name="rw" select="attribute::row"/>
                <xsl:variable name="sum" select="attribute::sum"/>
                <tr>
                    <td t="1">
                        <para>
                            <xsl:choose>
                                    <xsl:when test="$id = 1">
                                       <xsl:attribute name="style">dept</xsl:attribute>
                                   </xsl:when>
                                <xsl:otherwise>
                                      <xsl:attribute name="style">normal</xsl:attribute>
                                   </xsl:otherwise>
                            </xsl:choose>
                            <xsl:value-of select="attribute::name"/>
                        </para>
                    </td>
                    <xsl:for-each select="//report/days/dayy">
                        <xsl:variable name="cell" select="attribute::cell" />
                        <td>
                        <para><xsl:attribute name="style">digits</xsl:attribute>
                        <xsl:value-of select="//employee[@row=$rw]/time-element[@index=$cell]"/>
                        </para>

                        </td>
                    </xsl:for-each>
                    <td><para>
                        <xsl:attribute name="style">sum</xsl:attribute><xsl:value-of select="attribute::sum"/></para></td>
                </tr>
            </xsl:for-each>

        </blockTable>
        <spacer length="1cm" />
        <condPageBreak height="1in" />
        <blockTable>
            <xsl:attribute name="style">legend</xsl:attribute>
            <xsl:attribute name="colWidths"><xsl:value-of select="$cols_legend"/></xsl:attribute>
            <tr>
                    <td>Color</td>
                    <td>Leave Type</td>

            </tr>
            <xsl:for-each select="report/legend">
            <tr>
                    <td>
                            <para>
                            <xsl:attribute name="style">digits</xsl:attribute>
                            </para>
                    </td>
                    <td>
                            <para>
                            <xsl:attribute name="style">normal</xsl:attribute>
                                <xsl:value-of select="attribute::name"/>
                            </para>
                    </td>
            </tr>
            </xsl:for-each>
        </blockTable>
    </xsl:template>
</xsl:stylesheet>
