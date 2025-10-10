import { expect, test } from "@odoo/hoot";
import { testEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { press, tick } from "@odoo/hoot-dom";
import { insertText, simulateArrowKeyPress, splitBlock } from "./_helpers/user_actions";
import { getContent } from "./_helpers/selection";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { isTableCell } from "@html_editor/utils/dom_info";
import { PLACEHOLDER } from "./_helpers/selection_placeholder";

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
        contentBeforeEdit: `${PLACEHOLDER()}<div contenteditable="false">a</div><p>b</p>`,
        contentAfter: `<div contenteditable="false">a</div><p>b</p>`,
    });
});

test("a selection placeholder is inserted before a table as first element, and removed on clean", async () => {
    await testEditor({
        contentBefore: `<table><tbody><tr><td>a</td></tr></tbody></table><p>b</p>`,
        contentBeforeEdit: `${PLACEHOLDER()}<table><tbody><tr><td>a</td></tr></tbody></table><p>b</p>`,
        contentAfter: `<table><tbody><tr><td>a</td></tr></tbody></table><p>b</p>`,
    });
});

test("a selection placeholder is inserted after a contenteditable=false as last element, and removed on clean", async () => {
    await testEditor({
        contentBefore: `<p>a</p><div contenteditable="false">b</div>`,
        contentBeforeEdit: `<p>a</p><div contenteditable="false">b</div>${PLACEHOLDER()}`,
        contentAfter: `<p>a</p><div contenteditable="false">b</div>`,
    });
});

test("a selection placeholder is inserted after a table as last element, and removed on clean", async () => {
    await testEditor({
        contentBefore: `<p>a</p><table><tbody><tr><td>b</td></tr></tbody></table>`,
        contentBeforeEdit: `<p>a</p><table><tbody><tr><td>b</td></tr></tbody></table>${PLACEHOLDER()}`,
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
            `${PLACEHOLDER()}
            <table><tbody><tr><td>a</td></tr></tbody></table>
            ${PLACEHOLDER()}
            <table><tbody><tr><td>b</td></tr></tbody></table>
            ${PLACEHOLDER()}`
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
            ${PLACEHOLDER()}
            <table><tbody><tr><td>d</td></tr></tbody></table>
            <p>e</p>`
        ),
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowDown");
            expect(getContent(editor.editable)).toBe(
                unformat(
                    `<p>a</p>
                    <table><tbody><tr><td>b</td></tr></tbody></table>
                    ${PLACEHOLDER({ selected: true })}
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
                    ${PLACEHOLDER()}
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
                    ${PLACEHOLDER({ selected: true })}
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
                    ${PLACEHOLDER()}
                    <table><tbody><tr><td>d</td></tr></tbody></table>
                    <p>e</p>`
                ),
                { message: "Stepped up out of the placeholder." }
            );
        },
        contentAfterEdit: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>
            ${PLACEHOLDER()}
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

test("moving the caret into a selection placeholder shows a horizontal caret", async () => {
    await testEditor({
        contentBefore: unformat(
            `<table><tbody><tr><td>a[]</td></tr></tbody></table>
            <table><tbody><tr><td>b</td></tr></tbody></table>`
        ),
        contentBeforeEdit: unformat(
            `${PLACEHOLDER()}
            <table><tbody><tr><td>a[]</td></tr></tbody></table>
            ${PLACEHOLDER()}
            <table><tbody><tr><td>b</td></tr></tbody></table>
            ${PLACEHOLDER()}`
        ),
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowDown");
        },
        contentAfterEdit: unformat(
            `${PLACEHOLDER()}
            <table><tbody><tr><td>a</td></tr></tbody></table>
            ${PLACEHOLDER({ selected: true })}
            <table><tbody><tr><td>b</td></tr></tbody></table>
            ${PLACEHOLDER()}`
        ),
        contentAfter: unformat(
            `<table><tbody><tr><td>a</td></tr></tbody></table>[]
            <table><tbody><tr><td>b</td></tr></tbody></table>`
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
            ${PLACEHOLDER()}
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
test("moving the caret into a trailing selection placeholder persists it", async () => {
    await testEditor({
        contentBefore: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>`
        ),
        contentBeforeEdit: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b[]</td></tr></tbody></table>
            ${PLACEHOLDER()}`
        ),
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowDown");
            await insertText(editor, "c");
        },
        contentAfterEdit: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b</td></tr></tbody></table>
            <p>c[]</p>`
        ),
        contentAfter: unformat(
            `<p>a</p>
            <table><tbody><tr><td>b</td></tr></tbody></table>
            <p>c[]</p>`
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
            ${PLACEHOLDER()}
            <table><tbody><tr><td>c</td></tr></tbody></table>
            <p>d</p>`
        ),
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowDown");
            expect(getContent(editor.editable)).toBe(
                unformat(
                    `<p>a</p>
                    <table><tbody><tr><td>b</td></tr></tbody></table>
                    ${PLACEHOLDER({ selected: true })}
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
        contentBeforeEdit: makeContent("b[]", PLACEHOLDER()),
        stepFunction: async (editor) => {
            await insertText(editor, "c");
            expect(getContent(editor.editable)).toBe(makeContent("bc[]", PLACEHOLDER()), {
                message: 'The letter "c" was inserted.',
            });
            await pressArrowKey(editor, "ArrowDown");
            await insertText(editor, "d");
            expect(getContent(editor.editable)).toBe(makeContent("bc", "<p>d[]</p>"), {
                message: "The placeholder was persisted.",
            });
            await undo();
            // Equivalent to `PLACEHOLDER({ selected: true })` but with different order of attributes:
            const selectedPlaceholder = `<p data-selection-placeholder="" class="o-horizontal-caret o-we-hint" o-we-hint-text='Type "/" for commands'>[]<br></p>`;
            expect(getContent(editor.editable)).toBe(makeContent("bc", selectedPlaceholder), {
                message: "Undo un-persisted the placeholder.",
            });
            await redo();
            expect(getContent(editor.editable)).toBe(makeContent("bc", "<p>d[]</p>"), {
                message: "Redo re-persisted the placeholder.",
            });
            await undo();
            expect(getContent(editor.editable)).toBe(makeContent("bc", selectedPlaceholder), {
                message: "Undo un-persisted the placeholder again.",
            });
            await undo();
            expect(getContent(editor.editable)).toBe(makeContent("b[]", PLACEHOLDER()), {
                message: 'Undo removed the letter "c".',
            });
            await undo();
            expect(getContent(editor.editable)).toBe(makeContent("b[]", PLACEHOLDER()), {
                message: "Undo did nothing.",
            });
        },
        contentAfter: makeContent("b[]"),
    });
});

