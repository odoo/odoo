import { expect, test } from "@odoo/hoot";
import { testEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { animationFrame, press, tick } from "@odoo/hoot-dom";
import { insertText, simulateArrowKeyPress, splitBlock } from "./_helpers/user_actions";
import { getContent } from "./_helpers/selection";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { isTableCell } from "@html_editor/utils/dom_info";
import { parseHTML } from "@html_editor/utils/html";

const pressArrowKey = async (editor, key) => {
    const selection = editor.shared.selection.getSelectionData().deepEditableSelection;
    if (
        !key.includes("Shift") &&
        selection.isCollapsed &&
        closestElement(selection.anchorNode, isTableCell)
    ) {
        // Since the selection is in a table, the table plugin handles the
        // arrow key so we use `press` instead of `simulateArrowKeyPress`
        // (which would then change the selection twice).
        // TODO: detect this without relying on implementation if possible.
        await press(key);
    } else {
        await simulateArrowKeyPress(editor, key);
        // Wait an extra tick in case of selection in root correction, so the
        // extra selectionchange event is triggered.
        await tick();
    }
    // Wait for selectionchange event.
    await tick();
};

test("a selection placeholder is inserted before a contenteditable=false as first element, and removed on clean", async () => {
    await testEditor({
        contentBefore: `<div contenteditable="false">a</div><p>b</p>`,
        contentBeforeEdit: `<p data-selection-placeholder=""><br></p><div contenteditable="false">a</div><p>b</p>`,
        contentAfter: `<div contenteditable="false">a</div><p>b</p>`,
    });
});

test("a selection placeholder is inserted before a table as first element, and removed on clean", async () => {
    await testEditor({
        contentBefore: `<table><tbody><tr><td>a</td></tr></tbody></table><p>b</p>`,
        contentBeforeEdit: `<p data-selection-placeholder=""><br></p><table><tbody><tr><td>a</td></tr></tbody></table><p>b</p>`,
        contentAfter: `<table><tbody><tr><td>a</td></tr></tbody></table><p>b</p>`,
    });
});

test("a selection placeholder is inserted after a contenteditable=false as last element, and removed on clean", async () => {
    await testEditor({
        contentBefore: `<p>a</p><div contenteditable="false">b</div>`,
        contentBeforeEdit: `<p>a</p><div contenteditable="false">b</div><p data-selection-placeholder=""><br></p>`,
        contentAfter: `<p>a</p><div contenteditable="false">b</div>`,
    });
});

test("a selection placeholder is inserted after a table as last element, and removed on clean", async () => {
    await testEditor({
        contentBefore: `<p>a</p><table><tbody><tr><td>b</td></tr></tbody></table>`,
        contentBeforeEdit: `<p>a</p><table><tbody><tr><td>b</td></tr></tbody></table><p data-selection-placeholder=""><br></p>`,
        contentAfter: `<p>a</p><table><tbody><tr><td>b</td></tr></tbody></table>`,
    });
});

test("a selection placeholder is inserted between two tables, and removed on clean", async () => {
    await testEditor({
        contentBefore: unformat(
            `<table><tbody><tr><td>a</td></tr></tbody></table>
            <table><tbody><tr><td>b</td></tr></tbody></table>`
        ),
        contentBeforeEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <table><tbody><tr><td>a</td></tr></tbody></table>
            <p data-selection-placeholder=""><br></p>
            <table><tbody><tr><td>b</td></tr></tbody></table>
            <p data-selection-placeholder=""><br></p>`
        ),
        contentAfter: unformat(
            `<table><tbody><tr><td>a</td></tr></tbody></table>
            <table><tbody><tr><td>b</td></tr></tbody></table>`
        ),
    });
});

test.tags("focus required");
test("can navigate in and out of selection placeholders", async () => {
    await testEditor({
        contentBefore: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>
            <table><tbody><tr><td>d</td></tr></tbody></table>
            <p>e</p>`
        ),
        contentBeforeEdit: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>
            <p data-selection-placeholder=""><br></p>
            <table><tbody><tr><td>d</td></tr></tbody></table>
            <p>e</p>`
        ),
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowDown");
            expect(getContent(editor.editable)).toBe(
                unformat(
                    `<p>a</p>
                    <table><tbody><tr><td>b</td></tr></tbody></table>
                    <p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>
                    <table><tbody><tr><td>d</td></tr></tbody></table>
                    <p>e</p>`
                ),
                { message: "Stepped down into the placeholder." }
            );
            await pressArrowKey(editor, "ArrowRight");
            expect(getContent(editor.editable)).toBe(
                unformat(
                    `<p>a</p>
                    <table><tbody><tr><td>b</td></tr></tbody></table>
                    <p data-selection-placeholder=""><br></p>
                    <table><tbody><tr><td>[]d</td></tr></tbody></table>
                    <p>e</p>`
                ),
                { message: "Stepped down out of the placeholder." }
            );
            await pressArrowKey(editor, "ArrowUp");
            expect(getContent(editor.editable)).toBe(
                unformat(
                    `<p>a</p>
                    <table><tbody><tr><td>b</td></tr></tbody></table>
                    <p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>
                    <table><tbody><tr><td>d</td></tr></tbody></table>
                    <p>e</p>`
                ),
                { message: "Stepped up into the placeholder." }
            );
            await pressArrowKey(editor, "ArrowLeft");
            expect(getContent(editor.editable)).toBe(
                unformat(
                    `<p>a</p>
                    <table><tbody><tr><td>b[]</td></tr></tbody></table>
                    <p data-selection-placeholder=""><br></p>
                    <table><tbody><tr><td>d</td></tr></tbody></table>
                    <p>e</p>`
                ),
                { message: "Stepped up out of the placeholder." }
            );
        },
        contentAfterEdit: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>
            <p data-selection-placeholder=""><br></p>
            <table><tbody><tr><td>d</td></tr></tbody></table>
            <p>e</p>`
        ),
        contentAfter: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>
            <table><tbody><tr><td>d</td></tr></tbody></table>
            <p>e</p>`
        ),
    });
});

test.tags("focus required");
test("moving the caret into a selection placeholder shows a horizontal caret", async () => {
    const focusedResult = unformat(
        `<p data-selection-placeholder=""><br></p>
        <table><tbody><tr><td>a</td></tr></tbody></table>
        <p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>
        <table><tbody><tr><td><textarea></textarea></td></tr></tbody></table>
        <p data-selection-placeholder=""><br></p>`
    );
    await testEditor({
        contentBefore: unformat(
            `<table><tbody><tr><td>a[]</td></tr></tbody></table>
            <table><tbody><tr><td><textarea></textarea></td></tr></tbody></table>`
        ),
        contentBeforeEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <table><tbody><tr><td>a[]</td></tr></tbody></table>
            <p data-selection-placeholder=""><br></p>
            <table><tbody><tr><td><textarea></textarea></td></tr></tbody></table>
            <p data-selection-placeholder=""><br></p>`
        ),
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowDown");
            expect(getContent(editor.editable)).toBe(focusedResult, {
                message: "The placeholder was selected.",
            });
            // Blur the editable.
            editor.editable.blur();
            await animationFrame();
            expect(getContent(editor.editable)).toBe(
                unformat(
                    `<p data-selection-placeholder=""><br></p>
                    <table><tbody><tr><td>a</td></tr></tbody></table>
                    <p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>
                    <table><tbody><tr><td><textarea></textarea></td></tr></tbody></table>
                    <p data-selection-placeholder=""><br></p>`
                ),
                {
                    message: "The placeholder stopped blinking when taking the focus out.",
                }
            );
            // Focus the editable.
            editor.editable.focus();
            await animationFrame();
            expect(getContent(editor.editable)).toBe(focusedResult, {
                message: "The placeholder started blinking again when taking the focus back in.",
            });
            // Focus the textarea, blurring the editable.
            editor.editable.querySelector("textarea").focus();
            await animationFrame();
            expect(getContent(editor.editable)).toBe(
                unformat(
                    `<p data-selection-placeholder=""><br></p>
                    <table><tbody><tr><td>a</td></tr></tbody></table>
                    <p data-selection-placeholder=""><br></p>
                    <table><tbody><tr><td>[]<textarea></textarea></td></tr></tbody></table>
                    <p data-selection-placeholder=""><br></p>`
                ),
                {
                    message:
                        "The placeholder stopped blinking when taking the focus into the textarea.",
                }
            );
            // Refocus the editable.
            editor.editable.focus();
            await animationFrame();
            // Focus again, it should start blinking again.
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder="" class="o-horizontal-caret o-we-hint" o-we-hint-text='Type "/" for commands'>[]<br></p>
            <table><tbody><tr><td>a</td></tr></tbody></table>
            <p data-selection-placeholder=""><br></p>
            <table><tbody><tr><td><textarea></textarea></td></tr></tbody></table>
            <p data-selection-placeholder=""><br></p>`
        ),
        contentAfter: unformat(
            `[]<table><tbody><tr><td>a</td></tr></tbody></table>
            <table><tbody><tr><td><textarea></textarea></td></tr></tbody></table>`
        ),
    });
});

test.tags("focus required");
test("typing in a selection placeholder persists it", async () => {
    await testEditor({
        contentBefore: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>
            <table><tbody><tr><td>d</td></tr></tbody></table>
            <p>e</p>`
        ),
        contentBeforeEdit: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>
            <p data-selection-placeholder=""><br></p>
            <table><tbody><tr><td>d</td></tr></tbody></table>
            <p>e</p>`
        ),
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowDown");
            await insertText(editor, "c");
        },
        contentAfterEdit: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b</td></tr></tbody></table>
            <p>c[]</p>
            <table><tbody><tr><td>d</td></tr></tbody></table>
            <p>e</p>`
        ),
        contentAfter: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b</td></tr></tbody></table>
            <p>c[]</p>
            <table><tbody><tr><td>d</td></tr></tbody></table>
            <p>e</p>`
        ),
    });
});

test.tags("focus required");
test("moving the caret into a trailing selection placeholder in the root persists it", async () => {
    await testEditor({
        contentBefore: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>`
        ),
        contentBeforeEdit: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>
            <p data-selection-placeholder=""><br></p>`
        ),
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowDown");
            await animationFrame(); // wait for selectionchange
        },
        contentAfterEdit: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b</td></tr></tbody></table>
            <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
        ),
        contentAfter: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b</td></tr></tbody></table>
            <p>[]<br></p>`
        ),
    });
});

