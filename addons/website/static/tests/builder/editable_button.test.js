import { expect, press, queryOne, test, waitFor } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { setSelection } from "@html_editor/../tests/_helpers/selection";

defineWebsiteModels();

test("copy in a savable button should not copy branding attributes", async () => {
    const { getEditor } = await setupWebsiteBuilder("", {
        headerContent: `<button data-oe-model="test">a<b>c</b>a<button>`,
    });
    await contains(":iframe [contenteditable=true]").focus();
    const editor = getEditor();
    const textNode = editor.editable.querySelector("b").firstChild;
    expect(textNode.nodeType).toBe(Node.TEXT_NODE);
    setSelection({ anchorNode: textNode, anchorOffset: 0, focusNode: textNode, focusOffset: 1 });
    const clipboardData = new DataTransfer();
    await press(["ctrl", "c"], { dataTransfer: clipboardData });
    expect(clipboardData.getData("text/plain")).toBe("c");
    expect(clipboardData.getData("text/html")).toBe(`<b>c</b>`);
});

test("tool to add a link is not available in <button>", async () => {
    await setupWebsiteBuilder("<button><span>text</span></button>");
    const spanEl = queryOne(":iframe button span");
    setSelection({ anchorNode: spanEl, anchorOffset: 0, focusOffset: spanEl.childNodes.length });
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar .btn[name='link']").toHaveCount(0);
});
