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
            <xsl:apply-templates select="*"/>
        </div>
    </xsl:template>

    <xsl:template match="*|@*|text()">
        <xsl:copy>
            <xsl:apply-templates select="*|@*|text()"/>
        </xsl:copy>
    </xsl:template>

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

    compile(key) {
        const root = this.templates[key].cloneNode(true);
        const doc = new Document();
        doc.append(root);
        const fragment = this.xsltProcessor.transformToFragment(doc.firstElementChild, document);
        const newRoot = createElement("t", [fragment]);
        return newRoot;
    }
}