test.tags("focus required");
test("moving the caret into a trailing selection placeholder not in the root doesn't persist it", async () => {
    await testEditor({
        contentBefore: unformat(
            `<p>a</p>
            <div contenteditable="true">
                <table><tbody><tr><td>b[]</td></tr></tbody></table>
            </div>
            <p>c</p>`
        ),
        contentBeforeEdit: unformat(
            `<p>a</p>
            <div contenteditable="true">
                <p data-selection-placeholder=""><br></p>
                <table><tbody><tr><td>b[]</td></tr></tbody></table>
                <p data-selection-placeholder=""><br></p>
            </div>
            <p>c</p>`
        ),
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowDown");
            await animationFrame(); // wait for selectionchange
        },
        contentAfterEdit: unformat(
            `<p>a</p>
            <div contenteditable="true">
                <p data-selection-placeholder=""><br></p>
                <table><tbody><tr><td>b</td></tr></tbody></table>
                <p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>
            </div>
            <p>c</p>`
        ),
        contentAfter: unformat(
            `<p>a</p>
            <div contenteditable="true">
                <table><tbody><tr><td>b</td></tr></tbody></table>
                []
            </div>
            <p>c</p>`
        ),
    });
});

test.tags("focus required");
test("enter in a selection placeholder persists it", async () => {
    await testEditor({
        contentBefore: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>
            <table><tbody><tr><td>c</td></tr></tbody></table>
            <p>d</p>`
        ),
        contentBeforeEdit: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>
            <p data-selection-placeholder=""><br></p>
            <table><tbody><tr><td>c</td></tr></tbody></table>
            <p>d</p>`
        ),
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowDown");
            expect(getContent(editor.editable)).toBe(
                unformat(
                    `<p>a</p>
                    <table><tbody><tr><td>b</td></tr></tbody></table>
                    <p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>
                    <table><tbody><tr><td>c</td></tr></tbody></table>
                    <p>d</p>`
                ),
                { message: "The placeholder was selected." }
            );
            splitBlock(editor);
            await tick();
        },
        contentAfterEdit: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b</td></tr></tbody></table>
            <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>
            <table><tbody><tr><td>c</td></tr></tbody></table>
            <p>d</p>`
        ),
        contentAfter: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b</td></tr></tbody></table>
            <p>[]<br></p>
            <table><tbody><tr><td>c</td></tr></tbody></table>
            <p>d</p>`
        ),
    });
});