test("a selection placeholder is restored after deletion from within", async () => {
    await testEditor({
        contentBefore: `<table><tbody><tr><td>[]a</td></tr></tbody></table>`,
        contentBeforeEdit: unformat(
            `${PLACEHOLDER()}
            <table><tbody><tr><td>[]a</td></tr></tbody></table>
            ${PLACEHOLDER()}`
        ),
        stepFunction: async (editor) => {
            await pressArrowKey(editor, "ArrowUp");
            expect(getContent(editor.editable)).toBe(
                unformat(
                    `${PLACEHOLDER({ selected: true })}
                    <table><tbody><tr><td>a</td></tr></tbody></table>
                    ${PLACEHOLDER()}`
                ),
                { message: "The top placeholder was selected." }
            );
            await press("Delete");
            await tick();
        },
        contentAfterEdit: unformat(
            `${PLACEHOLDER()}
            <table><tbody><tr><td>[]a</td></tr></tbody></table>
            ${PLACEHOLDER()}`
        ),
        contentAfter: `<table><tbody><tr><td>[]a</td></tr></tbody></table>`,
    });
});

test("a selection placeholder is restored after deletion from without", async () => {
    await testEditor({
        contentBefore: `<table><tbody><tr><td>[]a</td></tr></tbody></table>`,
        contentBeforeEdit: unformat(
            `${PLACEHOLDER()}
            <table><tbody><tr><td>[]a</td></tr></tbody></table>
            ${PLACEHOLDER()}`
        ),
        stepFunction: async (editor) => {
            await press("Backspace");
            await tick();
        },
        contentAfterEdit: unformat(
            `${PLACEHOLDER()}
            <table><tbody><tr><td>[]a</td></tr></tbody></table>
            ${PLACEHOLDER()}`
        ),
        contentAfter: `<table><tbody><tr><td>[]a</td></tr></tbody></table>`,
    });
});
