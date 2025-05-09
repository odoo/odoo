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
import { setupEditor, testEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { insertText, tripleClick } from "./_helpers/user_actions";

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

test("correct selection after triple click with bold", async () => {
    const { el } = await setupEditor("<p>[]abc<strong>d</strong></p><p>efg</p>", {});
    await tripleClick(queryFirst("p").firstChild);
    expect(getContent(el)).toBe("<p>[abc<strong>d]</strong></p><p>efg</p>");
});

test("correct selection after triple click in multi-line block (1)", async () => {
    const { el } = await setupEditor("<p>[]abc<br>efg</p>", {});
    await tripleClick(queryFirst("p").firstChild);
    expect(getContent(el)).toBe("<p>[abc<br>efg]</p>");
});

test("correct selection after triple click in multi-line block (2)", async () => {
    const { el } = await setupEditor("<p>block1</p><p>[]block2<br>block2</p><p>block3</p>", {});
    await tripleClick(queryFirst("p").nextSibling.firstChild); // we triple click inside block2
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
    expect(getContent(el)).toBe(`<div class="oe_structure"><p>[ab]</p><p>cd</p></div>`);
});

test("press 'ctrl+a' in 'contenteditable' should only select his content", async () => {
    const { el } = await setupEditor(
        `<div contenteditable="false"><p contenteditable="true">a[]b</p><p contenteditable="true">cd</p></div>`
    );
    await press(["ctrl", "a"]);
    expect(getContent(el)).toBe(
        `<div contenteditable="false"><p contenteditable="true">[ab]</p><p contenteditable="true">cd</p></div>`
    );
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

test("set a collapse selection in a contenteditable false should move it after this node", async () => {
    const { el, editor } = await setupEditor(`<p>ab<span contenteditable="false">cd</span>ef</p>`);
    editor.shared.selection.setSelection({
        anchorNode: queryOne("span[contenteditable='false']"),
        anchorOffset: 1,
    });
    editor.shared.selection.focusEditable();
    expect(getContent(el)).toBe(`<p>ab<span contenteditable="false">cd</span>[]ef</p>`);
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

/** @deprecated these are legacy functions, replaced by `getTargetedNodes` */
describe("getters", () => {
    describe("getTraversedNodes", () => {
        test("should return the anchor node of a collapsed selection", async () => {
            const { editor } = await setupEditor("<div><p>a[]bc</p><div>def</div></div>");
            expect(
                editor.shared.selection
                    .getTraversedNodes()
                    .map((node) =>
                        node.nodeType === Node.TEXT_NODE ? node.textContent : node.nodeName
                    )
            ).toEqual(["abc"]);
        });

        test("should return the nodes traversed in a cross-blocks selection", async () => {
            const { editor } = await setupEditor("<div><p>a[bc</p><div>d]ef</div></div>");
            expect(
                editor.shared.selection
                    .getTraversedNodes()
                    .map((node) =>
                        node.nodeType === Node.TEXT_NODE ? node.textContent : node.nodeName
                    )
            ).toEqual(["DIV", "P", "abc", "DIV", "def"]);
        });

        test("should return the nodes traversed in a cross-blocks selection with hybrid nesting", async () => {
            const { editor } = await setupEditor(
                "<div><section><p>a[bc</p></section><div>d]ef</div></div>"
            );
            expect(
                editor.shared.selection
                    .getTraversedNodes()
                    .map((node) =>
                        node.nodeType === Node.TEXT_NODE ? node.textContent : node.nodeName
                    )
            ).toEqual(["DIV", "SECTION", "P", "abc", "DIV", "def"]);
        });

        test("should return an image in a parent selection", async () => {
            const { editor } = await setupEditor(`<div id="parent-element-to-select"><img></div>`);
            const sel = editor.document.getSelection();
            const range = editor.document.createRange();
            const parent = editor.document.querySelector("div#parent-element-to-select");
            range.setStart(parent, 0);
            range.setEnd(parent, 1);
            sel.removeAllRanges();
            sel.addRange(range);
            expect(
                editor.shared.selection
                    .getTraversedNodes()
                    .map((node) =>
                        node.nodeType === Node.TEXT_NODE ? node.textContent : node.nodeName
                    )
            ).toEqual(["DIV", "IMG"]);
        });

        test("should return the text node in which the range is collapsed", async () => {
            const { el: editable, editor } = await setupEditor("<p>ab[]cd</p>");
            const abcd = editable.firstChild.firstChild;
            const result = editor.shared.selection.getTraversedNodes();
            expect(result).toEqual([abcd]);
        });

        test("should find that a the range traverses the next paragraph as well", async () => {
            const { el: editable, editor } = await setupEditor("<p>ab[cd</p><p>ef]gh</p>");
            const p1 = editable.firstChild;
            const abcd = p1.firstChild;
            const p2 = editable.childNodes[1];
            const efgh = p2.firstChild;
            const result = editor.shared.selection.getTraversedNodes();
            expect(result).toEqual([p1, abcd, p2, efgh]);
        });

        test("should find all traversed nodes in nested range", async () => {
            const { el: editable, editor } = await setupEditor(
                '<p><span class="a">ab[</span>cd</p><div><p><span class="b"><b>e</b><i>f]g</i>h</span></p></div>'
            );
            const p1 = editable.firstChild;
            const cd = p1.lastChild;
            const div = editable.lastChild;
            const p2 = div.firstChild;
            const span2 = p2.firstChild;
            const b = span2.firstChild;
            const e = b.firstChild;
            const i = b.nextSibling;
            const fg = i.firstChild;
            const result = editor.shared.selection.getTraversedNodes();
            expect(result).toEqual([p1, cd, div, p2, span2, b, e, i, fg]);
        });

        test("selection does not have an edge with a br element", async () => {
            await testEditor({
                contentBefore: "[<p>ab</p><p>cd<br></p>]",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const p1 = editable.firstChild;
                    const ab = p1.firstChild;
                    const p2 = editable.lastChild;
                    const cd = p2.firstChild;
                    const br = p2.lastChild;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([p1, ab, p2, cd, br]);
                },
            });
        });
        test("selection ends before br element at start of p element", async () => {
            await testEditor({
                contentBefore: "[<p>ab</p><p>]<br>cd<br></p>",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const p1 = editable.firstChild;
                    const ab = p1.firstChild;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([p1, ab]);
                },
            });
        });
        test("selection ends before a br in middle of p element", async () => {
            await testEditor({
                contentBefore: "[<p>ab</p><p><br>cd]<br>ef<br></p>",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const p1 = editable.firstChild;
                    const ab = p1.firstChild;
                    const p2 = editable.lastChild;
                    const firstBr = p2.firstChild;
                    const cd = firstBr.nextSibling;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([p1, ab, p2, firstBr, cd]);
                },
            });
        });
        test("selection end after a br in middle of p elemnt", async () => {
            await testEditor({
                contentBefore: "[<p>ab</p><p><br>cd<br>]ef<br></p>",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const p1 = editable.firstChild;
                    const ab = p1.firstChild;
                    const p2 = editable.lastChild;
                    const br1 = p2.firstChild;
                    const cd = br1.nextSibling;
                    const br2 = cd.nextSibling;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([p1, ab, p2, br1, cd, br2]);
                },
            });
        });
        test("selection ends after a br at end of p elemnt", async () => {
            await testEditor({
                contentBefore: "[<p>ab</p><p><br>cd<br>]</p>",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const p1 = editable.firstChild;
                    const ab = p1.firstChild;
                    const p2 = editable.lastChild;
                    const br1 = p2.firstChild;
                    const cd = br1.nextSibling;
                    const br2 = cd.nextSibling;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([p1, ab, p2, br1, cd, br2]);
                },
            });
        });
        test("selection ends between 2 br elements", async () => {
            await testEditor({
                contentBefore: "[<p>ab</p><p>cd<br>]<br>ef</p>",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const p1 = editable.firstChild;
                    const ab = p1.firstChild;
                    const p2 = editable.firstChild.nextSibling;
                    const cd = p2.firstChild;
                    const br1 = cd.nextSibling;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([p1, ab, p2, cd, br1]);
                },
            });
        });
        test("selection starts before a br in middle of p element", async () => {
            await testEditor({
                contentBefore: "<p>ab[<br>cd</p><p>ef</p>]",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const p1 = editable.firstChild;
                    const ab = p1.firstChild;
                    const br = ab.nextSibling;
                    const cd = br.nextSibling;
                    const p2 = editable.lastChild;
                    const ef = p2.firstChild;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([p1, br, cd, p2, ef]);
                },
            });
        });
        test("selection starts before a br in start of p element", async () => {
            await testEditor({
                contentBefore: "<p>[ab<br>cd</p><p>ef</p>]",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const p1 = editable.firstChild;
                    const ab = p1.firstChild;
                    const br = ab.nextSibling;
                    const cd = br.nextSibling;
                    const p2 = editable.lastChild;
                    const ef = p2.firstChild;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([p1, ab, br, cd, p2, ef]);
                },
            });
        });
        test("selection starts after a br at end of p element", async () => {
            await testEditor({
                contentBefore: "<p>ab<br>[</p><p>cd</p>]",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const p2 = editable.lastChild;
                    const cd = p2.firstChild;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([p2, cd]);
                },
            });
        });
        test("selection starts after a br in middle of p element", async () => {
            await testEditor({
                contentBefore: "<p>ab<br>[cd</p><p>ef</p>]",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const p1 = editable.firstChild;
                    const ab = p1.firstChild;
                    const br = ab.nextSibling;
                    const cd = br.nextSibling;
                    const p2 = editable.lastChild;
                    const ef = p2.firstChild;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([p1, cd, p2, ef]);
                },
            });
        });
        test("selection starts between 2 br elements", async () => {
            await testEditor({
                contentBefore: "<p>ab<br>[<br>cd</p><p>ef</p>]",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const p1 = editable.firstChild;
                    const ab = p1.firstChild;
                    const br1 = ab.nextSibling;
                    const br2 = br1.nextSibling;
                    const cd = br2.nextSibling;
                    const p2 = editable.firstChild.nextSibling;
                    const ef = p2.firstChild;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([p1, br2, cd, p2, ef]);
                },
            });
        });
        test("selection within table cells 1", async () => {
            await testEditor({
                contentBefore: "<table><tbody><tr><td>abcd[e</td><td>f]g</td></tr></tbody></table>",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const tr = editable.firstChild.firstChild.firstChild;
                    const td1 = tr.firstChild;
                    const abcde = td1.firstChild;
                    const td2 = td1.nextSibling;
                    const fg = td2.firstChild;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([td1, abcde, td2, fg]);
                },
            });
        });
        test("selection within table cells 2", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody><tr><td>abcd<br>[<br>e</td><td>f]g</td></tr></tbody></table>",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const tr = editable.firstChild.firstChild.firstChild;
                    const td1 = tr.firstChild;
                    const abcd = td1.firstChild;
                    const br1 = abcd.nextSibling;
                    const br2 = br1.nextSibling;
                    const e = br2.nextSibling;
                    const td2 = td1.nextSibling;
                    const fg = td2.firstChild;
                    const result = editor.shared.selection.getTraversedNodes();
                    expect(result).toEqual([td1, abcd, br1, br2, e, td2, fg]);
                },
            });
        });
    });

    describe("getSelectedNodes", () => {
        test("should return nothing if the range is collapsed", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: (editor) => {
                    const result = editor.shared.selection.getSelectedNodes();
                    expect(result).toEqual([]);
                },
                contentAfter: "<p>ab[]cd</p>",
            });
        });

        test("should find that no node is fully selected", async () => {
            await testEditor({
                contentBefore: "<p>ab[c]d</p>",
                stepFunction: (editor) => {
                    const result = editor.shared.selection.getSelectedNodes();
                    expect(result).toEqual([]);
                },
            });
        });

        test("should find that no node is fully selected, across blocks", async () => {
            await testEditor({
                contentBefore: "<p>ab[cd</p><p>ef]gh</p>",
                stepFunction: (editor) => {
                    const result = editor.shared.selection.getSelectedNodes();
                    expect(result).toEqual([]);
                },
            });
        });

        test("should find that a text node is fully selected", async () => {
            await testEditor({
                contentBefore: '<p><span class="a">ab</span>[cd]</p>',
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const result = editor.shared.selection.getSelectedNodes();
                    const cd = editable.firstChild.lastChild;
                    expect(result).toEqual([cd]);
                },
            });
        });

        test("should find that a block is fully selected", async () => {
            await testEditor({
                contentBefore: "<p>[ab</p><p>cd</p><p>ef]gh</p>",
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const result = editor.shared.selection.getSelectedNodes();
                    const ab = editable.firstChild.firstChild;
                    const p2 = editable.childNodes[1];
                    const cd = p2.firstChild;
                    expect(result).toEqual([ab, p2, cd]);
                },
            });
        });

        test("should find all selected nodes in nested range", async () => {
            await testEditor({
                contentBefore:
                    '<p><span class="a">ab[</span>cd</p><div><p><span class="b"><b>e</b><i>f]g</i>h</span></p></div>',
                stepFunction: (editor) => {
                    const editable = editor.editable;
                    const cd = editable.firstChild.lastChild;
                    const b = editable.lastChild.firstChild.firstChild.firstChild;
                    const e = b.firstChild;
                    const result = editor.shared.selection.getSelectedNodes();
                    expect(result).toEqual([cd, b, e]);
                },
            });
        });
    });
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
                const outerDiv = editable.firstChild;
                const p1 = outerDiv.firstChild; // The selection crossed `</p>` -> include it.
                const abc = p1.firstChild;
                const innerDiv = p1.nextSibling; // The selection crossed `<div>` -> include it.
                const def = innerDiv.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
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
                // The first span is not included because the selection appears
                // to the user to just be before the letter "c".
                const p1 = editable.firstChild; // The selection crossed `</p>` -> include it.
                const cd = p1.lastChild;
                const div = editable.lastChild;
                const p2 = div.firstChild;
                const span2 = p2.firstChild; // The selection crossed `<span class="b">` -> include it.
                const b = span2.firstChild;
                const e = b.firstChild;
                const i = b.nextSibling; // The selection crossed `<i>` -> include it.
                const fg = i.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, cd, div, p2, span2, b, e, i, fg]);
            });
        });
        describe("outwardly selected block", () => {
            test.tags("fails -> to investigate");
            test.tags("dubious");
            test.skip("should return a fully selected block (from its outer edges) and its contents", async () => {
                // DUBIOUS: It seems right but [<p> has been treated differently
                // elsewhere. Here it fails in the way I expect other tests to
                // pass.
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
            test.tags("dubious");
            test("should include intersected blocks, including an empty one (selection across two blocks, from/to inner right edge)", async () => {
                const { el: editable, editor } = await setupEditor("<p>ab[</p><p>cd]</p>");
                // The selection is seen as `<p>abc</p><p>[def]</p>` by the user
                // -> the first P and its contents are not intersected by the
                // selection.
                // THIS IS DUBIOUS BECAUSE WHILE SEEN THAT WAY (always?) IF THE USER
                // TYPES IT WILL REMOVE THE NEWLINE.
                const p2 = editable.childNodes[1]; // The selection crossed `<p>` -> include it.
                const cd = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p2, cd]);
            });

            test.tags("dubious");
            test("<p>ab[</p><p>cd</p>]", async () => {
                // The selection is seen as `<p>ab</p><p>[cd</p>]` by the user
                // -> the first P and its contents are not intersected by the
                // selection.
                // THIS IS DUBIOUS BECAUSE WHILE SEEN THAT WAY (always?) IF THE USER
                // TYPES IT WILL REMOVE THE NEWLINE.
                const { el: editable, editor } = await setupEditor("<p>ab[</p><p>cd</p>]");
                const p2 = editable.lastChild;
                const cd = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p2, cd]);
            });

            test.tags("dubious");
            test("should include intersected blocks, including an empty one (selection across two blocks, from inner right to inner left edge)", async () => {
                const { editor } = await setupEditor("<p>abcd[</p><p>]<br></p>");
                // The selection is seen as `<p>abc</p><p>[]<br></p>` by the user
                // -> the first P and its contents are not intersected by the selection.
                // THIS IS DUBIOUS BECAUSE WHILE SEEN THAT WAY (always?) IF THE USER
                // TYPES IT WILL REMOVE THE NEWLINE.
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([]);
            });

            test.tags("fails -> to investigate");
            test.skip("should ignore a triple click block crossing", async () => {
                const { editor } = await setupEditor("<p>ab[cd</p><p>]efgh</p>");
                // The selection is seen as `<p>ab[cd]</p><p>efgh</p>` by the user
                // -> the second P is not intersected by the selection.
                expect(nameNodes(editor.shared.selection.getTargetedNodes())).toEqual(["abcd"]);
            });

            test("should ignore a triple click block crossing but include an outwardly selected block (1)", async () => {
                const { el: editable, editor } = await setupEditor("[<p>ab</p><p>]cd</p>");
                // The selection is seen as `[<p>ab]</p><p>cd</p>` by the user
                // -> the second P is not intersected by the selection.
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab]);
            });

            test("should ignore a triple click block crossing but include an outwardly selected block (2)", async () => {
                const { el: editable, editor } = await setupEditor("[<p>ab</p><p>]<br>cd<br></p>");
                // The selection is seen as `[<p>ab]</p><p><br>cd<br></p>` by the user
                // -> the second P is not intersected by the selection.
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab]);
            });

            test("should ignore a triple click block crossing but include an outwardly selected block (3)", async () => {
                const { el: editable, editor } = await setupEditor("[<p>ab</p><p>]<br></p>");
                // The selection is seen as `[<p>ab]</p><p><br></p>` by the user
                // -> the second P is not intersected by the selection.
                const p1 = editable.firstChild;
                const ab = p1.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab]);
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

            test.tags("dubious");
            test("should not include a non-selected BR just before selection (from outer right edge)", async () => {
                const { el: editable, editor } = await setupEditor("<p>ab<br>[</p><p>cd</p>]");
                // The selection is seen as `<p>ab<br></p><p>[cd</p>]` by the user
                // -> the first P is not intersected by the selection.
                // THIS IS DUBIOUS BECAUSE WHILE SEEN THAT WAY (always?) IF THE USER
                // TYPES IT WILL REMOVE THE NEWLINE.
                const p2 = editable.lastChild;
                const cd = p2.firstChild;
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p2, cd]);
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
                const result = editor.shared.selection.getTargetedNodes();
                expect(result).toEqual([p1, ab, p2, br1, cd, br2]);
            });

            test("should include a selected BR just at the beginning of selection", async () => {
                const { el: editable, editor } = await setupEditor("<p>ab[<br>cd</p><p>ef</p>]");
                const p1 = editable.firstChild; // The selection crossed `</p>` -> include it.
                const ab = p1.firstChild;
                const br = ab.nextSibling;
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
