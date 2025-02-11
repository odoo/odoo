import { test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";

const ctrlShiftDelete = () => press(["Ctrl", "Shift", "Delete"]);

test("should do nothing on ctrl+shift+delete", async () => {
    await testEditor({
        contentBefore: "<p>[]<br></p>",
        stepFunction: ctrlShiftDelete,
        contentAfter: "<p>[]<br></p>",
    });
});
test("should delete to end of paragraph with ctrl+shift+delete", async () => {
    await testEditor({
        contentBefore: "<p>[]abc def</p>",
        stepFunction: ctrlShiftDelete,
        contentAfter: "<p>[]<br></p>",
    });
});

test("should delete to end of paragraph with ctrl+shift+delete (2)", async () => {
    await testEditor({
        contentBefore: "<p>abc []def ghi</p>",
        stepFunction: ctrlShiftDelete,
        contentAfter: "<p>abc&nbsp;[]</p>",
    });
});

test("should delete to end of paragraph with ctrl+shift+delete (3)", async () => {
    await testEditor({
        contentBefore: "<p>[]abc def</p><p>second paragraph</p>",
        stepFunction: ctrlShiftDelete,
        contentAfter: "<p>[]<br></p><p>second paragraph</p>",
    });
});

test("should delete text between line-break and cursor", async () => {
    await testEditor({
        contentBefore: "<p>abc[] def ghi<br>text</p>",
        stepFunction: ctrlShiftDelete,
        contentAfter: "<p>abc[]<br>text</p>",
    });
});

test("should delete text between line-break and cursor (2)", async () => {
    await testEditor({
        contentBefore: "<p>[]abc def ghi<br>text</p>",
        stepFunction: ctrlShiftDelete,
        contentAfter: "<p>[]<br>text</p>",
    });
});

test("should delete text between cursor and next line-break", async () => {
    await testEditor({
        contentBefore: "<p>abc[] def ghi<br>text<br>more text</p>",
        stepFunction: ctrlShiftDelete,
        contentAfter: "<p>abc[]<br>text<br>more text</p>",
    });
});

test("should not remove an unremovable element on CTRL+SHIFT+DELETE", async () => {
    await testEditor({
        contentBefore: unformat(`
            <p class="oe_unremovable">[]<br></p>
            <p>abc</p>`),
        stepFunction: ctrlShiftDelete,
        contentAfter: unformat(`
            <p class="oe_unremovable">[]<br></p>
            <p>abc</p>`),
    });
});

test("should not merge an unbreakable element on CTRL+SHIFT+DELETE", async () => {
    await testEditor({
        contentBefore: unformat(`
            <div class="oe_unbreakable">abc[]</div>
            <p>def</p>`),
        stepFunction: ctrlShiftDelete,
        contentAfter: unformat(`
            <div class="oe_unbreakable">abc[]</div>
            <p>def</p>`),
    });
});

test("should not merge an unbreakable element on CTRL+SHIFT+DELETE (2)", async () => {
    await testEditor({
        contentBefore: unformat(`
            <p>abc[]</p>
            <div class="oe_unbreakable">def</div>`),
        stepFunction: ctrlShiftDelete,
        contentAfter: unformat(`
            <p>abc[]</p>
            <div class="oe_unbreakable">def</div>`),
    });
});
