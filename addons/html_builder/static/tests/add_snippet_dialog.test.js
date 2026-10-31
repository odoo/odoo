import { animationFrame, edit, expect, press, queryFirst, queryOne, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    confirmAddSnippet,
    createTestSnippets,
    getSnippetStructure,
    setupHTMLBuilder,
    waitForSnippetDialog,
} from "@html_builder/../tests/helpers";

const MOBILE_BTN = ".o_add_snippet_dialog button[title='Toggle Mobile Preview']";
const SNIPPET_IFRAME = ".o_add_snippet_dialog iframe.o_add_snippet_iframe";

async function openSnippetDialog() {
    await contains(".o_snippet_thumbnail_area").click();
    await waitForSnippetDialog();
}

test("Toggling mobile preview button manages snippet layout and restores original state", async () => {
    await setupHTMLBuilder(`<h1> Homepage </h1>`);
    await openSnippetDialog();
    expect(MOBILE_BTN).toHaveCount(1);

    const iframeEl = document.querySelector(SNIPPET_IFRAME);
    const iframeDoc = iframeEl.contentDocument;
    expect(iframeDoc.querySelectorAll(".o_snippets_preview_row > div")).toHaveCount(2);

    await contains(MOBILE_BTN).click();
    expect(iframeDoc.querySelectorAll(".o_snippets_preview_row > div")).toHaveCount(3);

    await contains(MOBILE_BTN).click();
    expect(iframeDoc.querySelectorAll(".o_snippets_preview_row > div")).toHaveCount(2);
});

test("Selecting a snippet while mobile preview is active drops it into the editable", async () => {
    const { getEditableContent } = await setupHTMLBuilder(`<h1> Homepage </h1>`);
    const editableContent = getEditableContent();
    await openSnippetDialog();
    await contains(MOBILE_BTN).click();
    expect(MOBILE_BTN).toHaveClass("text-success");

    await confirmAddSnippet("s_test");
    expect(".o_add_snippet_dialog").toHaveCount(0);
    expect(editableContent.querySelectorAll("[data-snippet='s_test']")).toHaveCount(1);
});

test.tags("desktop");
test("Tabs navigation", async () => {
    const snippets = [
        { name: "Test", groupName: "a", innerHTML: "Yop" },
        { name: "Test", groupName: "b", innerHTML: "Hello" },
        { name: "Test", groupName: "c", innerHTML: "Nice" },
    ];
    await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
                '<div name="B" data-oe-snippet-id="123" data-o-snippet-group="b"><section data-snippet="s_snippet_group"></section></div>',
                '<div name="C" data-oe-snippet-id="123" data-o-snippet-group="c"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: createTestSnippets({ snippets, withName: false }).map(
                (snippetDesc) => getSnippetStructure(snippetDesc)
            ),
        },
    });
    await openSnippetDialog();
    await contains(".o_add_snippet_dialog_search").focus();
    // Tab behavior should be initialized.
    expect(".o_add_snippet_dialog .active[role=tab]:not([tabindex='-1'])").toHaveCount(1);
    expect(".o_add_snippet_dialog [role=tab][tabindex='-1']").toHaveCount(2);
    const activeBtnEl = queryOne(".o_add_snippet_dialog .active[role=tab][tabindex='0']");
    await press("Tab");
    expect(document.activeElement).toBe(activeBtnEl);
    await press("ArrowDown");
    expect(document.activeElement).toBe(
        queryFirst(".o_add_snippet_dialog [role=tab][tabindex='-1']")
    );
    expect(queryOne(".o_add_snippet_dialog .active[tabindex='0']")).toBe(activeBtnEl);
    await press("Alt+S"); // Focus the search input.
    await edit("az"); // Make a dummy search to reinitialize the tabs.
    await animationFrame();
    expect(".o_add_snippet_dialog [role=tab]").toHaveCount(0);
    await edit(""); // Delete the search
    await animationFrame();
    // Tab behavior should be back.
    expect(".o_add_snippet_dialog [role=tab]:not([tabindex='-1'])").toHaveCount(1);
});
