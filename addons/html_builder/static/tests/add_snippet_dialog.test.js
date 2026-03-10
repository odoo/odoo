import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    confirmAddSnippet,
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
