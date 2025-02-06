import { expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { splitBlock } from "../_helpers/user_actions";
import { getContent } from "../_helpers/selection";

test("should replace splitElementBlock with insertLineBreak (selection start)", async () => {
    await testEditor({
        contentBefore: `<div class="oe_unbreakable">[]ab</div>`,
        stepFunction: splitBlock,
        contentAfter: `<div class="oe_unbreakable"><br>[]ab</div>`,
    });
});
test("should replace splitElementBlock with insertLineBreak (selection between)", async () => {
    await testEditor({
        contentBefore: `<div class="oe_unbreakable">a[]b</div>`,
        stepFunction: splitBlock,
        contentAfter: `<div class="oe_unbreakable">a<br>[]b</div>`,
    });
});
test("should replace splitElementBlock with insertLineBreak (selection end)", async () => {
    await testEditor({
        contentBefore: `<div class="oe_unbreakable">ab[]</div>`,
        stepFunction: splitBlock,
        contentAfter: `<div class="oe_unbreakable">ab<br>[]<br></div>`,
    });
});
test("should not split a contenteditable='false'", async () => {
    const { editor, el } = await setupEditor(`<p contenteditable="false">ab</p>`);
    const p = el.querySelector("p");
    editor.shared.split.splitBlockNode({ targetNode: p, targetOffset: 0 });
    expect(getContent(el)).toBe(`<p contenteditable="false">ab</p>`);
});
test("should split an explicit contenteditable='true' if its ancestor isContentEditable", async () => {
    await testEditor({
        contentBefore: `<p contenteditable="true">ab[]</p>`,
        stepFunction: splitBlock,
        contentAfter: `<p contenteditable="true">ab</p><p contenteditable="true">[]<br></p>`,
    });
});
test("should insert a newline instead of splitting an explicit contenteditable='true' if its ancestor is not contentEditable", async () => {
    await testEditor({
        contentBefore: `<div contenteditable="false"><p contenteditable="true">ab[]</p></div>`,
        stepFunction: splitBlock,
        contentAfter: `<div contenteditable="false"><p contenteditable="true">ab<br>[]<br></p></div>`,
    });
});
