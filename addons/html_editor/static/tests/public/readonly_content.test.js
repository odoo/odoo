import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { location } from "@web/core/browser/browser";

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