test.tags("focus required");
test("can undo/redo the persiting of selection placeholders", async () => {
    const makeContent = (inTable = "", placeholder = "") =>
        unformat(
            `<p>a</p>
            <table><tbody><tr><td>${inTable}</td></tr></tbody></table>
            ${placeholder}
            <table><tbody><tr><td>e</td></tr></tbody></table><p>f</p>`
        );
    const [undo, redo] = ["Z", "Y"].map((key) => async () => {
        await press(["Ctrl", key]);
        await tick();
    });
    await testEditor({
        contentBefore: makeContent("b[]"),
        contentBeforeEdit: makeContent("b[]", '<p data-selection-placeholder=""><br></p>'),
        stepFunction: async (editor) => {
            await insertText(editor, "c");
            expect(getContent(editor.editable)).toBe(
                makeContent("bc[]", '<p data-selection-placeholder=""><br></p>'),
                {
                    message: 'The letter "c" was inserted.',
                }
            );
            await pressArrowKey(editor, "ArrowDown");
            await insertText(editor, "d");
            expect(getContent(editor.editable)).toBe(makeContent("bc", "<p>d[]</p>"), {
                message: "The placeholder was persisted.",
            });
            await undo();
            expect(getContent(editor.editable)).toBe(
                makeContent(
                    "bc",
                    `<p data-selection-placeholder="" class="o-horizontal-caret o-we-hint" o-we-hint-text='Type "/" for commands'>[]<br></p>`
                ),
                { message: "Undo un-persisted the placeholder." }
            );
            await redo();
            expect(getContent(editor.editable)).toBe(makeContent("bc", "<p>d[]</p>"), {
                message: "Redo re-persisted the placeholder.",
            });
            await undo();
            expect(getContent(editor.editable)).toBe(
                makeContent(
                    "bc",
                    `<p data-selection-placeholder="" class="o-horizontal-caret o-we-hint" o-we-hint-text='Type "/" for commands'>[]<br></p>`
                ),
                { message: "Undo un-persisted the placeholder again." }
            );
            await undo();
            expect(getContent(editor.editable)).toBe(
                makeContent("b[]", '<p data-selection-placeholder=""><br></p>'),
                {
                    message: 'Undo removed the letter "c".',
                }
            );
            await undo();
            expect(getContent(editor.editable)).toBe(
                makeContent("b[]", '<p data-selection-placeholder=""><br></p>'),
                {
                    message: "Undo did nothing.",
                }
            );
        },
        contentAfter: makeContent("b[]"),
    });
});

