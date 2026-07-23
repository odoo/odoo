import { expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { getContent } from "./_helpers/selection";

test("should remove empty class attribute", async () => {
    // content after is compared after cleaning up DOM
    await testEditor({
        contentBefore: '<div class=""></div>',
        contentAfter: "<div><br></div>",
    });
});

test("should remove `style.color` from table and apply it to tds", async () => {
    await testEditor({
        contentBefore: unformat(`
                <table style="color: red;" class="o_selected_table"><tbody>
                    <tr><td class="o_selected_td">ab</td></tr>
                    <tr><td>ab</td></tr>
                </tbody></table>
            `),
        contentBeforeEdit: unformat(`
            <p data-selection-placeholder=""><br></p>
            <table class="o_selected_table">
                <tbody>
                    <tr><td class="o_selected_td" style="color: red;">ab</td></tr>
                    <tr><td style="color: red;">ab</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder=""><br></p>
        `),
    });
});

test("should remove `style.color` from table and apply it to td without `style.color`", async () => {
    await testEditor({
        contentBefore: unformat(`
                <table style="color: red;"><tbody>
                    <tr><td>ab</td></tr>
                    <tr><td style="color: green;">ab</td></tr>
                </tbody></table>
            `),
        contentBeforeEdit: unformat(`
            <p data-selection-placeholder=""><br></p>
            <table>
                <tbody>
                    <tr><td style="color: red;">ab</td></tr>
                    <tr><td style="color: green;">ab</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder=""><br></p>
        `),
    });
});

test("Should properly add feffs around icons", async () => {
    await testEditor({
        contentBefore: `<div><span class="oi" data-icon="local_bar" contenteditable="false"></span></div>`,
        contentBeforeEdit: `<div class="o-paragraph">\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>\ufeff</div>`,
    });
});

test("should flag mutations from normalization", async () => {
    class MakeItBluePlugin extends Plugin {
        static id = "makeItBlue";
        static dependencies = [];
        resources = {
            normalize_processors: (root) => {
                for (const p of selectElements(root, "p.blue")) {
                    p.setAttribute("style", "color: blue;");
                    p.append(this.document.createTextNode("d"));
                }
            },
        };
    }
    const config = { includePlugins: [MakeItBluePlugin] };
    const { editor, el, plugins } = await setupEditor("<p>a[]</p>", { config });

    const normalize = editor.shared.dom.normalize.bind(editor);
    const domObserverPlugin = plugins.get("domObserver");
    const expectedM = [];
    const step = (callback, ...newMutations) => {
        callback();
        domObserverPlugin.flush();
        expectedM.push(...newMutations);
        const mutations = domObserverPlugin.mutations;
        const received = mutations.map(({ type, isAutomatic = false }) => ({ type, isAutomatic }));
        const expected = expectedM.map(({ type, isAutomatic = false }) => ({ type, isAutomatic }));
        expect(received).toEqual(expected);
    };

    step(() => editor.shared.dom.insert("b"), { type: "add" });
    step(() => el.firstChild.setAttribute("class", "blue"), { type: "classList" });
    step(normalize, { type: "attributes", isAutomatic: true }, { type: "add", isAutomatic: true });
    step(() => editor.shared.dom.insert("c"), { type: "add" });

    // Checking the result for good measure.
    expect(getContent(el)).toBe('<p class="blue" style="color: blue;">abc[]d</p>');
});
