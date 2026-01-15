import { describe, expect, test } from "@odoo/hoot";
import { expectMarkup, allowTranslations } from "@web/../tests/web_test_helpers";

import { renderToElement, renderToString } from "@web/core/utils/render";

describe.current.tags("headless");

test("renderToElement always returns an element", () => {
    allowTranslations();
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
    expectMarkup(compiledTemplate.outerHTML).toBe("<div>Ok</div>");
});
