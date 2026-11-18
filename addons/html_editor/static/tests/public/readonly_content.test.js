import { describe, expect, test } from "@odoo/hoot";
import { dblclick, queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { location } from "@web/core/browser/browser";
import { base64Img } from "../_helpers/editor";
import { expectElementCount } from "../_helpers/ui_expectations";

setupInteractionWhiteList("html_editor.readonly_content");

describe.current.tags("interaction_dev");

describe("accessibility attributes", () => {
    test("applies the accessibility attributes set in the editor", async () => {
        await startInteractions(
            `<div class="o_readonly"><span data-oe-role="img" data-oe-aria-label="Logo">a</span></div>`
        );
        expect("span").toHaveAttribute("role", "img");
        expect("span").toHaveAttribute("aria-label", "Logo");
    });

    test("removes them when interactions stop", async () => {
        const { core } = await startInteractions(
            `<div class="o_readonly"><span data-oe-role="img" data-oe-aria-label="Logo">a</span></div>`
        );
        core.stopInteractions();
        expect("span").not.toHaveAttribute("role");
        expect("span").not.toHaveAttribute("aria-label");
    });
});

describe("links", () => {
    test("opens external links in a new tab", async () => {
        await startInteractions(
            `<div class="o_readonly"><a class="external" href="https://www.odoo.com">a</a></div>`
        );
        expect("a.external").toHaveAttribute("target", "_blank");
        expect("a.external").toHaveAttribute("rel", "noreferrer noopener");
    });

    test("does not change links to the website itself", async () => {
        await startInteractions(
            `<div class="o_readonly"><a class="relative" href="/odoo">a</a><a class="absolute" href="${location.origin}/odoo">b</a></div>`
        );
        expect("a.relative").not.toHaveAttribute("target");
        expect("a.absolute").not.toHaveAttribute("target");
    });
});

describe("tables", () => {
    test("wraps the tables in a scroll container, except the nested ones", async () => {
        await startInteractions(
            `<div class="o_readonly"><table class="o_table"><tbody><tr><td><table class="o_table"><tbody><tr><td>a</td></tr></tbody></table></td></tr></tbody></table></div>`
        );
        expect(".o_readonly > .o_table_wrapper > table").toHaveCount(1);
        expect("td .o_table_wrapper").toHaveCount(0);
    });
});

describe("copy", () => {
    test("copies the selection with the editor's clipboard format", async () => {
        await startInteractions(
            `<div class="o_readonly"><p>before</p><p><strong>A</strong></p><p>after</p></div>`
        );
        const range = new Range();
        range.setStart(queryOne("p:first-child"), 1);
        range.setEnd(queryOne("p:last-child"), 0);
        getSelection().removeAllRanges();
        getSelection().addRange(range);

        const clipboardData = new DataTransfer();
        queryOne(".o_readonly").dispatchEvent(
            new ClipboardEvent("copy", { bubbles: true, clipboardData })
        );

        expect(clipboardData.getData("text/plain").trim()).toBe("A");
        expect(clipboardData.getData("text/html")).toInclude("<strong>A</strong>");
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
            clipboardData.getData("text/html")
        );
    });
});

describe("image preview", () => {
    test.tags("desktop");
    test("double-clicking a readonly image opens its preview", async () => {
        await startInteractions(`<div class="o_readonly"><img src="${base64Img}"></div>`);
        await mountWithCleanup(MainComponentsContainer);
        const image = queryOne(".o_readonly img");
        await dblclick(image);
        await expectElementCount(".o-FileViewer-viewImage", 1);
        expect(".o-FileViewer-viewImage").toHaveAttribute("data-src", image.src);
    });

    test.tags("desktop");
    test("double-clicking an image of an embedded component only opens its preview in an editable part", async () => {
        await startInteractions(
            `<div class="o_readonly"><div data-embedded="toggle"><img src="${base64Img}"><div data-embedded-editable="content"><img src="${base64Img}"></div></div></div>`
        );
        await mountWithCleanup(MainComponentsContainer);
        await expectElementCount(".o_readonly img", 2);
        await dblclick(queryOne("[data-embedded] > img"));
        await animationFrame();
        expect(".o-FileViewer").toHaveCount(0);

        const image = queryOne("[data-embedded-editable] img");
        await dblclick(image);
        await expectElementCount(".o-FileViewer-viewImage", 1);
        expect(".o-FileViewer-viewImage").toHaveAttribute("data-src", image.src);
    });

    test.tags("desktop");
    test("closes the preview when interactions stop", async () => {
        const { core } = await startInteractions(
            `<div class="o_readonly"><img src="${base64Img}"></div>`
        );
        await mountWithCleanup(MainComponentsContainer);
        await dblclick(".o_readonly img");
        await expectElementCount(".o-FileViewer-viewImage", 1);
        core.stopInteractions();
        await animationFrame();
        expect(".o-FileViewer").toHaveCount(0);
    });
});
