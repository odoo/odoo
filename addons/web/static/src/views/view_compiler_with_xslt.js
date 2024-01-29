/** @odoo-module **/

import { createElement } from "@web/core/utils/xml";
import { SIZES } from "@web/core/ui/ui_service";

// improve with variables, params,...
const xslt = `
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:output method="xml" />

    <xsl:template match="form">
        <xsl:variable name="hasSheet" select="boolean(//sheet)" />
        <div>
            <xsl:attribute name="class">o_form_renderer<xsl:if test="not($hasSheet)"> o_form_nosheet</xsl:if></xsl:attribute>
            <xsl:attribute name="t-att-class">__comp__.props.class</xsl:attribute>
            <xsl:attribute name="t-attf-class">{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}}<xsl:choose><xsl:when test="$hasSheet"> d-flex {{ __comp__.uiService.size &lt; ${SIZES.XXL} ? 'flex-column' : 'flex-nowrap h-100' }}</xsl:when><xsl:otherwise> d-block</xsl:otherwise></xsl:choose> {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}</xsl:attribute>
            <xsl:if test="true()">
                <xsl:attribute name="t-ref">compiled_view_root</xsl:attribute>
            </xsl:if>
            <xsl:apply-templates select="*|@*"/>
        </div>
    </xsl:template>

    <xsl:template match="*">
        <xsl:copy>
            <xsl:apply-templates select="*|@*|text()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="@*">
        <xsl:copy />
    </xsl:template>

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

    <xsl:template match="label[@for]">

    </xsl:template>
    
    <!-- remove comments -->
    <xsl:template match="comment()" /> 

</xsl:stylesheet>
`;

export class ViewCompilerWithXSLT {
    constructor(templates) {
        this.xsltProcessor = new XSLTProcessor();
        const xslStylesheet = new DOMParser().parseFromString(xslt, "application/xml");
        this.xsltProcessor.importStylesheet(xslStylesheet);
        this.templates = templates;
        this.setup();
    }

    setup() {}

    compile(key, params = {}) {
        for (const [k, v] of Object.entries(params)) {
            this.xsltProcessor.setParameter(null, k, v);
        }
        const root = this.templates[key].cloneNode(true);
        const doc = new Document();
        doc.append(root);
        const fragment = this.xsltProcessor.transformToFragment(doc.firstElementChild, document);
        const newRoot = createElement("t", [fragment]);
        return newRoot;
    }
}
