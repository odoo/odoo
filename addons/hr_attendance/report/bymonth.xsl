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
				<paraStyle name="terp_header_Centre" fontName="Helvetica-Bold" fontSize="14.0" leading="17" alignment="CENTER" spaceBefore="12.0" spaceAfter="6.0"/>
				<paraStyle name="name" fontName="Helvetica" textColor="green" fontSize="7"/>
				<paraStyle name="normal" fontName="Helvetica" fontSize="6"/>
				<blockTableStyle id="week">
					<blockFont name="Helvetica-BoldOblique" size="8" start="0,0" stop="-1,0"/>
					<blockFont name="Helvetica" size="5" start="0,1" stop="-1,-1"/>
					<blockBackground colorName="grey" start="0,0" stop="-1,0"/>
					<lineStyle kind="LINEABOVE" colorName="grey" start="0,0" stop="-1,0" />
					<lineStyle kind="LINEBEFORE" colorName="grey" start="0,0" stop="-1,-1"/>
					<lineStyle kind="LINEAFTER" colorName="grey" start="-1,0" stop="-1,-1"/>
					<lineStyle kind="LINEBELOW" colorName="grey" start="0,0" stop="-1,-1"/>
					<blockValign value="TOP"/>
				</blockTableStyle>
	</xsl:template>

    <xsl:template name="story">
		<spacer length="1cm" />
		<para style="terp_header_Centre" t="1">Attendance By Month</para>
		<spacer length="1cm" />
        <blockTable
			colWidths="3cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm,0.69cm" style="week">
            <tr>
				<td><xsl:value-of select="/report/month" /><xsl:text> </xsl:text><xsl:value-of select="/report/year" /></td>
				<td>1</td>
				<td>2</td>
				<td>3</td>
				<td>4</td>
				<td>5</td>
				<td>6</td>
				<td>7</td>
				<td>8</td>
				<td>9</td>
				<td>10</td>
				<td>11</td>
				<td>12</td>
				<td>13</td>
				<td>14</td>
				<td>15</td>
				<td>16</td>
				<td>17</td>
				<td>18</td>
				<td>19</td>
				<td>20</td>
				<td>21</td>
				<td>22</td>
				<td>23</td>
				<td>24</td>
				<td>25</td>
				<td>26</td>
				<td>27</td>
				<td>28</td>
				<td>29</td>
				<td>30</td>
				<td>31</td>
            </tr>
			<xsl:apply-templates select="report/user"/>
      </blockTable>
    </xsl:template>

    <xsl:template match="user">
<!--		<tr></tr>-->
		<tr>
			<td>
				<para style="name"><xsl:value-of select="name" /></para>
			</td>
			<xsl:for-each select="day">
				<td><xsl:value-of select="wh" /></td>
			</xsl:for-each>
		</tr>

<!--		<tr>-->
<!--			<td>Worked</td>-->
<!--			-->
<!--		</tr>-->
    </xsl:template>
</xsl:stylesheet>
