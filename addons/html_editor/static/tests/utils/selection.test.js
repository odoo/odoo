import { DIRECTIONS, nodeSize } from "@html_editor/utils/position";
import {
    ensureFocus,
    getAdjacentCharacter,
    getCursorDirection,
} from "@html_editor/utils/selection";
import { describe, expect, test } from "@odoo/hoot";
import { dispatch } from "@odoo/hoot-dom";
import { insertText, setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { setSelection } from "../_helpers/selection";

describe("ensureFocus", () => {
    // TODO @phoenix: unskipped when ensureFocus is add in the code base
    test.todo(
        "should preserve the focus on the child of this.editable when executing a powerbox command even if it is enclosed in a contenteditable=false",
        async () => {
            await testEditor({
                contentBefore: unformat(`
                <div contenteditable="false"><div contenteditable="true">
                    <p>[]<br></p>
                </div></div>
                <p><br></p>`),
                stepFunction: async (editor) => {
                    const sel = document.getSelection();
                    const element = sel.anchorNode;
                    await dispatch(editor.editable, "keydown", { key: "/" });
                    await insertText(editor, "/");
                    await dispatch(editor.editable, "keyup", { key: "/" });
                    await insertText(editor, "h2");
                    await dispatch(element, "keyup", { key: "2" });
                    await dispatch(editor.editable, "keydown", { key: "Enter" });
                    const activeElement = document.activeElement;
                    editor.shared.selection.setCursorStart(activeElement.lastElementChild);
                    // TODO @phoenix still need it ?
                    // await nextTickFrame();
                },
                contentAfter: unformat(`
                <div contenteditable="false"><div contenteditable="true">
                    <h2>[]<br></h2>
                </div></div>
                <p><br></p>`),
            });
        }
    );

    test.todo(
        "should preserve the focus on the child of this.editable even if it is enclosed in a contenteditable=false",
        async () => {
            await testEditor({
                contentBefore: unformat(`
                <div contenteditable="false"><div contenteditable="true">
                    <p>[]<br></p>
                </div></div>
                <p><br></p>`),
                stepFunction: async (editor) => {
                    ensureFocus(editor.editable);
                    // TODO @phoenix still need it ?
                    // await nextTickFrame();
                    let activeElement = document.activeElement;
                    editor.shared.selection.setCursorStart(activeElement.lastElementChild);
                    await insertText(editor, "focusWasConserved");
                    // Proof that a simple call to Element.focus would change
                    // the focus in this case.
                    editor.editable.focus();
                    // TODO @phoenix still need it ?
                    // await nextTickFrame();
                    activeElement = document.activeElement;
                    editor.shared.selection.setCursorStart(activeElement.lastElementChild);
                    // TODO @phoenix still need it ?
                    // await nextTickFrame();
                },
                contentAfter: unformat(`
                <div contenteditable="false"><div contenteditable="true">
                    <p>focusWasConserved</p>
                </div></div>
                <p>[]<br></p>`),
            });
        }
    );

    test.todo(
        "should update the focus when the active element is not the focus target",
        async () => {
            await testEditor({
                contentBefore: unformat(`
                <div contenteditable="false"><div contenteditable="true">
                    <p>[]<br></p>
                </div></div>
                <div contenteditable="false"><div id="target" contenteditable="true">
                    <p><br></p>
                </div></div>`),
                stepFunction: async (editor) => {
                    const element = editor.editable.querySelector("#target");
                    ensureFocus(element);
                    // TODO @phoenix still need it ?
                    // await nextTickFrame();
                    const activeElement = document.activeElement;
                    editor.shared.selection.setCursorStart(activeElement.lastElementChild);
                    // TODO @phoenix still need it ?
                    // await nextTickFrame();
                },
                contentAfter: unformat(`
                <div contenteditable="false"><div contenteditable="true">
                    <p><br></p>
                </div></div>
                <div contenteditable="false"><div id="target" contenteditable="true">
                    <p>[]<br></p>
                </div></div>`),
            });
        }
    );
});

describe("getCursorDirection", () => {
    test("should identify a forward selection", async () => {
        await testEditor({
            contentBefore: "<p>a[bc]d</p>",
            stepFunction: (editor) => {
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    editor.document.getSelection();
                expect(getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset)).toBe(
                    DIRECTIONS.RIGHT
                );
            },
        });
    });

    test("should identify a backward selection", async () => {
        await testEditor({
            contentBefore: "<p>a]bc[d</p>",
            stepFunction: (editor) => {
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    editor.document.getSelection();
                expect(getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset)).toBe(
                    DIRECTIONS.LEFT
                );
            },
        });
    });

    test("should identify a collapsed selection", async () => {
        await testEditor({
            contentBefore: "<p>ab[]cd</p>",
            stepFunction: (editor) => {
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    editor.document.getSelection();
                expect(getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset)).toBe(
                    false
                );
            },
        });
    });
});

describe("getAdjacentCharacter", () => {
    test("should return the ZWS character before the cursor", async () => {
        const { editor, el } = await setupEditor("<p><span>abc</span>\u200b</p>");
        const p = el.firstChild;
        // Place the cursor at the end of the P (not in a leaf node)
        setSelection({ anchorNode: p, anchorOffset: nodeSize(p) });
        const selection = editor.document.getSelection();
        expect(getAdjacentCharacter(selection, "previous", el)).toBe("\u200b");
    });
});
