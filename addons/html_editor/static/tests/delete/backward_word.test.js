import { test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { mockUserAgent } from "@odoo/hoot-mock";

// CTRL+BACKSPACE
test("should not remove the last p with ctrl+backspace", async () => {
    await testEditor({
        contentBefore: unformat(`<p>[]<br></p>`),
        stepFunction: () => press(["Ctrl", "Backspace"]),
        contentAfter: unformat(`<p>[]<br></p>`),
    });
});

test("should not remove the last p enclosed in a contenteditable=false with ctrl+backspace", async () => {
    await testEditor({
        contentBefore: unformat(`
                <p>text</p>
                <div contenteditable="false"><div contenteditable="true">
                    <p>[]<br></p>
                </div></div>`),
        stepFunction: () => press(["Ctrl", "Backspace"]),
        contentAfter: unformat(`
                <p>text</p>
                <div contenteditable="false"><div contenteditable="true">
                    <p>[]<br></p>
                </div></div>`),
    });
});

test("should add a <p><br></p> element when deleting the last child of the editable with ctrl+backspace", async () => {
    await testEditor({
        contentBefore: unformat(`
                <blockquote>
                    []<br>
                </blockquote>`),
        stepFunction: () => press(["Ctrl", "Backspace"]),
        contentAfter: unformat(`<p>[]<br></p>`),
    });
});

test("should add a <p><br></p> element when deleting the last child of an element with ctrl+backspace", async () => {
    await testEditor({
        contentBefore: unformat(`
                <div contenteditable="false"><div contenteditable="true">
                    <blockquote>
                        []<br>
                    </blockquote>
                </div></div>`),
        stepFunction: () => press(["Ctrl", "Backspace"]),
        contentAfter: unformat(`
                <div contenteditable="false"><div contenteditable="true">
                    <p>[]<br></p>
                </div></div>`),
    });
});

test("should not remove an unremovable element on CTRL+BACKSPACE", async () => {
    await testEditor({
        contentBefore: unformat(`
                <div contenteditable="false"><div contenteditable="true">
                    <blockquote class="oe_unremovable">
                        []<br>
                    </blockquote>
                </div></div>`),
        stepFunction: () => press(["Ctrl", "Backspace"]),
        contentAfter: unformat(`
                <div contenteditable="false"><div contenteditable="true">
                    <blockquote class="oe_unremovable">
                        []<br>
                    </blockquote>
                </div></div>`),
    });
});

test("should not remove an unremovable element on CTRL+BACKSPACE (2)", async () => {
    await testEditor({
        contentBefore: unformat(`
            <p>abc</p>
            <p class="oe_unremovable">[]<br></p>`),
        stepFunction: () => press(["Ctrl", "Backspace"]),
        contentAfter: unformat(`
            <p>abc</p>
            <p class="oe_unremovable">[]<br></p>`),
    });
});

test("should not merge an unbreakable element on CTRL+BACKSPACE", async () => {
    await testEditor({
        contentBefore: unformat(`
            <div class="oe_unbreakable">abc</div>
            <p>[]def</p>`),
        stepFunction: () => press(["Ctrl", "Backspace"]),
        contentAfter: unformat(`
            <div class="oe_unbreakable">abc</div>
            <p>[]def</p>`),
    });
});

test("should not merge an unbreakable element on CTRL+BACKSPACE (2)", async () => {
    await testEditor({
        contentBefore: unformat(`
            <p>abc</p>
            <div class="oe_unbreakable">[]def</div>`),
        stepFunction: () => press(["Ctrl", "Backspace"]),
        contentAfter: unformat(`
            <p>abc</p>
            <div class="oe_unbreakable">[]def</div>`),
    });
});

test("Should delete last word on MacOS", async () => {
    mockUserAgent("mac");
    await testEditor({
        contentBefore: `<p>hello world[]</p>`,
        stepFunction: () => press(["Alt", "Backspace"]),
        contentAfter: `<p>hello&nbsp;[]</p>`,
    });
});
