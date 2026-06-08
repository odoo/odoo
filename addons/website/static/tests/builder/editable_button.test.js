import { expect, press, test } from "@odoo/hoot";
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
