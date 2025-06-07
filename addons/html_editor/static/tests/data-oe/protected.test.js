import { expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { setSelection, setContent, getContent } from "../_helpers/selection";
import { deleteBackward, insertText, undo } from "../_helpers/user_actions";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { parseHTML } from "@html_editor/utils/html";
import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { execCommand } from "../_helpers/userCommands";

test("should ignore protected elements children mutations (true)", async () => {
    await testEditor({
        contentBefore: unformat(`
                <div><p>a[]</p></div>
                <div data-oe-protected="true"><p>a</p></div>
                `),
        stepFunction: async (editor) => {
            await insertText(editor, "bc");
            const protectedParagraph = editor.editable.querySelector(
                '[data-oe-protected="true"] > p'
            );
            protectedParagraph.append(document.createTextNode("b"));
            editor.shared.history.addStep();
            execCommand(editor, "historyUndo");
        },
        contentAfterEdit: unformat(`
                <div><p>ab[]</p></div>
                <div data-oe-protected="true" contenteditable="false"><p>ab</p></div>
                `),
    });
});

test("should not ignore unprotected elements children mutations (false)", async () => {
    await testEditor({
        contentBefore: unformat(`
                <div><p>a[]</p></div>
                <div data-oe-protected="true"><div data-oe-protected="false"><p>a</p></div></div>
                `),
        stepFunction: async (editor) => {
            await insertText(editor, "bc");
            const unProtectedParagraph = editor.editable.querySelector(
                '[data-oe-protected="false"] > p'
            );
            setSelection({ anchorNode: unProtectedParagraph, anchorOffset: 1 });
            await insertText(editor, "bc");
            execCommand(editor, "historyUndo");
        },
        contentAfterEdit: unformat(`
                <div><p>abc</p></div>
                <div data-oe-protected="true" contenteditable="false"><div data-oe-protected="false" contenteditable="true"><p>ab[]</p></div></div>
                `),
    });
});

test("should not update activeSelection when clicking inside a protected node", async () => {
    const { el, editor } = await setupEditor(`<p><span data-oe-protected="true"></span>[]</p>`);
    const span = el.querySelector("span");
    let editableSelection = editor.shared.selection.getEditableSelection();
    const documentSelection = editor.document.getSelection();
    documentSelection.removeAllRanges();
    const range = editor.document.createRange();
    range.selectNodeContents(span);
    // Set document range inside the protected zone
    documentSelection.addRange(range);
    editableSelection = editor.shared.selection.getEditableSelection();
    // Ensure that the editable selection stayed unchanged
    setSelection(editableSelection);
    expect(getContent(el)).toBe(
        `<p><span data-oe-protected="true" contenteditable="false"></span>[]</p>`
    );
});

test("should not normalize protected elements children (true)", async () => {
    await testEditor({
        contentBefore: unformat(`
                <div>
                    <p><i class="fa"></i></p>
                    <ul><li>abc<p><br></p></li></ul>
                </div>
                <div data-oe-protected="true">
                    <p><i class="fa"></i></p>
                    <ul><li>abc<p><br></p></li></ul>
                </div>
                `),
        contentAfterEdit: unformat(`
                <div>
                    <p>\ufeff<i class="fa" contenteditable="false">\u200B</i>\ufeff</p>
                    <ul><li><p>abc</p><p><br></p></li></ul>
                </div>
                <div data-oe-protected="true" contenteditable="false">
                    <p>\ufeff<i class="fa"></i>\ufeff</p>
                    <ul><li>abc<p><br></p></li></ul>
                </div>
                `),
    });
});

test("should not remove/merge empty (identical) protecting nodes", async () => {
    const { el, editor } = await setupEditor(`<p><span data-oe-protected="true"></span>[]</p>`);
    editor.shared.dom.insert(parseHTML(editor.document, `<span data-oe-protected="true"></span>`));
    editor.shared.history.addStep();
    expect(getContent(el)).toBe(
        unformat(
            `<p>
                <span data-oe-protected="true" contenteditable="false"></span>
                <span data-oe-protected="true" contenteditable="false"></span>[]
            </p>`
        )
    );
});

test("should normalize unprotected elements children (false)", async () => {
    await testEditor({
        contentBefore: unformat(`
                <div data-oe-protected="true">
                    <p><i class="fa"></i></p>
                    <ul><li>abc<p><br></p></li></ul>
                    <div data-oe-protected="false">
                        <p><i class="fa"></i></p>
                        <ul><li>abc<p><br></p></li></ul>
                    </div>
                </div>
                `),
        contentAfterEdit: unformat(`
                <div data-oe-protected="true" contenteditable="false">
                    <p>\ufeff<i class="fa"></i>\ufeff</p>
                    <ul><li>abc<p><br></p></li></ul>
                    <div data-oe-protected="false" contenteditable="true">
                        <p>\ufeff<i class="fa" contenteditable="false">\u200B</i>\ufeff</p>
                        <ul><li><p>abc</p><p><br></p></li></ul>
                    </div>
                </div>
                `),
    });
});

test("should not handle table selection in protected elements children (true)", async () => {
    await testEditor({
        contentBefore: unformat(`
                <div data-oe-protected="true">
                    <p>a[bc</p><table><tbody><tr><td>a]b</td><td>cd</td><td>ef</td></tr></tbody></table>
                </div>
                `),
        contentAfterEdit: unformat(`
                <div data-oe-protected="true" contenteditable="false">
                    <p>a[bc</p><table><tbody><tr><td>a]b</td><td>cd</td><td>ef</td></tr></tbody></table>
                </div>
                `),
    });
});

test("should handle table selection in unprotected elements", async () => {
    await testEditor({
        contentBefore: unformat(`
                <div data-oe-protected="true">
                    <div data-oe-protected="false">
                        <p>a[bc</p><table><tbody><tr><td>a]b</td><td>cd</td><td>ef</td></tr></tbody></table>
                    </div>
                </div>
                `),
        contentAfterEdit: unformat(`
                <div data-oe-protected="true" contenteditable="false">
                    <div data-oe-protected="false" contenteditable="true">
                        <p>a[bc</p>
                        <table class="o_selected_table"><tbody><tr>
                            <td class="o_selected_td">a]b</td>
                            <td class="o_selected_td">cd</td>
                            <td class="o_selected_td">ef</td>
                        </tr></tbody></table>
                    </div>
                </div>
                `),
    });
});

test("should not remove contenteditable attribute of a protected node", async () => {
    await testEditor({
        contentBefore: unformat(`
                <div data-oe-protected="true">
                    <p contenteditable="true">content</p>
                    <table contenteditable="true">
                        <tbody><tr><td>ab</td></tr></tbody>
                    </table>
                    <div contenteditable="true">
                        <p>content</p>
                    </div>
                </div>
            `),
        contentAfterEdit: unformat(`
                <div data-oe-protected="true" contenteditable="false">
                    <p contenteditable="true">content</p>
                    <table contenteditable="true">
                        <tbody><tr><td>ab</td></tr></tbody>
                    </table>
                    <div contenteditable="true">
                        <p>content</p>
                    </div>
                </div>
            `),
    });
});

test("should not select a protected table even if it is contenteditable='true'", async () => {
    // Individually protected cells are not yet supported for simplicity
    // since there is no need for that currently.
    await testEditor({
        contentBefore: unformat(`
                <div data-oe-protected="true">
                    <table contenteditable="true"><tbody><tr>
                        <td>[ab</td>
                    </tr></tbody></table>
                    <table><tbody><tr>
                        <td>cd]</td>
                    </tr></tbody></table>
                </div>
            `),
        contentAfterEdit: unformat(`
                <div data-oe-protected="true" contenteditable="false">
                    <table contenteditable="true"><tbody><tr>
                        <td>[ab</td>
                    </tr></tbody></table>
                    <table><tbody><tr>
                        <td>cd]</td>
                    </tr></tbody></table>
                </div>
            `),
    });
});

test("select a protected element shouldn't open the toolbar", async () => {
    const { el } = await setupEditor(
        `<div><p>[a]</p></div><div data-oe-protected="true"><p>b</p><div data-oe-protected="false">c</div></div>`
    );
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(1);

    setContent(
        el,
        `<div><p>a</p></div><div data-oe-protected="true"><p>[b]</p><div data-oe-protected="false">c</div></div>`
    );
    await waitForNone(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(0);

    setContent(
        el,
        `<div><p>a</p></div><div data-oe-protected="true"><p>b</p><div data-oe-protected="false">[c]</div></div>`
    );
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(1);
});

test("should protect disconnected nodes", async () => {
    const { editor, el, plugins } = await setupEditor(
        `<div data-oe-protected="true"><p>a</p></div><p>a</p>`
    );
    const div = el.querySelector("div");
    const protectedP = div.querySelector("p");
    protectedP.remove();
    div.remove();
    editor.shared.history.addStep();
    const lastStep = editor.shared.history.getHistorySteps().at(-1);
    expect(lastStep.mutations.length).toBe(1);
    expect(lastStep.mutations[0].type).toBe("remove");
    expect(plugins.get("history").unserializeNode(lastStep.mutations[0].node).outerHTML).toBe(
        `<div contenteditable="false" data-oe-protected="true"></div>`
    );
});

test("should not crash when changing attributes and removing a protecting anchor", async () => {
    const { editor, el, plugins } = await setupEditor(
        `<div data-oe-protected="true" data-attr="value"><p>a</p></div><p>a</p>`
    );
    const div = el.querySelector("div");
    div.dataset.attr = "other";
    div.remove();
    editor.shared.history.addStep();
    const lastStep = editor.shared.history.getHistorySteps().at(-1);
    expect(lastStep.mutations.length).toBe(2);
    expect(lastStep.mutations[0].type).toBe("attributes");
    expect(lastStep.mutations[1].type).toBe("remove");
    expect(plugins.get("history").unserializeNode(lastStep.mutations[1].node).outerHTML).toBe(
        `<div contenteditable="false" data-attr="other" data-oe-protected="true"><p>a</p></div>`
    );
});

test("removing a protected node should be undo-able", async () => {
    const { editor, el } = await setupEditor(
        `<div data-oe-protected="true"><p>a</p></div><p>[]a</p>`
    );
    deleteBackward(editor);
    expect(getContent(el)).toBe(`<p>[]a</p>`);
    undo(editor);
    expect(getContent(el)).toBe(
        `<div data-oe-protected="true" contenteditable="false"><p>a</p></div><p>[]a</p>`
    );
});

test("removing a recursively protected then unprotected node should be undo-able", async () => {
    const { editor, el, plugins } = await setupEditor(
        unformat(`
            <div data-oe-protected="true">
                <p>a</p>
                <div data-oe-protected="false">
                    <p>b</p>
                    <div data-oe-protected="true">
                        <p>c</p>
                        <div data-oe-protected="false">
                            <p>d</p>
                        </div>
                        <p>w</p>
                    </div>
                    <p>x</p>
                </div>
                <p>y</p>
            </div>
            <p>[]z</p>
        `)
    );
    const protectPlugin = plugins.get("protectedNode");
    const protectingNodes = [...el.querySelectorAll(`[data-oe-protected="true"]`)];
    const unprotectingNodes = [...el.querySelectorAll(`[data-oe-protected="false"]`)];
    const unprotectedDescendants = [];
    for (const unprotectingNode of unprotectingNodes) {
        unprotectedDescendants.push([...unprotectingNode.childNodes]);
    }
    expect(protectPlugin.filterDescendantsToRemove(protectingNodes[0])).toEqual(
        unprotectedDescendants[0]
    );
    expect(protectPlugin.filterDescendantsToRemove(protectingNodes[1])).toEqual(
        unprotectedDescendants[1]
    );
    deleteBackward(editor);
    expect([...unprotectingNodes[0].childNodes]).toEqual([]);
    expect([...unprotectingNodes[1].childNodes]).toEqual([]);
    expect(getContent(el)).toBe(`<p>[]z</p>`);
    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
            <div data-oe-protected="true" contenteditable="false">
                <p>a</p>
                <div data-oe-protected="false" contenteditable="true">
                    <p>b</p>
                    <div data-oe-protected="true" contenteditable="false">
                        <p>c</p>
                        <div data-oe-protected="false" contenteditable="true">
                            <p>d</p>
                        </div>
                        <p>w</p>
                    </div>
                    <p>x</p>
                </div>
                <p>y</p>
            </div>
            <p>[]z</p>
        `)
    );
});

test("removing a protected node and then removing its protected parent should be ignored", async () => {
    const { editor, el, plugins } = await setupEditor(
        unformat(`
            <div data-oe-protected="true">
                <div class="a">
                    <div class="b"></div>
                </div>
            </div>
        `)
    );
    const historyPlugin = plugins.get("history");
    expect(editor.shared.history.getHistorySteps().length).toBe(1);
    expect(historyPlugin.currentStep.mutations).toEqual([]);
    const a = el.querySelector(".a");
    const b = el.querySelector(".b");
    b.remove();
    a.remove();
    editor.shared.history.addStep();
    expect(editor.shared.history.getHistorySteps().length).toBe(1);
    expect(historyPlugin.currentStep.mutations).toEqual([]);
    expect(getContent(el)).toBe(`<div data-oe-protected="true" contenteditable="false"></div>`);
});

test("removing a protected ancestor, then a protected descendant, then its protected parent should be ignored", async () => {
    const { editor, el, plugins } = await setupEditor(
        unformat(`
            <div data-oe-protected="true">
                <div class="a">
                    <div class="b">
                        <div class="c"></div>
                    </div>
                </div>
            </div>
        `)
    );
    const historyPlugin = plugins.get("history");
    expect(editor.shared.history.getHistorySteps().length).toBe(1);
    expect(historyPlugin.currentStep.mutations).toEqual([]);
    const a = el.querySelector(".a");
    const b = el.querySelector(".b");
    const c = el.querySelector(".c");
    a.remove();
    c.remove();
    b.remove();
    editor.shared.history.addStep();
    expect(editor.shared.history.getHistorySteps().length).toBe(1);
    expect(historyPlugin.currentStep.mutations).toEqual([]);
    expect(getContent(el)).toBe(`<div data-oe-protected="true" contenteditable="false"></div>`);
});

test("moving a protected node at an unprotected location, only remove should be ignored", async () => {
    const { editor, el, plugins } = await setupEditor(
        unformat(`
            <div data-oe-protected="true">
                <div class="b" data-oe-protected="false"></div>
            </div>
            <div data-oe-protected="true">
                <p class="a"></p>
            </div>
        `)
    );
    const historyPlugin = plugins.get("history");
    expect(editor.shared.history.getHistorySteps().length).toBe(1);
    expect(historyPlugin.currentStep.mutations).toEqual([]);
    const a = el.querySelector(".a");
    const b = el.querySelector(".b");
    b.append(a);
    editor.shared.history.addStep();
    const historySteps = editor.shared.history.getHistorySteps();
    expect(historySteps.length).toBe(2);
    const lastStep = historySteps.at(-1);
    expect(lastStep.mutations.length).toBe(1);
    expect(lastStep.mutations[0].type).toBe("add");
    expect(historyPlugin.idToNodeMap.get(lastStep.mutations[0].id)).toBe(a);
    expect(getContent(el)).toBe(
        unformat(`
            <div data-oe-protected="true" contenteditable="false">
                <div class="b" data-oe-protected="false" contenteditable="true">
                    <p class="a"></p>
                </div>
            </div>
            <div data-oe-protected="true" contenteditable="false"></div>
        `)
    );
});

test("moving an unprotected node at a protected location, only add should be ignored", async () => {
    const { editor, el, plugins } = await setupEditor(
        unformat(`
            <div data-oe-protected="true">
                <div data-oe-protected="false">
                    <p class="a">content</p>
                </div>
            </div>
            <div class="b" data-oe-protected="true"></div>
        `)
    );
    const historyPlugin = plugins.get("history");
    expect(editor.shared.history.getHistorySteps().length).toBe(1);
    expect(historyPlugin.currentStep.mutations).toEqual([]);
    const a = el.querySelector(".a");
    const b = el.querySelector(".b");
    b.append(a);
    editor.shared.history.addStep();
    const historySteps = editor.shared.history.getHistorySteps();
    expect(historySteps.length).toBe(2);
    const lastStep = historySteps.at(-1);
    expect(lastStep.mutations.length).toBe(1);
    expect(lastStep.mutations[0].type).toBe("remove");
    expect(historyPlugin.idToNodeMap.get(lastStep.mutations[0].id)).toBe(a);
    expect(getContent(el)).toBe(
        unformat(`
            <div data-oe-protected="true" contenteditable="false">
                <div data-oe-protected="false" contenteditable="true"></div>
            </div>
            <div class="b" data-oe-protected="true" contenteditable="false">
                <p class="a">content</p>
            </div>
        `)
    );
});

test("sequentially added nodes under a protecting parent are correctly protected", async () => {
    const { editor, el, plugins } = await setupEditor(
        unformat(`
            <div data-oe-protected="true">
                content
            </div>
        `)
    );
    const protectedPlugin = plugins.get("protectedNode");
    expect(editor.shared.history.getHistorySteps().length).toBe(1);
    const protecting = el.querySelector("[data-oe-protected='true']");
    const element = editor.document.createElement("div");
    const node = editor.document.createTextNode("a");
    protecting.prepend(element);
    element.prepend(node);
    editor.shared.history.addStep();
    expect(protectedPlugin.protectedNodes.has(element)).toBe(true);
    expect(protectedPlugin.protectedNodes.has(node)).toBe(true);
    expect(getContent(el)).toBe(
        unformat(`
            <div data-oe-protected="true" contenteditable="false">
                <div>a</div>
                content
            </div>
        `)
    );
    node.remove();
    editor.shared.history.addStep();
    expect(getContent(el)).toBe(
        unformat(`
            <div data-oe-protected="true" contenteditable="false">
                <div></div>
                content
            </div>
        `)
    );
    expect(editor.shared.history.getHistorySteps().length).toBe(1);
});

test("don't protect a node under data-oe-protected='false' through delete and undo", async () => {
    const { editor, el, plugins } = await setupEditor(
        unformat(`
            <div data-oe-protected="true">
                <div data-oe-protected="false">
                    <p>a</p>
                </div>
            </div>
            <p>[]a</p>
        `)
    );
    const protectedPlugin = plugins.get("protectedNode");
    expect(editor.shared.history.getHistorySteps().length).toBe(1);
    const protecting = el.querySelector("[data-oe-protected='false']");
    const paragraph = editor.document.createElement("p");
    const node = editor.document.createTextNode("b");
    protecting.prepend(paragraph);
    paragraph.prepend(node);
    editor.shared.history.addStep();
    expect(editor.shared.history.getHistorySteps().length).toBe(2);
    expect(protectedPlugin.protectedNodes.has(paragraph)).toBe(false);
    expect(protectedPlugin.protectedNodes.has(node)).toBe(false);
    expect(getContent(el)).toBe(
        unformat(`
            <div data-oe-protected="true" contenteditable="false">
                <div data-oe-protected="false" contenteditable="true">
                    <p>b</p>
                    <p>a</p>
                </div>
            </div>
            <p>[]a</p>
        `)
    );
    deleteBackward(editor);
    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
            <div data-oe-protected="true" contenteditable="false">
                <div data-oe-protected="false" contenteditable="true">
                    <p>b</p>
                    <p>a</p>
                </div>
            </div>
            <p>[]a</p>
        `)
    );
    expect(editor.shared.history.getHistorySteps().length).toBe(4);
});

