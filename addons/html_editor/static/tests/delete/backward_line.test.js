import { test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";

const ctrlShiftBackspace = () => press(["Ctrl", "Shift", "Backspace"]);

test("should do nothing on ctrl+shift+backspace", async () => {
    await testEditor({
        contentBefore: "<p>[]<br></p>",
        stepFunction: ctrlShiftBackspace,
        contentAfter: "<p>[]<br></p>",
    });
});
test("should delete to start of paragraph with ctrl+shift+backspace", async () => {
    await testEditor({
        contentBefore: "<p>abc def[]</p>",
        stepFunction: ctrlShiftBackspace,
        contentAfter: "<p>[]<br></p>",
    });
});

test("should delete to start of paragraph with ctrl+shift+backspace (2)", async () => {
    await testEditor({
        contentBefore: "<p>abc def[] ghi</p>",
        stepFunction: ctrlShiftBackspace,
        contentAfter: "<p>[]&nbsp;ghi</p>",
    });
});

test.tags("focus required");
test("should delete to start of paragraph with ctrl+shift+backspace (3)", async () => {
    await testEditor({
        contentBefore: "<p>first paragraph</p><p>abc def[]</p>",
        stepFunction: ctrlShiftBackspace,
        contentAfter: "<p>first paragraph</p><p>[]<br></p>",
    });
});

test("should delete text between line-break and cursor", async () => {
    await testEditor({
        contentBefore: "<p>text<br>abc def []ghi</p>",
        stepFunction: ctrlShiftBackspace,
        contentAfter: "<p>text<br>[]ghi</p>",
    });
});

test("should delete text between line-break and cursor (2)", async () => {
    await testEditor({
        contentBefore: "<p>text<br>abc def ghi[]</p>",
        stepFunction: ctrlShiftBackspace,
        contentAfter: "<p>text<br>[]<br></p>",
    });
});

test("should delete text between cursor and previous line-break", async () => {
    await testEditor({
        contentBefore: "<p>text<br>more text<br>abc def []ghi</p>",
        stepFunction: ctrlShiftBackspace,
        contentAfter: "<p>text<br>more text<br>[]ghi</p>",
    });
});

test("should not remove an unremovable element on CTRL+SHIFT+BACKSPACE", async () => {
    await testEditor({
        contentBefore: unformat(`
            <p>abc</p>
            <p class="oe_unremovable">[]<br></p>`),
        stepFunction: ctrlShiftBackspace,
        contentAfter: unformat(`
            <p>abc</p>
            <p class="oe_unremovable">[]<br></p>`),
    });
});

test("should not merge an unbreakable element on CTRL+SHIFT+BACKSPACE", async () => {
    await testEditor({
        contentBefore: unformat(`
            <div class="oe_unbreakable">abc</div>
            <p>[]def</p>`),
        stepFunction: ctrlShiftBackspace,
        contentAfter: unformat(`
            <div class="oe_unbreakable">abc</div>
            <p>[]def</p>`),
    });
});

test("should not merge an unbreakable element on CTRL+SHIFT+BACKSPACE (2)", async () => {
    await testEditor({
        contentBefore: unformat(`
            <p>abc</p>
            <div class="oe_unbreakable">[]def</div>`),
        stepFunction: ctrlShiftBackspace,
        contentAfter: unformat(`
            <p>abc</p>
            <div class="oe_unbreakable">[]def</div>`),
    });
});
