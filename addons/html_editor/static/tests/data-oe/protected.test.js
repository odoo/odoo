import { expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { setSelection, setContent, getContent } from "../_helpers/selection";
import { deleteBackward, insertText, undo } from "../_helpers/user_actions";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { parseHTML } from "@html_editor/utils/html";

test("should ignore protected elements children mutations (true)", async () => {
    await testEditor({
        contentBefore: unformat(`
                <div><p>a[]</p></div>
                <div data-oe-protected="true"><p>a</p></div>
                `),
        stepFunction: async (editor) => {
            insertText(editor, "bc");
            const protectedParagraph = editor.editable.querySelector(
                '[data-oe-protected="true"] > p'
            );
            protectedParagraph.append(document.createTextNode("b"));
            editor.dispatch("ADD_STEP");
            editor.dispatch("HISTORY_UNDO");
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
            insertText(editor, "bc");
            const unProtectedParagraph = editor.editable.querySelector(
                '[data-oe-protected="false"] > p'
            );
            setSelection({ anchorNode: unProtectedParagraph, anchorOffset: 1 });
            insertText(editor, "bc");
            editor.dispatch("HISTORY_UNDO");
        },
        contentAfterEdit: unformat(`
                <div><p>abc</p></div>
                <div data-oe-protected="true" contenteditable="false"><div data-oe-protected="false" contenteditable="true"><p>ab[]</p></div></div>
                `),
    });
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
        stepFunction: async (editor) => editor.dispatch("NORMALIZE", { node: editor.editable }),
        contentAfterEdit: unformat(`
                <div>
                    <p><i class="fa" contenteditable="false">\u200B</i></p>
                    <ul><li><p>abc</p><p><br></p></li></ul>
                </div>
                <div data-oe-protected="true" contenteditable="false">
                    <p><i class="fa"></i></p>
                    <ul><li>abc<p><br></p></li></ul>
                </div>
                `),
    });
});

test("should not remove/merge empty (identical) protecting nodes", async () => {
    const { el, editor } = await setupEditor(`<p><span data-oe-protected="true"></span>[]</p>`);
    editor.shared.domInsert(parseHTML(editor.document, `<span data-oe-protected="true"></span>`));
    editor.dispatch("ADD_STEP");
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
        stepFunction: async (editor) => editor.dispatch("NORMALIZE", { node: editor.editable }),
        contentAfterEdit: unformat(`
                <div data-oe-protected="true" contenteditable="false">
                    <p><i class="fa"></i></p>
                    <ul><li>abc<p><br></p></li></ul>
                    <div data-oe-protected="false" contenteditable="true">
                        <p><i class="fa" contenteditable="false">\u200B</i></p>
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
    editor.dispatch("ADD_STEP");
    const lastStep = editor.shared.getHistorySteps().at(-1);
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
    editor.dispatch("ADD_STEP");
    const lastStep = editor.shared.getHistorySteps().at(-1);
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
    const protectPlugin = plugins.get("protected_node");
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

test("normalize should set contenteditable attribute on protecting nodes and that mutation should be observed", async () => {
    // Mutation should be observed in order for the content to arrive to a collaborator in a
    // "normalized state". Can be changed, but the entire editable has to be normalized
    // after receiving any external step in that case.
    const { editor, el, plugins } = await setupEditor(
        unformat(`
            <p>a[]</p>
        `)
    );
    const p = el.querySelector("p");
    p.before(
        ...parseHTML(
            editor.document,
            unformat(`
                <div data-oe-protected="true">
                    <div data-oe-protected="false">
                        <p>d</p>
                    </div>
                </div>
            `)
        ).children
    );
    editor.dispatch("ADD_STEP");
    const historyPlugin = plugins.get("history");
    const lastStep = editor.shared.getHistorySteps().at(-1);
    expect(lastStep.mutations.length).toBe(3);
    expect(lastStep.mutations[0].type).toBe("add");
    expect(lastStep.mutations[1].type).toBe("attributes");
    expect(lastStep.mutations[1].value).toBe("false");
    expect(historyPlugin.idToNodeMap.get(lastStep.mutations[1].id)).toBe(
        el.querySelector(`[data-oe-protected="true"]`)
    );
    expect(lastStep.mutations[2].type).toBe("attributes");
    expect(lastStep.mutations[2].value).toBe("true");
    expect(historyPlugin.idToNodeMap.get(lastStep.mutations[2].id)).toBe(
        el.querySelector(`[data-oe-protected="false"]`)
    );
    expect(getContent(el)).toBe(
        unformat(`
            <div data-oe-protected="true" contenteditable="false">
                <div data-oe-protected="false" contenteditable="true">
                    <p>d</p>
                </div>
            </div>
            <p>a[]</p>
        `)
    );
});
