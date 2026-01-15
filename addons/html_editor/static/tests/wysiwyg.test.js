import { describe, expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupWysiwyg } from "./_helpers/editor";
import { getContent, setContent, setSelection } from "./_helpers/selection";
import { expectElementCount } from "./_helpers/ui_expectations";
import { range } from "@web/core/utils/numbers";
import { htmlJoin } from "@web/core/utils/html";
import { markup } from "@odoo/owl";

describe("Wysiwyg Component", () => {
    test("Wysiwyg component can be instantiated", async () => {
        const { el } = await setupWysiwyg();
        expect(".o-wysiwyg").toHaveCount(1);
        expect(".odoo-editor-editable").toHaveCount(1);
        await expectElementCount(".o-we-toolbar", 0);

        // set the selection to a range, and check that the toolbar
        // is opened
        expect(getContent(el)).toBe("");
        setContent(el, "hello [hoot]");
        await animationFrame();
        await expectElementCount(".o-we-toolbar", 1);
    });

    test("Wysiwyg component can be instantiated with initial content", async () => {
        const { el } = await setupWysiwyg({
            config: { content: markup`<p>hello rodolpho</p>` },
        });
        expect(el.innerHTML).toBe(`<p>hello rodolpho</p>`);
    });

    test("Wysiwyg in iframe with a contentClass that need to be trim", async () => {
        await setupWysiwyg({
            iframe: true,
            contentClass: "test ",
        });
        expect(":iframe .test.odoo-editor-editable").toHaveCount(1);
    });

    test.tags("desktop");
    test("wysiwyg in iframe: toolbar should be well positioned", async () => {
        const CLOSE_ENOUGH = 10;
        const { el } = await setupWysiwyg({
            iframe: true,
            config: {
                content: htmlJoin(
                    range(0, 30).map(() => markup`<p>editable text inside the iframe</p>`)
                ),
            },
        });

        // Add some content before the iframe to make sure it's top does not
        // match the top window's top (i.e. create a vertical offset).
        const iframe = document.querySelector("iframe");
        for (let i = 0; i < 10; i++) {
            const p = document.createElement("p");
            p.textContent = "content outside the iframe";
            iframe.before(p);
        }
        const iframeOffset = iframe.getBoundingClientRect().top;

        // Select a paragraph's content to display the toolbar.
        const p = el.childNodes[5];
        setSelection({ anchorNode: p, anchorOffset: 0, focusNode: p, focusOffset: 1 });
        const toolbar = await waitFor(".o-we-toolbar");

        // Check that toolbar is on top of and close to the selected paragraph.
        const pTop = p.getBoundingClientRect().top + iframeOffset;
        const toolbarBottom = toolbar.getBoundingClientRect().bottom;
        expect(pTop - toolbarBottom).toBeWithin(0, CLOSE_ENOUGH);
    });
});
