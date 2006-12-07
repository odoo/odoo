<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fo="http://www.w3.org/1999/XSL/Format">

    <xsl:import href="../../custom/corporate_defaults.xsl"/>
    <xsl:import href="../../base/report/rml_template.xsl"/>
    <xsl:variable name="page_format">a4_normal</xsl:variable>

    <xsl:template name="stylesheet">
        <blockTableStyle id="week">
            <blockFont name="Helvetica-BoldOblique" size="12" start="0,0" stop="-1,0"/>
            <blockBackground colorName="grey" start="0,0" stop="-1,0"/>
            <blockTextColor colorName="red" start="-1,0" stop="-1,-1"/>
            <lineStyle kind="LINEBEFORE" colorName="grey" start="-1,0" stop="-1,-1"/>
            <blockValign value="TOP"/>
        </blockTableStyle>
    </xsl:template>

    <xsl:template match="/">
        <xsl:call-template name="rml" />
    </xsl:template>

    <xsl:template name="story">
        <xsl:apply-templates select="report/user"/>
    </xsl:template>

    <xsl:template match="user">
        <para>
            <b>Name:</b>
            <i><xsl:value-of select="name" /></i>
        </para>
        <blockTable colWidths="4cm,1.5cm,1.5cm,1.5cm,1.5cm,1.5cm,1.5cm,1.5cm,1.5cm" style="week">
            <tr>
                <td></td>
                <td>Mon</td>
                <td>Tue</td>
                <td>Wed</td>
                <td>Thu</td>
                <td>Fri</td>
                <td>Sat</td>
                <td>Sun</td>
                <td>Tot</td>
            </tr>
            <xsl:for-each select="week">
                <tr></tr>
                <tr>
                    <td>Week :</td>
                    <td></td>
                    <td>from <xsl:value-of select="weekstart" /> to <xsl:value-of select="weekend" /></td>
                </tr>
                <tr>
                    <td>Theoretical workhours</td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Monday/theoretical">
                                <xsl:value-of select="Monday/theoretical" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Tuesday/theoretical">
                                <xsl:value-of select="Tuesday/theoretical" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Wednesday/theoretical">
                                <xsl:value-of select="Wednesday/theoretical" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Thursday/theoretical">
                                <xsl:value-of select="Thursday/theoretical" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Friday/theoretical">
                                <xsl:value-of select="Friday/theoretical" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Saturday/theoretical">
                                <xsl:value-of select="Saturday/theoretical" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Sunday/theoretical">
                                <xsl:value-of select="Sunday/theoretical" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:value-of select="total/theoretical" />
                    </td>
                </tr>
                <tr>
                    <td>Workhours</td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Monday/workhours">
                                <xsl:value-of select="Monday/workhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Tuesday/workhours">
                                <xsl:value-of select="Tuesday/workhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Wednesday/workhours">
                                <xsl:value-of select="Wednesday/workhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Thursday/workhours">
                                <xsl:value-of select="Thursday/workhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Friday/workhours">
                                <xsl:value-of select="Friday/workhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Saturday/workhours">
                                <xsl:value-of select="Saturday/workhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Sunday/workhours">
                                <xsl:value-of select="Sunday/workhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:value-of select="total/worked" />
                    </td>
                </tr>
                <tr>
                    <td>Holiday hours</td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Monday/holidayhours">
                                <xsl:value-of select="Monday/holidayhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Tuesday/holidayhours">
                                <xsl:value-of select="Tuesday/holidayhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Wednesday/holidayhours">
                                <xsl:value-of select="Wednesday/holidayhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Thursday/holidayhours">
                                <xsl:value-of select="Thursday/holidayhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Friday/holidayhours">
                                <xsl:value-of select="Friday/holidayhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Saturday/holidayhours">
                                <xsl:value-of select="Saturday/holidayhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:choose>
                            <xsl:when test="Sunday/holidayhours">
                                <xsl:value-of select="Sunday/holidayhours" />
                            </xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>							
                    </td>
                    <td>
                        <xsl:value-of select="total/holiday" />
                    </td>
                </tr>
            </xsl:for-each>
        </blockTable>
    </xsl:template>
</xsl:stylesheet>
