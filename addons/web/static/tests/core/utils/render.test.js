import { expect, test } from "@odoo/hoot";

import { renderToElement, renderToString } from "@web/core/utils/render";

test`headless`("renderToElement always returns an element", () => {
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
    expect(compiledTemplate.parentElement).toBe(null, {
        message: "compiledTemplate.parentElement must be empty",
    });
    expect(compiledTemplate.nodeType).toBe(Node.ELEMENT_NODE, {
        message: "compiledTemplate must be an element",
    });
    expect(compiledTemplate.outerHTML).toBe("<div>Ok</div>");
});
