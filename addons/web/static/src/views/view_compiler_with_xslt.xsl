<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:template match="field">
        <xsl:variable name="recordExpr" select="'__comp__.props.record'" />
        <xsl:variable name="field_id">
            <xsl:choose>
                <xsl:when test="@field_id"><xsl:value-of select="@field_id" /></xsl:when>
                <xsl:otherwise>null</xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <Field
            id="'{$field_id}'"
            name="'{@name}'"
            record="{$recordExpr}"
            fieldInfo="__comp__.props.archInfo.fieldNodes['{$field_id}']"
            readonly="__comp__.props.archInfo.activeActions?.edit === false and !{$recordExpr}.isNew"
        >
            <xsl:if test="@widget">
                <xsl:attribute name="type">'<xsl:value-of select="@widget"/>'</xsl:attribute>
            </xsl:if>
        </Field>
    </xsl:template>
    
    <!-- remove comments -->
    <xsl:template match="comment()" />

</xsl:stylesheet>
