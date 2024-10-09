import { describe, expect, test } from "@odoo/hoot";
import { getActiveElement, press, queryFirst, queryOne } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { useAutofocus } from "@web/core/utils/hooks";
import { Plugin } from "../src/plugin";
import { MAIN_PLUGINS } from "../src/plugin_sets";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { insertText, tripleClick } from "./_helpers/user_actions";

test("getEditableSelection should work, even if getSelection returns null", async () => {
    const { editor } = await setupEditor("<p>a[b]</p>");
    let selection = editor.shared.getEditableSelection();
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);

    // it happens sometimes in firefox that the selection is null
    patchWithCleanup(document, {
        getSelection: () => null,
    });

    selection = editor.shared.getEditableSelection();
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);
});

test("plugins should be notified when ranges are removed", async () => {
    let count = 0;
    class TestPlugin extends Plugin {
        static name = "test";
        resources = {
            onSelectionChange: () => count++,
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

test("fix selection P in the beggining being a direct child of the editable p after selection", async () => {
    const { el } = await setupEditor("<div>a</div>[]<p>b</p>");
    expect(getContent(el)).toBe(`<div>a</div><p>[]b</p>`);
});
test("fix selection P in the beggining being a direct child of the editable p before selection", async () => {
    const { el } = await setupEditor("<p>a</p>[]<div>b</div>");
    expect(getContent(el)).toBe(`<p>a[]</p><div>b</div>`);
});

describe("documentSelectionIsInEditable", () => {
    test("documentSelectionIsInEditable should be true", async () => {
        const { editor } = await setupEditor("<p>a[]b</p>");
        const selectionData = editor.shared.getSelectionData();
        expect(selectionData.documentSelectionIsInEditable).toBe(true);
    });

    test("documentSelectionIsInEditable should be false when it is set outside the editable", async () => {
        const { editor } = await setupEditor("<p>ab</p>");
        const selectionData = editor.shared.getSelectionData();
        expect(selectionData.documentSelectionIsInEditable).toBe(false);
    });

    test("documentSelectionIsInEditable should be false when it is set outside the editable after retrieving it", async () => {
        const { editor } = await setupEditor("<p>ab[]</p>");
        const selection = document.getSelection();
        let selectionData = editor.shared.getSelectionData();
        expect(selectionData.documentSelectionIsInEditable).toBe(true);
        selection.setPosition(document.body);
        // value is updated directly !
        selectionData = editor.shared.getSelectionData();
        expect(selectionData.documentSelectionIsInEditable).toBe(false);
    });
});

test("setEditableSelection should not crash if getSelection returns null", async () => {
    const { editor } = await setupEditor("<p>a[b]</p>");
    let selection = editor.shared.getEditableSelection();
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);

    // it happens sometimes in firefox that the selection is null
    patchWithCleanup(document, {
        getSelection: () => null,
    });

    selection = editor.shared.setSelection({
        anchorNode: editor.editable.firstChild,
        anchorOffset: 0,
    });

    // Selection could not be set, so it remains unchanged.
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);
});

test("modifySelection should not crash if getSelection returns null", async () => {
    const { editor } = await setupEditor("<p>a[b]</p>");
    let selection = editor.shared.getEditableSelection();
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);

    // it happens sometimes in firefox that the selection is null
    patchWithCleanup(document, {
        getSelection: () => null,
    });

    selection = editor.shared.modifySelection("extend", "backward", "word");

    // Selection could not be modified.
    expect(selection.startOffset).toBe(1);
    expect(selection.endOffset).toBe(2);
});

test("setSelection should not set the selection outside the editable", async () => {
    const { editor, el } = await setupEditor("<p>a[b]</p>");
    editor.document.getSelection().setPosition(document.body);
    await tick();
    const selection = editor.shared.setSelection(editor.shared.getEditableSelection());
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
        static name = "test";
        static dependencies = ["overlay"];
        resources = {
            powerboxItems: [
                {
                    category: "widget",
                    name: "Test",
                    description: "Test",
                    action: () => {
                        this.showOverlay();
                    },
                },
            ],
        };

        setup() {
            this.overlay = this.shared.createOverlay(TestInput);
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
    expect(getActiveElement()).toBe(queryOne("input.test"));

    // Something trigger restore
    const cursors = editor.shared.preserveSelection();
    cursors.restore();
    expect(getActiveElement()).toBe(queryOne("input.test"));
});

test("set a collapse selection in a contenteditable false should move it after this node", async () => {
    const { el, editor } = await setupEditor(`<p>ab<span contenteditable="false">cd</span>ef</p>`);
    editor.shared.setSelection({
        anchorNode: queryOne("span[contenteditable='false']"),
        anchorOffset: 1,
    });
    editor.shared.focusEditable();
    expect(getContent(el)).toBe(`<p>ab<span contenteditable="false">cd</span>[]ef</p>`);
});
