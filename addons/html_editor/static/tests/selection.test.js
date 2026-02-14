import { describe, expect, test } from "@odoo/hoot";
import { isInViewPort, press, queryFirst, queryOne } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { useAutofocus } from "@web/core/utils/hooks";
import { Plugin } from "../src/plugin";
import { MAIN_PLUGINS } from "../src/plugin_sets";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { insertText, tripleClick } from "./_helpers/user_actions";
import { withSequence } from "@html_editor/utils/resource";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { SelectionPlugin } from "@html_editor/core/selection_plugin";

test("getEditableSelection should work, even if getSelection returns null", async () => {
    const { editor } = await setupEditor("<p>a[b]</p>");
    let selection = editor.shared.selection.getEditableSelection();
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);

    // it happens sometimes in firefox that the selection is null
    patchWithCleanup(document, {
        getSelection: () => null,
    });

    selection = editor.shared.selection.getEditableSelection();
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);
});

test("plugins should be notified when ranges are removed", async () => {
    let count = 0;
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            selectionchange_handlers: () => count++,
        };
    }

    const { el } = await setupEditor("<p>a[b]</p>", {
        config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
    });
    const countBefore = count;
    document.getSelection().removeAllRanges();
    await animationFrame();
    expect(count).toBe(countBefore + 1);
    expect(getContent(el)).toBe("<p>ab</p>");
});

test.tags("desktop");
test("triple click outside of the Editor", async () => {
    const { el } = await setupEditor("<p>[]abc</p><p>d</p>", {});
    const anchorNode = el.parentElement;
    await tripleClick(el.parentElement);
    expect(document.getSelection().anchorNode).toBe(anchorNode);
    expect(getContent(el)).toBe("<p>abc</p><p>d</p>");

    const p = el.querySelector("p");
    await tripleClick(p);
    expect(document.getSelection().anchorNode).toBe(p.childNodes[0]);
    expect(getContent(el)).toBe("<p>[abc]</p><p>d</p>");
});

test.tags("desktop");
test("correct selection after triple click with bold", async () => {
    const { el } = await setupEditor("<p>[]abc<strong>d</strong></p><p>efg</p>", {});
    await tripleClick(queryFirst("p").firstChild);
    expect(getContent(el)).toBe("<p>[abc<strong>d]</strong></p><p>efg</p>");
});

test.tags("desktop");
test("selection on triple click should be contained in the paragraph", async () => {
    const { el } = await setupEditor("<div><p>[]abc</p><br><br><h2>def</h2></div>");
    await tripleClick(el.querySelector("p:not([data-selection-placeholder])"));
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            "<div><p>[abc]</p><br><br><h2>def</h2></div>" +
            '<p data-selection-placeholder=""><br></p>'
    );
});

test.tags("desktop");
test("correct selection after triple click in multi-line block (1)", async () => {
    const { el } = await setupEditor("<p>[]abc<br>efg</p>", {});
    await tripleClick(queryFirst("p").firstChild);
    expect(getContent(el)).toBe("<p>[abc<br>efg]</p>");
});

test.tags("desktop");
test("correct selection after triple click in multi-line block (2)", async () => {
    const { el } = await setupEditor("<p>block1</p><p>[]block2<br>block2</p><p>block3</p>", {});
    await tripleClick(queryFirst("p:not([data-selection-placeholder])").nextSibling.firstChild); // we triple click inside block2
    expect(getContent(el)).toBe("<p>block1</p><p>[block2<br>block2]</p><p>block3</p>");
});

test("fix selection P in the beggining being a direct child of the editable p after selection", async () => {
    const { el } = await setupEditor("<div>a</div>[]<p>b</p>");
    expect(getContent(el)).toBe(`<div class="o-paragraph">a</div><p>[]b</p>`);
});
test("fix selection P in the beginning being a direct child of the editable p before selection", async () => {
    const { el } = await setupEditor("<p>a</p>[]<div>b</div>");
    expect(getContent(el)).toBe(`<p>a</p><div class="o-paragraph">[]b</div>`);
});

describe("documentSelectionIsInEditable", () => {
    test("documentSelectionIsInEditable should be true", async () => {
        const { editor } = await setupEditor("<p>a[]b</p>");
        const selectionData = editor.shared.selection.getSelectionData();
        expect(selectionData.documentSelectionIsInEditable).toBe(true);
    });

    test("documentSelectionIsInEditable should be false when it is set outside the editable", async () => {
        const { editor } = await setupEditor("<p>ab</p>");
        const selectionData = editor.shared.selection.getSelectionData();
        expect(selectionData.documentSelectionIsInEditable).toBe(false);
    });

    test("documentSelectionIsInEditable should be false when it is set outside the editable after retrieving it", async () => {
        const { editor } = await setupEditor("<p>ab[]</p>");
        const selection = document.getSelection();
        let selectionData = editor.shared.selection.getSelectionData();
        expect(selectionData.documentSelectionIsInEditable).toBe(true);
        selection.setPosition(document.body);
        // value is updated directly !
        selectionData = editor.shared.selection.getSelectionData();
        expect(selectionData.documentSelectionIsInEditable).toBe(false);
    });
});

test("getSelectionData should validate the offsets of activeSelection", async () => {
    const { editor } = await setupEditor("<p>a[b]</p>");
    let selection = editor.shared.selection.getEditableSelection();
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);

    // We simulate getSelection() returning null while activeSelection has an
    // offset pointing to a deleted element. This is an edge case that occurs in
    // Chrome (see commit message).
    patchWithCleanup(document, {
        getSelection: () => null,
    });
    patchWithCleanup(SelectionPlugin.prototype, {
        getSelectionData() {
            this.activeSelection = { ...this.activeSelection, anchorOffset: 5 };
            return super.getSelectionData();
        },
    });

    selection = editor.shared.selection.getEditableSelection();
    expect(selection.anchorOffset).toBe(0);
});