test("protected plugin is robust against other plugins which can filter mutations", async () => {
    class FilterPlugin extends Plugin {
        static id = "filterPlugin";
        resources = {
            savable_mutation_record_predicates: this.isMutationRecordSavable.bind(this),
        };
        isMutationRecordSavable(record) {
            if (
                record.type === "childList" &&
                record.removedNodes.length === 1 &&
                [...record.removedNodes][0] === a
            ) {
                // Artificially hide the removal of `a` node
                return false;
            }
            return true;
        }
    }
    const { editor, el, plugins } = await setupEditor(
        unformat(`
            <div data-oe-protected="true">
                <div class="a">
                    <div class="b"></div>
                </div>
            </div>
        `),
        // Put FilterPlugin as the first plugin, so that its filter is applied before
        // protected_node_plugin.
        { config: { Plugins: [FilterPlugin, ...MAIN_PLUGINS] } }
    );
    const historyPlugin = plugins.get("history");
    expect(editor.shared.history.getHistorySteps().length).toBe(1);
    expect(historyPlugin.currentStep.mutations).toEqual([]);
    const a = el.querySelector(".a");
    const b = el.querySelector(".b");
    a.remove();
    b.remove();
    editor.shared.history.addStep();
    expect(editor.shared.history.getHistorySteps().length).toBe(1);
    expect(historyPlugin.currentStep.mutations).toEqual([]);
    expect(getContent(el)).toBe(`<div data-oe-protected="true" contenteditable="false"></div>`);
});
