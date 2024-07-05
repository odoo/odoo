import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { setSelection, setContent } from "../_helpers/selection";
import { insertText } from "../_helpers/user_actions";
import { waitFor, waitForNone } from "@odoo/hoot-dom";

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
                <div data-oe-protected="true"><p>ab</p></div>
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
                <div data-oe-protected="true"><div data-oe-protected="false"><p>ab[]</p></div></div>
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
                <div data-oe-protected="true">
                    <p><i class="fa"></i></p>
                    <ul><li>abc<p><br></p></li></ul>
                </div>
                `),
    });
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
                <div data-oe-protected="true">
                    <p><i class="fa"></i></p>
                    <ul><li>abc<p><br></p></li></ul>
                    <div data-oe-protected="false">
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
                <div data-oe-protected="true">
                    <p>a[bc</p><table><tbody><tr><td>a]b</td><td>cd</td><td>ef</td></tr></tbody></table>
                </div>
                `),
    });
});

test("should handle table selection in unprotected elements children (false)", async () => {
    await testEditor({
        contentBefore: unformat(`
                <div data-oe-protected="true">
                    <div data-oe-protected="false">
                        <p>a[bc</p><table><tbody><tr><td>a]b</td><td>cd</td><td>ef</td></tr></tbody></table>
                    </div>
                </div>
                `),
        contentAfterEdit: unformat(`
                <div data-oe-protected="true">
                    <div data-oe-protected="false">
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

test("should not select a protected table (true)", async () => {
    // Individually protected cells are not yet supported for simplicity
    // since there is no need for that currently.
    await testEditor({
        contentBefore: unformat(`
                    <table data-oe-protected="true"><tbody><tr>
                        <td>[ab</td>
                    </tr></tbody></table>
                    <table><tbody><tr>
                        <td>cd]</td>
                    </tr></tbody></table>
                `),
        contentAfterEdit: unformat(`
                    <table data-oe-protected="true"><tbody><tr>
                        <td>[ab</td>
                    </tr></tbody></table>
                    <table class="o_selected_table"><tbody><tr>
                        <td class="o_selected_td">cd]</td>
                    </tr></tbody></table>
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
    await animationFrame();
    const lastStep = editor.shared.getHistorySteps().at(-1);
    expect(lastStep.mutations.length).toBe(1);
    expect(lastStep.mutations[0].type).toBe("remove");
    expect(plugins.get("history").unserializeNode(lastStep.mutations[0].node).outerHTML).toBe(
        `<div data-oe-protected="true"></div>`
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
    await animationFrame();
    const lastStep = editor.shared.getHistorySteps().at(-1);
    expect(lastStep.mutations.length).toBe(2);
    expect(lastStep.mutations[0].type).toBe("attributes");
    expect(lastStep.mutations[1].type).toBe("remove");
    expect(plugins.get("history").unserializeNode(lastStep.mutations[1].node).outerHTML).toBe(
        `<div data-attr="other" data-oe-protected="true"><p>a</p></div>`
    );
});
