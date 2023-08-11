/** @odoo-module **/

import { renderToElement, renderToString } from "@web/core/utils/render";

QUnit.module("utils", () => {
    QUnit.module("render");

    QUnit.test("renderToElement always returns an element", (assert) => {
        renderToString.app.addTemplate(
            "test.render.template.1",
            `<t t-if="False">
              <div>NotOk</div>
            </t>
            <t t-else="">
              <div>Ok</div>
            </t>`
        );
        const compiledTemplate = renderToElement("test.render.template.1");
        assert.strictEqual(
            compiledTemplate.parentElement,
            null,
            "compiledTemplate.parentElement must be empty"
        );
        assert.strictEqual(
            compiledTemplate.nodeType,
            Node.ELEMENT_NODE,
            "compiledTemplate must be an element"
        );
        assert.strictEqual(compiledTemplate.outerHTML, "<div>Ok</div>");
    });
});
