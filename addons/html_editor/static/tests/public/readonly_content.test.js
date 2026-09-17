import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { browser } from "@web/core/browser/browser";

setupInteractionWhiteList("html_editor.readonly_content");

describe.current.tags("interaction_dev");

describe("table scroll container", () => {
    test("wraps the tables of readonly content, except the nested ones", async () => {
        await startInteractions(
            `<div class="o_readonly"><table class="o_table"><tbody><tr><td><table class="o_table"><tbody><tr><td>a</td></tr></tbody></table></td></tr></tbody></table></div>`
        );
        expect(".o_readonly > .o_table_wrapper > table").toHaveCount(1);
        expect("td .o_table_wrapper").toHaveCount(0);
    });

    test("does not wrap tables outside of readonly content", async () => {
        await startInteractions(
            `<div><table class="o_table"><tbody><tr><td>a</td></tr></tbody></table></div>`
        );
        expect(".o_table_wrapper").toHaveCount(0);
    });

    test("does not wrap an already wrapped table", async () => {
        await startInteractions(
            `<div class="o_readonly"><div class="o_table_wrapper"><table class="o_table"><tbody><tr><td>a</td></tr></tbody></table></div></div>`
        );
        expect(".o_table_wrapper").toHaveCount(1);
    });

    test("restores the content when interactions stop, and wraps it again when they restart", async () => {
        const { core } = await startInteractions(
            `<div class="o_readonly"><table class="o_table"><tbody><tr><td>a</td></tr></tbody></table></div>`
        );
        expect(".o_readonly > .o_table_wrapper > table").toHaveCount(1);

        core.stopInteractions();
        expect(".o_table_wrapper").toHaveCount(0);
        expect(".o_readonly > table").toHaveCount(1);

        await core.startInteractions();
        expect(".o_readonly > .o_table_wrapper > table").toHaveCount(1);
    });
});

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
        expect("a.external").toHaveAttribute("rel", "noreferrer");
    });

    test("does not change links to the website itself", async () => {
        await startInteractions(
            `<div class="o_readonly"><a class="relative" href="/odoo">a</a><a class="absolute" href="${browser.location.origin}/odoo">b</a></div>`
        );
        expect("a.relative").not.toHaveAttribute("target");
        expect("a.absolute").not.toHaveAttribute("target");
    });

    test("restores the links when interactions stop", async () => {
        const { core } = await startInteractions(
            `<div class="o_readonly"><a href="https://www.odoo.com" target="_self">a</a></div>`
        );
        core.stopInteractions();
        expect("a").toHaveAttribute("target", "_self");
        expect("a").not.toHaveAttribute("rel");
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
