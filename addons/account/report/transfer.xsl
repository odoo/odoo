<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format">

	<xsl:import href="../../base/report/corporate_defaults.xsl"/>
	<xsl:import href="../../base/report/rml_template.xsl"/>
	<xsl:variable name="page_format">a4_normal</xsl:variable>

	<xsl:template match="/">
		<xsl:call-template name="rml"/>
	</xsl:template>

	<xsl:template name="stylesheet">
	</xsl:template>

	<xsl:template name="story">
		<xsl:apply-templates select="transfer-list"/>
	</xsl:template>

	<xsl:template match="transfer-list">
		<xsl:apply-templates select="transfer"/>
	</xsl:template>

	<xsl:template match="transfer">
		<setNextTemplate name="other_pages"/>
		<para>
		<b t="1">Document</b>: <i><xsl:value-of select="name"/></i>
		</para><para>
		<b t="1">Type</b>: <i><xsl:value-of select="type"/></i>
		</para><para>
		<b t="1">Reference</b>: <i><xsl:value-of select="reference"/></i>
		</para><para>
		<b t="1">Partner ID</b>: <i><xsl:value-of select="partner_id"/></i>
		</para><para>
		<b t="1">Date</b>: <i><xsl:value-of select="date"/></i>
		</para><para>
		<b t="1">Amount</b>: <i><xsl:value-of select="amount"/></i>
		</para>
		<xsl:if test="number(change)>0">
			<para>
			<b t="1">Change</b>: <i><xsl:value-of select="change"/></i>
			</para>
		</xsl:if>
		<setNextTemplate name="first_page"/>
		<pageBreak/>
	</xsl:template>
</xsl:stylesheet>
