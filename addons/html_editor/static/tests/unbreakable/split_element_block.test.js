import { test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { splitBlock } from "../_helpers/user_actions";

test("should replace splitElementBlock with insertLineBreak (selection start)", async () => {
    await testEditor({
        contentBefore: `<div>[]ab</div>`,
        stepFunction: splitBlock,
        contentAfter: `<div><br>[]ab</div>`,
    });
});
test("should replace splitElementBlock with insertLineBreak (selection between)", async () => {
    await testEditor({
        contentBefore: `<div>a[]b</div>`,
        stepFunction: splitBlock,
        contentAfter: `<div>a<br>[]b</div>`,
    });
});
test("should replace splitElementBlock with insertLineBreak (selection end)", async () => {
    await testEditor({
        contentBefore: `<div>ab[]</div>`,
        stepFunction: splitBlock,
        contentAfter: `<div>ab<br>[]<br></div>`,
    });
});