test("setEditableSelection should not crash if getSelection returns null", async () => {
    const { editor } = await setupEditor("<p>a[b]</p>");
    let selection = editor.shared.selection.getEditableSelection();
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);

    // it happens sometimes in firefox that the selection is null
    patchWithCleanup(document, {
        getSelection: () => null,
    });

    selection = editor.shared.selection.setSelection({
        anchorNode: editor.editable.firstChild,
        anchorOffset: 0,
    });

    // Selection could not be set, so it remains unchanged.
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);
});

test("getSelectionData should use the range of the document selection to set offsets (specifically for safari)", async () => {
    const { editor } = await setupEditor("[]");
    let selection = editor.shared.selection.getEditableSelection();
    expect(selection.startOffset).toBe(0);
    expect(selection.endOffset).toBe(0);

    // Simulate the broken behavior of Safari where getSelection returns a selection
    // with offsets outside of the actual node length, and the range is correct.
    patchWithCleanup(document, {
        getSelection: () => ({
            ...selection,
            anchorOffset: 1,
            focusOffset: 1,
            rangeCount: 1,
            getRangeAt: () => ({
                commonAncestorContainer: selection.anchorNode,
                startContainer: selection.anchorNode,
                endContainer: selection.focusNode,
                startOffset: 0,
                endOffset: 0,
            }),
        }),
    });

    selection = editor.shared.selection.getEditableSelection();
    expect(selection.anchorOffset).toBe(0);
});

test("active selection shouldn't change when document selection is inconsistent with its range", async () => {
    const { editor } = await setupEditor("<p>[]</p>abc");
    let selection = editor.shared.selection.getEditableSelection();
    const originalAnchorNode = selection.anchorNode;
    expect(selection.startOffset).toBe(0);
    expect(selection.endOffset).toBe(0);

    // Simulate a very broken DOM selection with inconsistent anchor/focus nodes
    // comparing its range.
    patchWithCleanup(document, {
        getSelection: () => ({
            ...selection,
            anchorNode: selection.anchorNode.parentNode,
            focusNode: selection.focusNode.parentNode,
            anchorOffset: 0,
            focusOffset: 0,
            rangeCount: 1,
            getRangeAt: () => ({
                commonAncestorContainer: selection.anchorNode,
                startContainer: selection.anchorNode,
                endContainer: selection.focusNode,
                startOffset: 0,
                endOffset: 0,
            }),
        }),
    });

    selection = editor.shared.selection.getEditableSelection();
    expect(selection.anchorNode).toBe(originalAnchorNode);
    expect(selection.anchorOffset).toBe(0);
});

test("modifySelection should not crash if getSelection returns null", async () => {
    const { editor } = await setupEditor("<p>a[b]</p>");
    let selection = editor.shared.selection.getEditableSelection();
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);

    // it happens sometimes in firefox that the selection is null
    patchWithCleanup(document, {
        getSelection: () => null,
    });

    selection = editor.shared.selection.modifySelection("extend", "backward", "word");

    // Selection could not be modified.
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);
});

test("setSelection should not set the selection outside the editable", async () => {
    const { editor, el } = await setupEditor("<p>a[b]</p>");
    editor.document.getSelection().setPosition(document.body);
    await tick();
    const selection = editor.shared.selection.setSelection(
        editor.shared.selection.getEditableSelection()
    );
    expect(el.contains(selection.anchorNode)).toBe(true);
});

test("press 'ctrl+a' in 'oe_structure' child should only select his content", async () => {
    const { el } = await setupEditor(`<div class="oe_structure"><p>a[]b</p><p>cd</p></div>`);
    await press(["ctrl", "a"]);
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            `<div class="oe_structure"><p>[ab]</p><p>cd</p></div>` +
            '<p data-selection-placeholder=""><br></p>'
    );
});

test("press 'ctrl+a' in 'contenteditable' should only select his content", async () => {
    const { el } = await setupEditor(
        `<div contenteditable="false"><p contenteditable="true">a[]b</p><p contenteditable="true">cd</p></div>`
    );
    await press(["ctrl", "a"]);
    expect(getContent(el)).toBe(
        `<p data-selection-placeholder=""><br></p><div contenteditable="false"><p contenteditable="true">[ab]</p><p contenteditable="true">cd</p></div><p data-selection-placeholder=""><br></p>`
    );
});

test.tags("focus required");
test("should focus the nearest editable ancestor when selection is inside a non-editable", async () => {
    const { editor } = await setupEditor(
        `<div contenteditable="false"><p contenteditable="true">[test]</p></div>`
    );
    const p = queryOne('p[contenteditable="true"]');
    expect(p).toBeFocused();

    // Moved focus outside of the editable
    p.blur();
    expect(document.body).toBeFocused();

    editor.shared.selection.focusEditable();
    // Focus should be on the closest editable element of the selection
    expect(p).toBeFocused();
});

