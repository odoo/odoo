import { test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";

test("should not remove an unremovable element on CTRL+DELETE", async () => {
    await testEditor({
        contentBefore: unformat(`
            <p class="oe_unremovable">[]<br></p>
            <p>abc</p>`),
        stepFunction: () => press(["Ctrl", "Delete"]),
        contentAfter: unformat(`
            <p class="oe_unremovable">[]<br></p>
            <p>abc</p>`),
    });
});

test("should not merge an unbreakable element on CTRL+DELETE", async () => {
    await testEditor({
        contentBefore: unformat(`
            <div class="oe_unbreakable">abc[]</div>
            <p>def</p>`),
        stepFunction: () => press(["Ctrl", "Delete"]),
        contentAfter: unformat(`
            <div class="oe_unbreakable">abc[]</div>
            <p>def</p>`),
    });
});

test("should not merge an unbreakable element on CTRL+DELETE (2)", async () => {
    await testEditor({
        contentBefore: unformat(`
            <p>abc[]</p>
            <div class="oe_unbreakable">def</div>`),
        stepFunction: () => press(["Ctrl", "Delete"]),
        contentAfter: unformat(`
            <p>abc[]</p>
            <div class="oe_unbreakable">def</div>`),
    });
});