test("a selection placeholder is restored after deletion from within", async () => {
    await testEditor({
        contentBefore: `<table><tbody><tr><td>[]a</td></tr></tbody></table>`,
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            `<table><tbody><tr><td>[]a</td></tr></tbody></table>` +
            '<p data-selection-placeholder=""><br></p>',
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowUp");
            expect(getContent(editor.editable)).toBe(
                `<p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>` +
                    `<table><tbody><tr><td>a</td></tr></tbody></table>` +
                    '<p data-selection-placeholder=""><br></p>',
                { message: "The top placeholder was selected." }
            );
            await press("Delete");
            await tick();
        },
        contentAfterEdit: `<p data-selection-placeholder=""><br></p><table><tbody><tr><td>[]a</td></tr></tbody></table><p data-selection-placeholder=""><br></p>`,
        contentAfter: `<table><tbody><tr><td>[]a</td></tr></tbody></table>`,
    });
});

test("a selection placeholder is restored after deletion from without", async () => {
    await testEditor({
        contentBefore: `<table><tbody><tr><td>[]a</td></tr></tbody></table>`,
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            `<table><tbody><tr><td>[]a</td></tr></tbody></table>` +
            '<p data-selection-placeholder=""><br></p>',
        stepFunction: async () => {
            await press("Backspace");
            await tick();
        },
        contentAfterEdit: `<p data-selection-placeholder=""><br></p><table><tbody><tr><td>[]a</td></tr></tbody></table><p data-selection-placeholder=""><br></p>`,
        contentAfter: `<table><tbody><tr><td>[]a</td></tr></tbody></table>`,
    });
});