test("restore a selection when you are not in the editable shouldn't move the focus", async () => {
    class TestInput extends Component {
        static template = xml`<input t-ref="input" t-att-value="'eee'" class="test"/>`;
        static props = ["*"];

        setup() {
            useAutofocus({ refName: "input", mobile: true });
        }
    }

    class TestPlugin extends Plugin {
        static id = "test";
        static dependencies = ["overlay"];
        resources = {
            user_commands: [
                {
                    id: "testShowOverlay",
                    title: "Test",
                    description: "Test",
                    run: this.showOverlay.bind(this),
                },
            ],
            powerbox_items: [
                {
                    categoryId: "widget",
                    commandId: "testShowOverlay",
                },
            ],
        };

        setup() {
            this.overlay = this.dependencies.overlay.createOverlay(TestInput);
        }

        showOverlay() {
            this.overlay.open({
                props: {},
            });
        }
    }

    const { editor } = await setupEditor("<p>te[]st</p>", {
        config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
    });
    await insertText(editor, "/test");
    await press("enter");
    await animationFrame();
    expect("input.test").toBeFocused();

    // Something trigger restore
    const cursors = editor.shared.selection.preserveSelection();
    cursors.restore();
    expect("input.test").toBeFocused();
});

test("preserveSelection's restore should always set the selection, even if it's the same as the current one", async () => {
    /**
     * There seems to be a bug in Chrome that renders the selection in a
     * different position than the one returned by document.getSelection().
     * Setting the selection (even if it's the same as the current one) seems to
     * solve the issue.
     *
     * A concrete example:
     * <p>abc <a href="#">some link</a> def[]</p>
     *     press shift + enter
     * The selection (in Chrome) is rendered at the following position if
     * setBaseAndExtent is skipped when setting the selection after a restore:
     * <p>abc <a href="#">some link</a>[] def<br><br></p>
     */
    const { editor } = await setupEditor("<p>ab[]cd</p>");
    patchWithCleanup(editor.document.getSelection(), {
        setBaseAndExtent: () => {
            expect.step("setBaseAndExtent");
        },
    });
    const cursors = editor.shared.selection.preserveSelection();
    cursors.restore();
    expect.verifySteps(["setBaseAndExtent"]);
});

