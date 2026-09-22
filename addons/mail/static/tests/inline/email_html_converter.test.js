import { useEmailHtmlConverter } from "@mail/convert_inline/hooks";
import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

defineMailModels();

class Converter extends Component {
    static template = xml`<div/>`;

    setup() {
        this.converter = useEmailHtmlConverter({});
    }
}

test("reference iframe does not make the page scrollable", async () => {
    const { converter } = await mountWithCleanup(Converter);
    const fragment = document.createRange().createContextualFragment("<p>Hello</p>");
    const template = await converter.convertToEmailHtml(fragment);
    expect(template.innerHTML).toInclude("Hello");
    const pageHeight = document.documentElement.scrollHeight;
    // Taller than any test viewport, so it would overflow the page if it took part in its layout.
    converter.updateLayoutDimensions({ width: 1320, height: 20000 });
    expect(document.documentElement.scrollHeight).toBe(pageHeight);
});