test("selection placeholders are vertically positioned in the middle between it and its blocker", async () => {
    const style = document.createElement("style");
    await testEditor({
        contentBefore: unformat(
            `<table style="margin: 50px"><tbody><tr><td>a</td></tr></tbody></table>
            <table style="margin: 10px"><tbody><tr><td>[]a</td></tr></tbody></table>`
        ),
        contentBeforeEdit: unformat(
            `<p data-selection-placeholder="" style="margin: 25px 0px -26px;"><br></p>
            <table style="margin: 50px"><tbody><tr><td>a</td></tr></tbody></table>
            <p data-selection-placeholder="" style="margin: -21px 0px 30px;"><br></p>
            <table style="margin: 10px"><tbody><tr><td>[]a</td></tr></tbody></table>
            <p data-selection-placeholder="" style="margin: -6px 0px 5px;"><br></p>`
        ),
        stepFunction: async (editor) => {
            style.innerText = `
                *[contenteditable=true] {
                    border: 1px solid blue;
                }
                table {
                    border: 1px solid green;
                }
                p[data-selection-placeholder] {
                    border-top: 1px solid red;
                }
            `;
            editor.document.head.append(style);
        },
    });
    // Comment this to make it easier to debug visually.
    style.remove();
});

test("selection placeholder margins remain correct when an element gets added", async () => {
    const style = document.createElement("style");
    await testEditor({
        contentBefore: unformat(
            `<table style="margin: 50px"><tbody><tr><td>a</td></tr></tbody></table>
            <table style="margin: 10px"><tbody><tr><td>[]a</td></tr></tbody></table>`
        ),
        stepFunction: async (editor) => {
            style.innerText = `
                *[contenteditable=true] {
                    border: 1px solid blue;
                }
                table {
                    border: 1px solid green;
                }
                p[data-selection-placeholder] {
                    border-top: 1px solid red;
                }
            `;
            editor.document.head.append(style);
            const table = parseHTML(
                editor.document,
                `<table style="margin: 100px"><tbody><tr><td>[]a</td></tr></tbody></table>`
            ).firstChild;
            editor.editable.append(table);
            editor.shared.history.addStep();
            await animationFrame();
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder="" style="margin: 25px 0px -26px;"><br></p>
            <table style="margin: 50px"><tbody><tr><td>a</td></tr></tbody></table>
            <p data-selection-placeholder="" style="margin: -21px 0px 30px;"><br></p>
            <table style="margin: 10px"><tbody><tr><td>[]a</td></tr></tbody></table>
            <p data-selection-placeholder="" style="margin: 55px 0px -46px;"><br></p>
            <table style="margin: 100px"><tbody><tr><td>[]a</td></tr></tbody></table>
            <p data-selection-placeholder="" style="margin: -51px 0px 50px;"><br></p>`
        ),
    });
    // Comment this to make it easier to debug visually.
    style.remove();
});