describe("getTargetedNodes", () => {
    const nameNodes = (nodes) =>
        nodes.map((node) => (node.nodeType === Node.TEXT_NODE ? node.textContent : node.nodeName));
    describe("single block", () => {
        describe("single text node", () => {
            test("should return the targeted text node (collapsed)", async () => {
                const { editor } = await setupEditor("<p>abc[]def</p>");
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual(["abcdef"]);
            });

            test("should return the targeted text node (collapsed, in a complex DOM)", async () => {
                const { editor } = await setupEditor("<div><p>a[]bc</p><div>def</div></div>");
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual(["abc"]);
            });

            test("should return the targeted text node (partial selection)", async () => {
                const { editor } = await setupEditor("<p>ab[cd]ef</p>");
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual(["abcdef"]);
            });

            test("should return the targeted text node (full selection)", async () => {
                const { editor } = await setupEditor("<p>[abcdef]</p>");
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual(["abcdef"]);
            });

            test("should return the targeted text node before an inline element", async () => {
                const { editor } = await setupEditor(`<p>[ab]<span class="a">cd</span></p>`);
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual(["ab"]);
            });

            test("should return the targeted text node after an inline element", async () => {
                const { editor } = await setupEditor(`<p><span class="a">ab</span>[cd]</p>`);
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual(["cd"]);
            });
        });

        describe("across inline elements", () => {
            test("should include a selected inline element (from its left outer edge)", async () => {
                const { editor } = await setupEditor("<p>ab[<span>cd</span>ef]</p>");
                // "ab" isn't included because no part of it is selected.
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual([
                    "SPAN",
                    "cd",
                    "ef",
                ]);
            });

            test("should include a selected inline element (from its left inner edge)", async () => {
                const { editor } = await setupEditor("<p>ab<span>[cd</span>ef]</p>");
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual([
                    "SPAN",
                    "cd",
                    "ef",
                ]);
            });

            test("should include a selected inline element (until its right outer edge)", async () => {
                const { editor } = await setupEditor("<p>[ab<span>cd</span>]ef</p>");
                // "ef" isn't included because no part of it is selected.
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual([
                    "ab",
                    "SPAN",
                    "cd",
                ]);
            });

            test("should include a selected inline element (until its right inner edge)", async () => {
                const { editor } = await setupEditor("<p>[ab<span>cd]</span>ef</p>");
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual([
                    "ab",
                    "SPAN",
                    "cd",
                ]);
            });
        });
    });
    describe("across blocks", () => {
        describe("basic", () => {
            test("should include intersected blocks", async () => {
                const { el: editable, editor } = await setupEditor("<p>ab[cd</p><p>ef]gh</p>");
                const p1 = editable.firstChild; // The selection crossed `</p>` -> include it.
                const abcd = p1.firstChild;
                const p2 = editable.childNodes[1]; // The selection crossed `<p>` -> include it.
                const efgh = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, abcd, p2, efgh]);
            });

            test("should include intersected blocks, including an empty one", async () => {
                const { el: editable, editor } = await setupEditor("<p>ab[cd</p><p><br>]</p>");
                const p1 = editable.firstChild; // The selection crossed `</p>` -> include it.
                const abcd = p1.firstChild;
                const p2 = editable.childNodes[1]; // The selection crossed `<p>` -> include it.
                const br = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, abcd, p2, br]);
            });

            test("should include intersected blocks (across three blocks)", async () => {
                const { el: editable, editor } = await setupEditor(
                    "<p>[ab</p><p>cd</p><p>ef]gh</p>"
                );
                const p1 = editable.firstChild; // The selection crossed `</p>` -> include it.
                const ab = p1.firstChild;
                const p2 = p1.nextSibling;
                const cd = p2.firstChild;
                const p3 = p2.nextSibling; // The selection crossed `<p>` -> include it.
                const ef = p3.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, p2, cd, p3, ef]);
            });

            test("should include intersected blocks within a common block", async () => {
                const { el: editable, editor } = await setupEditor(
                    "<div><p>a[bc</p><div>d]ef</div></div>"
                );
                const outerDiv = editable.querySelector("div");
                const p1 = outerDiv.firstChild; // The selection crossed `</p>` -> include it.
                const abc = p1.firstChild;
                const innerDiv = p1.nextSibling; // The selection crossed `<div>` -> include it.
                const def = innerDiv.firstChild;
                const result = editor.shared.selection
                    .getTargetedNodes()
                    .filter((node) => !node.hasAttribute?.("data-selection-placeholder"));
                expect(result).toEqual([p1, abc, innerDiv, def]);
            });

            test("should include intersected blocks (complex nested structure)", async () => {
                const { editor } = await setupEditor(
                    "<div><p>a[b</p><h1>cd</h1></div><h2>e]f</h2>"
                );
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual([
                    "DIV",
                    "P",
                    "ab",
                    "H1",
                    "cd",
                    "H2",
                    "ef",
                ]);
            });

            test("should find all targeted nodes in a complex nested structure", async () => {
                const { el: editable, editor } = await setupEditor(
                    `<p><span class="a">ab[</span>cd</p><div><p><span class="b"><b>e</b><i>f]g</i>h</span></p></div>`
                );
                const p1 = editable.firstChild; // The selection crossed `</p>` -> include it.
                const span1 = p1.firstChild; // The selection crossed `</span>` -> include it.
                // "ab" isn't included because no part of it is selected.
                const cd = p1.lastChild;
                const div = editable.querySelector("div");
                const p2 = div.firstChild;
                const span2 = p2.firstChild; // The selection crossed `<span class="b">` -> include it.
                const b = span2.firstChild;
                const e = b.firstChild;
                const i = b.nextSibling; // The selection crossed `<i>` -> include it.
                const fg = i.firstChild;
                const result = editor.shared.selection
                    .getTargetedNodes()
                    .filter((node) => !node.hasAttribute?.("data-selection-placeholder"));
                expect(result).toEqual([p1, span1, cd, div, p2, span2, b, e, i, fg]);
            });
        });
        describe("outwardly selected block", () => {
            test.tags("fails -> to investigate");
            test("should return a fully selected block (from its outer edges) and its contents", async () => {
                const { editor } = await setupEditor("<div>[<p>abc</p>]</div>");
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual(["P", "abc"]);
            });

            test("should return a fully selected empty block (from its outer edges)", async () => {
                const { editor } = await setupEditor("<div>[<p><br></p>]</div>");
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual(["P", "BR"]);
            });

            test("should include two fully selected blocks and their contents (from their outer edges)", async () => {
                const { el: editable, editor } = await setupEditor("[<p>ab</p><p>cd<br></p>]");
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const p2 = editable.lastChild;
                const cd = p2.firstChild;
                const br = p2.lastChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, p2, cd, br]);
            });

            test("should include an outwardly selected block and an intersected block (left outer edge)", async () => {
                const { el: editable, editor } = await setupEditor("[<p>ab<br>cd</p><p>ef]</p>");
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const br = ab.nextSibling;
                const cd = br.nextSibling;
                const p2 = editable.lastChild; // The selection crossed `<p>` -> include it.
                const ef = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, br, cd, p2, ef]);
            });

            test("should include an outwardly selected block and an intersected block (right outer edge)", async () => {
                const { el: editable, editor } = await setupEditor("<p>[ab<br>cd</p><p>ef</p>]");
                const p1 = editable.firstChild; // The selection crossed `</p>` -> include it.
                const ab = p1.firstChild;
                const br = ab.nextSibling;
                const cd = br.nextSibling;
                const p2 = editable.lastChild;
                const ef = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, br, cd, p2, ef]);
            });
        });

        describe("edges and brs", () => {
            test("should include intersected blocks, including an empty one (selection across two blocks, from/to inner right edge)", async () => {
                const { el: editable, editor } = await setupEditor("<p>ab[</p><p>cd]</p>");
                const p1 = editable.childNodes[0]; // The selection crossed `</p>` -> include it.
                // "ab" isn't included because no part of it is selected.
                const p2 = p1.nextSibling; // The selection crossed `<p>` -> include it.
                const cd = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, p2, cd]);
            });

            test("<p>ab[</p><p>cd</p>]", async () => {
                const { el: editable, editor } = await setupEditor("<p>ab[</p><p>cd</p>]");
                const p1 = editable.childNodes[0]; // The selection crossed `</p>` -> include it.
                // "ab" isn't included because no part of it is selected.
                const p2 = p1.nextSibling; // The selection crossed `<p>` -> include it.
                const cd = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, p2, cd]);
            });

            test.tags("former triple-click");
            test("should include intersected blocks, including an empty one (selection across two blocks, from inner right to inner left edge)", async () => {
                const { el: editable, editor } = await setupEditor("<p>abcd[</p><p>]<br></p>");
                const p1 = editable.childNodes[0]; // The selection crossed `</p>` -> include it.
                // "ab" isn't included because no part of it is selected.
                const p2 = p1.nextSibling; // The selection crossed `<p>` -> include it.
                // The BR is not included because the selection ended at (p2,
                // 0), not in the BR.
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, p2]);
            });

            test.tags("former triple-click");
            test("should include the targeted nodes until the beginning of a new block", async () => {
                const { editor } = await setupEditor("<p>ab[cd</p><h1>]efgh</h1>");
                // "efgh" isn't included because no part of it is selected.
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual([
                    "P",
                    "abcd",
                    "H1",
                ]);
            });

            test.tags("former triple-click");
            test("should include the targeted nodes until the beginning of a new block, and an outwardly selected block (1)", async () => {
                const { el: editable, editor } = await setupEditor("[<p>ab</p><p>]cd</p>");
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const p2 = p1.nextSibling; // The selection crossed `<p>` -> include it.
                // "cd" isn't included because no part of it is selected.
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, p2]);
            });

            test.tags("former triple-click");
            test("should include the targeted nodes until the beginning of a new block, and an outwardly selected block (2)", async () => {
                const { el: editable, editor } = await setupEditor("[<p>ab</p><p>]<br>cd<br></p>");
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const p2 = p1.nextSibling; // The selection crossed `<p>` -> include it.
                // The BR is not included because the selection ended at (p2,
                // 0), not in the BR.
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, p2]);
            });

            test.tags("former triple-click");
            test("should include the targeted nodes until the beginning of a new block, and an outwardly selected block (3)", async () => {
                const { el: editable, editor } = await setupEditor("[<p>ab</p><p>]<br></p>");
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const p2 = p1.nextSibling; // The selection crossed `<p>` -> include it.
                // The BR is not included because the selection ended at (p2,
                // 0), not in the BR.
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, p2]);
            });

            test("should not include a non-selected BR just after selection", async () => {
                const { el: editable, editor } = await setupEditor(
                    "[<p>ab</p><p><br>cd]<br>ef<br></p>"
                );
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const p2 = editable.lastChild; // The selection crossed `<p>` -> include it.
                const firstBr = p2.firstChild;
                const cd = firstBr.nextSibling;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, p2, firstBr, cd]);
            });

            test("should not include a non-selected BR just before selection", async () => {
                const { el: editable, editor } = await setupEditor("<p>ab<br>[cd</p><p>ef</p>]");
                const p1 = editable.firstChild; // The selection crossed `</p>` -> include it.
                const ab = p1.firstChild;
                const br = ab.nextSibling;
                const cd = br.nextSibling;
                const p2 = editable.lastChild;
                const ef = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, cd, p2, ef]);
            });

            test("should not include a non-selected BR just before selection (from outer right edge)", async () => {
                const { el: editable, editor } = await setupEditor("<p>ab<br>[</p><p>cd</p>]");
                const p1 = editable.firstChild;
                const p2 = editable.lastChild;
                const cd = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, p2, cd]);
            });

            test("should include a selected BR just at the end of selection", async () => {
                const { el: editable, editor } = await setupEditor(
                    "[<p>ab</p><p><br>cd<br>]ef<br></p>"
                );
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const p2 = editable.lastChild; // The selection crossed `<p>` -> include it.
                const br1 = p2.firstChild;
                const cd = br1.nextSibling;
                const br2 = cd.nextSibling;
                // "ef" isn't included because no part of it is selected.
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, p2, br1, cd, br2]);
            });

            test("should include a selected BR just at the beginning of selection", async () => {
                const { el: editable, editor } = await setupEditor("<p>ab[<br>cd</p><p>ef</p>]");
                const p1 = editable.firstChild; // The selection crossed `</p>` -> include it.
                // "ab" isn't included because no part of it is selected.
                const br = p1.childNodes[1];
                const cd = br.nextSibling;
                const p2 = editable.lastChild;
                const ef = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, br, cd, p2, ef]);
            });

            test("should include a selected BR just at the end of selection and of block", async () => {
                const { el: editable, editor } = await setupEditor("[<p>ab</p><p><br>cd<br>]</p>");
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const p2 = editable.lastChild; // The selection crossed `<p>` -> include it.
                const br1 = p2.firstChild;
                const cd = br1.nextSibling;
                const br2 = cd.nextSibling;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, p2, br1, cd, br2]);
            });

            test("should include a selected BR just at the end of selection but not its non-selected BR sibling", async () => {
                const { el: editable, editor } = await setupEditor(
                    "[<p>ab</p><p>cd<br>]<br>ef</p>"
                );
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const p2 = editable.firstChild.nextSibling; // The selection crossed `<p>` -> include it.
                const cd = p2.firstChild;
                const br1 = cd.nextSibling;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, p2, cd, br1]);
            });

            test("should include a selected BR just at the beginning of selection but not its non-selected BR sibling", async () => {
                const { el: editable, editor } = await setupEditor(
                    "<p>ab<br>[<br>cd</p><p>ef</p>]"
                );
                const p1 = editable.firstChild; // The selection crossed `</p>` -> include it.
                const ab = p1.firstChild;
                const br1 = ab.nextSibling;
                const br2 = br1.nextSibling;
                const cd = br2.nextSibling;
                const p2 = editable.firstChild.nextSibling;
                const ef = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, br2, cd, p2, ef]);
            });
        });

        test("should return an image in a parent selection", async () => {
            const { editor } = await setupEditor(`<div id="parent-element-to-select"><img></div>`);
            const sel = editor.document.getSelection();
            const range = editor.document.createRange();
            const parent = editor.document.querySelector("div#parent-element-to-select");
            // `<div id="parent-element-to-select">[<img>]</div>`:
            range.setStart(parent, 0);
            range.setEnd(parent, 1);
            sel.removeAllRanges();
            sel.addRange(range);
            expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual(["IMG"]);
        });

        describe("in tables", () => {
            test("should return the targeted nodes across two adjacent table cells", async () => {
                const { el: editable, editor } = await setupEditor(
                    "<table><tbody><tr><td>abcd[e</td><td>f]g</td></tr></tbody></table>"
                );
                // The special table selection implies the two table cells are
                // fully marked as selected.
                const td1 = editable.querySelector("td"); // The selection crossed `</td>` -> include it.
                const abcde = td1.firstChild;
                const td2 = td1.nextSibling; // The selection crossed `<td>` -> include it.
                const fg = td2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([td1, abcde, td2, fg]);
            });

            test("should return the targeted nodes across two adjacent table cells, with line breaks", async () => {
                const { el: editable, editor } = await setupEditor(
                    "<table><tbody><tr><td>abcd<br>[<br>e</td><td>f]g</td></tr></tbody></table>"
                );
                // The special table selection implies the two table cells are
                // fully marked as selected.
                const td1 = editable.querySelector("td"); // The selection crossed `</td>` -> include it.
                const abcd = td1.firstChild; // Special table selection -> full TD contents included.
                const br1 = abcd.nextSibling; // Special table selection -> full TD contents included.
                const br2 = br1.nextSibling;
                const e = br2.nextSibling;
                const td2 = td1.nextSibling; // The selection crossed `<td>` -> include it.
                const fg = td2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                // The special table selection makes it so that both TDs are
                // shown as fully selection.
                expect(result).toEqual([td1, abcd, br1, br2, e, td2, fg]);
            });
        });
    });
});

