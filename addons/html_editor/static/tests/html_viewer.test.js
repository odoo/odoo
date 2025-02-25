import { HtmlViewer } from "@html_editor/fields/html_viewer";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { markup } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";

test(`XML-like self-closing elements are fixed in a standalone HtmlViewer`, async () => {
    await mountWithCleanup(WebClient);

    registry.category("main_components").add("mycomponent", {
        Component: HtmlViewer,
        props: {
            config: {
                value: markup(`<a href="#"/>outside<a href="#">inside</a>`),
            },
        },
    });
    await animationFrame();
    expect(".o_readonly").toHaveInnerHTML(
        `<a href="#" target="_blank" rel="noreferrer"></a>outside<a href="#" target="_blank" rel="noreferrer">inside</a>`
    );
});