describe("selection setters", () => {
    function getProcessSelection(selection) {
        const { anchorNode, anchorOffset, focusNode, focusOffset } = selection;
        return [anchorNode, anchorOffset, focusNode, focusOffset];
    }

    describe("setSelection", () => {
        describe("collapsed", () => {
            test("should collapse the cursor at the beginning of an element", async () => {
                const { editor, el } = await setupEditor("<p>abc</p>");
                const p = el.firstChild;
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: p.firstChild,
                        anchorOffset: 0,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([p.firstChild, 0, p.firstChild, 0]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([
                    p.firstChild,
                    0,
                    p.firstChild,
                    0,
                ]);
            });

            test("should collapse the cursor within an element", async () => {
                const { editor, el } = await setupEditor("<p>abcd</p>");
                const p = el.firstChild;
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: p.firstChild,
                        anchorOffset: 2,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([p.firstChild, 2, p.firstChild, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([
                    p.firstChild,
                    2,
                    p.firstChild,
                    2,
                ]);
            });

            test("should collapse the cursor at the end of an element", async () => {
                const { editor, el } = await setupEditor("<p>abc</p>");
                const p = el.firstChild;
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: p.firstChild,
                        anchorOffset: 3,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([p.firstChild, 3, p.firstChild, 3]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([
                    p.firstChild,
                    3,
                    p.firstChild,
                    3,
                ]);
            });

            test("should collapse the cursor before a nested inline element", async () => {
                const { editor, el } = await setupEditor("<p>ab<span>cd<b>ef</b>gh</span>ij</p>");
                const p = el.firstChild;
                const cd = p.childNodes[1].firstChild;
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: cd,
                        anchorOffset: 2,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([cd, 2, cd, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([cd, 2, cd, 2]);
            });

            test("should collapse the cursor at the beginning of a nested inline element", async () => {
                const { editor, el } = await setupEditor("<p>ab<span>cd<b>ef</b>gh</span>ij</p>");
                const p = el.firstChild;
                const ef = p.childNodes[1].childNodes[1].firstChild;
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: ef,
                        anchorOffset: 0,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([ef, 0, ef, 0]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([ef, 0, ef, 0]);
            });

            test("should collapse the cursor within a nested inline element", async () => {
                const { editor, el } = await setupEditor("<p>ab<span>cd<b>efgh</b>ij</span>kl</p>");
                const p = el.firstChild;
                const efgh = p.childNodes[1].childNodes[1].firstChild;
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: efgh,
                        anchorOffset: 2,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([efgh, 2, efgh, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([
                    efgh,
                    2,
                    efgh,
                    2,
                ]);
            });

            test("should collapse the cursor at the end of a nested inline element", async () => {
                const { editor, el } = await setupEditor("<p>ab<span>cd<b>ef</b>gh</span>ij</p>");
                const p = el.firstChild;
                const ef = p.childNodes[1].childNodes[1].firstChild;
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: ef,
                        anchorOffset: 2,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([ef, 2, ef, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([ef, 2, ef, 2]);
            });

            test("should collapse the cursor after a nested inline element", async () => {
                const { editor, el } = await setupEditor("<p>ab<span>cd<b>ef</b>gh</span>ij</p>");
                const p = el.firstChild;
                const ef = p.childNodes[1].childNodes[1].firstChild;
                const gh = p.childNodes[1].lastChild;
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: gh,
                        anchorOffset: 0,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([ef, 2, ef, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([ef, 2, ef, 2]);

                const nonNormalizedResult = getProcessSelection(
                    editor.shared.selection.setSelection(
                        { anchorNode: gh, anchorOffset: 0 },
                        { normalize: false }
                    )
                );
                editor.shared.selection.focusEditable();
                expect(nonNormalizedResult).toEqual([gh, 0, gh, 0]);
                const sel = document.getSelection();
                expect([sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset]).toEqual([
                    gh,
                    0,
                    gh,
                    0,
                ]);
            });
        });

        describe("forward", () => {
            test("should select the contents of an element", async () => {
                const { editor, el } = await setupEditor("<p>abc</p>");
                const p = el.firstChild;
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: p.firstChild,
                        anchorOffset: 0,
                        focusNode: p.firstChild,
                        focusOffset: 3,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([p.firstChild, 0, p.firstChild, 3]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([
                    p.firstChild,
                    0,
                    p.firstChild,
                    3,
                ]);
            });

            test("should make a complex selection", async () => {
                const { el, editor } = await setupEditor(
                    "<p>ab<span>cd<b>ef</b>gh</span>ij</p><p>kl<span>mn<b>op</b>qr</span>st</p>"
                );
                const [p1, p2] = el.childNodes;
                const ef = p1.childNodes[1].childNodes[1].firstChild;
                const qr = p2.childNodes[1].childNodes[2];
                const st = p2.childNodes[2];
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: ef,
                        anchorOffset: 1,
                        focusNode: st,
                        focusOffset: 0,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([ef, 1, qr, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([ef, 1, qr, 2]);

                const nonNormalizedResult = getProcessSelection(
                    editor.shared.selection.setSelection(
                        {
                            anchorNode: ef,
                            anchorOffset: 1,
                            focusNode: st,
                            focusOffset: 0,
                        },
                        { normalize: false }
                    )
                );
                expect(nonNormalizedResult).toEqual([ef, 1, st, 0]);
                const sel = document.getSelection();
                expect([sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset]).toEqual([
                    ef,
                    1,
                    st,
                    0,
                ]);
            });
        });

        describe("backward", () => {
            test("should select the contents of an element", async () => {
                const { editor, el } = await setupEditor("<p>abc</p>");
                const p = el.firstChild;
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: p.firstChild,
                        anchorOffset: 3,
                        focusNode: p.firstChild,
                        focusOffset: 0,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([p.firstChild, 3, p.firstChild, 0]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([
                    p.firstChild,
                    3,
                    p.firstChild,
                    0,
                ]);
            });

            test("should make a complex selection", async () => {
                const { el, editor } = await setupEditor(
                    "<p>ab<span>cd<b>ef</b>gh</span>ij</p><p>kl<span>mn<b>op</b>qr</span>st</p>"
                );
                const [p1, p2] = el.childNodes;
                const ef = p1.childNodes[1].childNodes[1].firstChild;
                const qr = p2.childNodes[1].childNodes[2];
                const st = p2.childNodes[2];
                const result = getProcessSelection(
                    editor.shared.selection.setSelection({
                        anchorNode: st,
                        anchorOffset: 0,
                        focusNode: ef,
                        focusOffset: 1,
                    })
                );
                editor.shared.selection.focusEditable();
                expect(result).toEqual([qr, 2, ef, 1]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([qr, 2, ef, 1]);

                const nonNormalizedResult = getProcessSelection(
                    editor.shared.selection.setSelection(
                        {
                            anchorNode: st,
                            anchorOffset: 0,
                            focusNode: ef,
                            focusOffset: 1,
                        },
                        { normalize: false }
                    )
                );
                expect(nonNormalizedResult).toEqual([st, 0, ef, 1]);
                const sel = document.getSelection();
                expect([sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset]).toEqual([
                    st,
                    0,
                    ef,
                    1,
                ]);
            });
        });
    });

    describe("setCursorStart", () => {
        test("should collapse the cursor at the beginning of an element", async () => {
            const { editor, el } = await setupEditor("<p>abc</p>");
            const p = el.firstChild;
            const result = getProcessSelection(editor.shared.selection.setCursorStart(p));
            editor.shared.selection.focusEditable();
            expect(result).toEqual([p.firstChild, 0, p.firstChild, 0]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([
                p.firstChild,
                0,
                p.firstChild,
                0,
            ]);
        });

        test("should collapse the cursor at the beginning of a nested inline element", async () => {
            const { editor, el } = await setupEditor("<p>ab<span>cd<b>ef</b>gh</span>ij</p>");
            const p = el.firstChild;
            const b = p.childNodes[1].childNodes[1];
            const ef = b.firstChild;
            const result = getProcessSelection(editor.shared.selection.setCursorStart(b));
            editor.shared.selection.focusEditable();
            expect(result).toEqual([ef, 0, ef, 0]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([ef, 0, ef, 0]);
        });

        test("should collapse the cursor after a nested inline element", async () => {
            const { editor, el } = await setupEditor("<p>ab<span>cd<b>ef</b>gh</span>ij</p>");
            const p = el.firstChild;
            const ef = p.childNodes[1].childNodes[1].firstChild;
            const gh = p.childNodes[1].lastChild;
            const result = getProcessSelection(editor.shared.selection.setCursorStart(gh));
            editor.shared.selection.focusEditable();
            expect(result).toEqual([ef, 2, ef, 2]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([ef, 2, ef, 2]);

            // @todo @phoenix normalize false is never use
            // const nonNormalizedResult = getProcessSelection(editor.shared.selection.setCursorStart(gh, false));
            // expect(nonNormalizedResult).toEqual([gh, 0, gh, 0]);
            // const sel = document.getSelection();
            // expect([sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset]).toEqual([
            //     gh,
            //     0,
            //     gh,
            //     0,
            // ]);
        });
    });

    describe("setCursorEnd", () => {
        test("should collapse the cursor at the end of an element", async () => {
            const { editor, el } = await setupEditor("<p>abc</p>");
            const p = el.firstChild;
            const result = getProcessSelection(editor.shared.selection.setCursorEnd(p));
            editor.shared.selection.focusEditable();
            expect(result).toEqual([p.firstChild, 3, p.firstChild, 3]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([
                p.firstChild,
                3,
                p.firstChild,
                3,
            ]);
        });

        test("should collapse the cursor before a nested inline element", async () => {
            const { editor, el } = await setupEditor("<p>ab<span>cd<b>ef</b>gh</span>ij</p>");
            const p = el.firstChild;
            const cd = p.childNodes[1].firstChild;
            const result = getProcessSelection(editor.shared.selection.setCursorEnd(cd));
            editor.shared.selection.focusEditable();
            expect(result).toEqual([cd, 2, cd, 2]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([cd, 2, cd, 2]);
        });

        test("should collapse the cursor at the end of a nested inline element", async () => {
            const { editor, el } = await setupEditor("<p>ab<span>cd<b>ef</b>gh</span>ij</p>");
            const p = el.firstChild;
            const b = p.childNodes[1].childNodes[1];
            const ef = b.firstChild;
            const result = getProcessSelection(editor.shared.selection.setCursorEnd(b));
            editor.shared.selection.focusEditable();
            expect(result).toEqual([ef, 2, ef, 2]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            expect([anchorNode, anchorOffset, focusNode, focusOffset]).toEqual([ef, 2, ef, 2]);
        });
    });
});

test.tags("desktop");
test("should not autoscroll if selection is partially visible in viewport", async () => {
    class Test extends models.Model {
        name = fields.Char();
        txt = fields.Html();
        _records = [{ id: 1, name: "Test", txt: "<p>This is some text</p>".repeat(50) }];
    }

    defineModels([Test]);
    await mountView({
        type: "form",
        resId: 1,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });

    const scrollableElement = queryOne(".o_content");
    const editable = queryOne(".odoo-editor-editable");
    const lastParagraph = editable.lastElementChild;
    const fifthLastParagraph = editable.children[45];

    // Select the last five paragraphs in backward.
    setSelection({
        anchorNode: lastParagraph,
        anchorOffset: 1,
        focusNode: fifthLastParagraph,
        focusOffset: 0,
    });
    await animationFrame();

    // Both ends of the selection are initially visible in the viewport.
    expect(isInViewPort(fifthLastParagraph)).toBe(true);
    expect(isInViewPort(lastParagraph)).toBe(true);

    // Scroll above so that last paragraph becomes invisible in viewport.
    scrollableElement.scrollTop -= 70;
    await animationFrame();
    expect(isInViewPort(lastParagraph)).toBe(false);
    expect(isInViewPort(fifthLastParagraph)).toBe(true);

    const scrollTop = scrollableElement.scrollTop;
    // Extend the selection to include one more paragraph above.
    setSelection({
        anchorNode: lastParagraph,
        anchorOffset: 1,
        focusNode: fifthLastParagraph.previousElementSibling,
        focusOffset: 0,
    });
    await animationFrame();

    // Ensure that extending selection did not trigger any auto-scrolling.
    expect(scrollableElement.scrollTop).toBe(scrollTop);
    expect(isInViewPort(lastParagraph)).toBe(false);
});

describe("crash fixes", () => {
    test("Should survive disconnected anchor", async () => {
        class TestPlugin extends Plugin {
            static id = "test";
            resources = {
                selectionchange_handlers: withSequence(-1, (selectionData) => {
                    const { anchorNode } = selectionData.editableSelection;
                    anchorNode.parentElement.remove();
                }),
            };
        }

        const { el } = await setupEditor("<p>x<span>a[]</span></p>", {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        });
        expect(getContent(el)).toBe("<p>x[]</p>");
    });
});

describe("Preserve selection", () => {
    const isSameCursor = (cursor1, cursor2) =>
        cursor1.anchor.node === cursor2.anchor.node &&
        cursor1.anchor.offset === cursor2.anchor.offset &&
        cursor1.focus.node === cursor2.focus.node &&
        cursor1.focus.offset === cursor2.focus.offset;

    test("Should properly sync cursors (1)", async () => {
        const { editor, el } = await setupEditor(
            `<p><span class="a">a</span><span class="b">b</span></p>`
        );
        const [span1, span2] = el.querySelectorAll("span");
        setSelection({
            anchorNode: span1,
            anchorOffset: 0,
            focusNode: span2,
            focusOffset: 0,
        });
        const c1 = editor.shared.selection.preserveSelection();
        const c2 = editor.shared.selection.preserveSelection();
        c1.update(callbacksForCursorUpdate.remove(span1));
        c2.update(callbacksForCursorUpdate.remove(span1));
        span1.remove();
        c1.restore();
        c2.restore();
        expect(isSameCursor(c1, c2)).toBe(true);
    });

    test("Should properly sync cursors (2)", async () => {
        const { editor, el } = await setupEditor(
            `<p><span class="a">a</span><span class="b">b</span></p>`
        );
        const [span1, span2] = el.querySelectorAll("span");
        setSelection({
            anchorNode: span1,
            anchorOffset: 0,
            focusNode: span2,
            focusOffset: 0,
        });
        const c1 = editor.shared.selection.preserveSelection();
        const c2 = editor.shared.selection.preserveSelection();
        c1.update(callbacksForCursorUpdate.remove(span1));
        span1.remove();
        c1.restore();
        expect(isSameCursor(c1, c2)).toBe(true);
    });

    test("Should properly sync cursors (3)", async () => {
        const { editor, el } = await setupEditor(
            `<p><span class="a">a</span><span class="b">b</span></p>`
        );
        const [span1, span2] = el.querySelectorAll("span");
        setSelection({
            anchorNode: span1,
            anchorOffset: 0,
            focusNode: span2,
            focusOffset: 0,
        });
        const c1 = editor.shared.selection.preserveSelection();
        const c2 = editor.shared.selection.preserveSelection();
        c1.update(callbacksForCursorUpdate.remove(span1));
        span1.remove();
        c2.restore();
        expect(isSameCursor(c1, c2)).toBe(true);
    });

    test("Should properly sync cursors (4)", async () => {
        const { editor, el } = await setupEditor(
            `<p><span class="a">a</span><span class="b">b</span></p>`
        );
        const [span1, span2] = el.querySelectorAll("span");
        setSelection({
            anchorNode: span1,
            anchorOffset: 0,
            focusNode: span2,
            focusOffset: 0,
        });
        const c1 = editor.shared.selection.preserveSelection();
        const c2 = editor.shared.selection.preserveSelection();
        c2.update(callbacksForCursorUpdate.remove(span1));
        span1.remove();
        c1.restore();
        expect(isSameCursor(c1, c2)).toBe(true);
    });
});
