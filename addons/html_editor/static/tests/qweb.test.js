import { describe, expect, test } from "@odoo/hoot";
import { click, dblclick, queryAll, queryAllTexts, queryOne, select } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { QWebPlugin } from "@html_editor/others/qweb_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { dispatchCleanForSave } from "./_helpers/dispatch";

const config = { Plugins: [...MAIN_PLUGINS, QWebPlugin] };
describe("qweb picker", () => {
    test("switch selected value to t-else value", async () => {
        const { el, editor } = await setupEditor(
            `<div><t t-if="test">yes</t><t t-else="">no</t></div>`,
            { config }
        );
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );
        await click(queryOne(`[data-oe-t-group-active="true"]`));
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(queryAllTexts(".o-we-qweb-picker option")).toEqual(["if: test", "else"]);
        expect(".o-we-qweb-picker select option:selected").toHaveText("if: test");

        await click(".o-we-qweb-picker select");
        await select("0,1"); // t-else
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(".o-we-qweb-picker select option:selected").toHaveText("else");
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0" data-oe-t-group-active="true">no</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );

        dispatchCleanForSave(editor, { root: el });
        expect(getContent(el)).toBe(`<div><t t-if="test">yes</t><t t-else="">no</t></div>`);
    });

    test("plugin's dom markers are not savable", async () => {
        const resources = {
            handleNewRecords: () => {
                expect.step("handleNewRecords");
            },
        };
        await setupEditor(`<div><t t-if="test">yes</t><t t-else="">no</t></div>`, {
            config: { ...config, resources },
        });
        expect.verifySteps([]);
    });

    test("switch selected value to the same value ", async () => {
        const { el } = await setupEditor(`<div><t t-if="test">yes</t><t t-else="">no</t></div>`, {
            config,
        });
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );
        await click(queryOne(`[data-oe-t-group-active="true"]`));
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(queryAllTexts(".o-we-qweb-picker option")).toEqual(["if: test", "else"]);
        expect(".o-we-qweb-picker select option:selected").toHaveText("if: test");

        await click(".o-we-qweb-picker select");
        await select("0,0"); // t-if
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(".o-we-qweb-picker select option:selected").toHaveText("if: test");
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );
    });

    test("switch selected value between each value", async () => {
        const { el } = await setupEditor(
            `<div><t t-if="test">if</t><t t-elif="test2">elif</t><t t-elif="test3">elif 3</t><t t-else="">else</t></div>`,
            { config }
        );
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">if</t><t t-elif="test2" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif</t><t t-elif="test3" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif 3</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">else</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );
        await click(queryOne(`[data-oe-t-group-active="true"]`));
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(queryAllTexts(".o-we-qweb-picker option")).toEqual([
            "if: test",
            "elif: test2",
            "elif: test3",
            "else",
        ]);
        expect(".o-we-qweb-picker select option:selected").toHaveText("if: test");

        await click(".o-we-qweb-picker select");
        await select("0,1"); // t-elif test2
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(".o-we-qweb-picker select option:selected").toHaveText("elif: test2");
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true">if</t><t t-elif="test2" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0" data-oe-t-group-active="true">elif</t><t t-elif="test3" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif 3</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">else</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );

        await click(".o-we-qweb-picker select");
        await select("0,2"); // t-elif test2
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(".o-we-qweb-picker select option:selected").toHaveText("elif: test3");
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true">if</t><t t-elif="test2" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif</t><t t-elif="test3" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0" data-oe-t-group-active="true">elif 3</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">else</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );

        await click(".o-we-qweb-picker select");
        await select("0,3"); // t-else
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(".o-we-qweb-picker select option:selected").toHaveText("else");
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true">if</t><t t-elif="test2" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif</t><t t-elif="test3" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif 3</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0" data-oe-t-group-active="true">else</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );
    });

    test("switch selected value with multi group", async () => {
        const { el } = await setupEditor(
            `<div><t t-if="test">yes</t><t t-else="">no</t><t t-if="test2">hello</t><t t-else="">bye</t></div>`,
            { config }
        );
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t><t t-if="test2" data-oe-t-inline="true" data-oe-t-group="1" data-oe-t-selectable="true" data-oe-t-group-active="true">hello</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="1">bye</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );
        expect('[data-oe-t-group-active="true"]').toHaveCount(2);

        await click(queryOne(`[data-oe-t-group="1"][data-oe-t-group-active="true"]`));
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(queryAllTexts(".o-we-qweb-picker option")).toEqual(["if: test2", "else"]);
        expect(".o-we-qweb-picker select option:selected").toHaveText("if: test2");

        await click(".o-we-qweb-picker select");
        await select("0,1"); // t-else
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(".o-we-qweb-picker select option:selected").toHaveText("else");
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t><t t-if="test2" data-oe-t-inline="true" data-oe-t-group="1" data-oe-t-selectable="true">hello</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="1" data-oe-t-group-active="true">bye</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );
    });

    test("click outside to close it", async () => {
        const { el } = await setupEditor(`<div><t t-if="test">yes</t><t t-else="">no</t></div>`, {
            config,
        });
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );

        // Open picker
        await click(queryOne(`[data-oe-t-group-active="true"]`));
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);

        // Click outside to close the picker
        await click(el.querySelector("div"));
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(0);
    });

    test("select value on branch node multi level", async () => {
        const { el } = await setupEditor(
            `<div><t t-if="test"><t t-if="sub-test">Sub if</t><t t-else="">Sub Else</t></t><t t-else="">Else</t></div>`,
            {
                config,
            }
        );
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true"><t t-if="sub-test" data-oe-t-inline="true" data-oe-t-group="1" data-oe-t-selectable="true" data-oe-t-group-active="true">Sub if</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="1">Sub Else</t></t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">Else</t></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );

        // Open picker on sub condition
        await click(queryAll(`[data-oe-t-group-active="true"]`)[1]);
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(".o-we-qweb-picker select").toHaveCount(2);
        expect(queryAllTexts(".o-we-qweb-picker select:first option")).toEqual([
            "if: test",
            "else",
        ]);
        expect(".o-we-qweb-picker select:first option:selected").toHaveText("if: test");
        expect(queryAllTexts(".o-we-qweb-picker select:last option")).toEqual([
            "if: sub-test",
            "else",
        ]);
        expect(".o-we-qweb-picker select:last option:selected").toHaveText("if: sub-test");

        // Select t-else on sub condition
        await click(".o-we-qweb-picker select:last");
        await select("1,1"); // sub t-else
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(".o-we-qweb-picker select").toHaveCount(2);
        expect(queryAllTexts(".o-we-qweb-picker select:first option")).toEqual([
            "if: test",
            "else",
        ]);
        expect(".o-we-qweb-picker select:first option:selected").toHaveText("if: test");
        expect(queryAllTexts(".o-we-qweb-picker select:last option")).toEqual([
            "if: sub-test",
            "else",
        ]);
        expect(".o-we-qweb-picker select:last option:selected").toHaveText("else");

        // Select t-else on main condition
        await click(".o-we-qweb-picker select:first");
        await select("0,1"); // t-else
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(".o-we-qweb-picker select").toHaveCount(1);
        expect(".o-we-qweb-picker select option:selected").toHaveText("else");
        expect(queryAllTexts(".o-we-qweb-picker select option")).toEqual(["if: test", "else"]);
    });
});

test("select text inside t-out", async () => {
    const { el } = await setupEditor(`<div><t t-out="test">Hello</t></div>`, {
        config,
    });
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            `<div><t t-out="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t></div>` +
            '<p data-selection-placeholder=""><br></p>'
    );

    setSelection({ anchorNode: el.querySelector("t[t-out]").childNodes[0], anchorOffset: 1 });

    await tick();
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            `<div><t t-out="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">H[]ello</t></div>` +
            '<p data-selection-placeholder=""><br></p>'
    );
    await dblclick("t");
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            `<div>[<t t-out="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>]</div>` +
            '<p data-selection-placeholder=""><br></p>'
    );
});

test("select text inside t-esc", async () => {
    const { el } = await setupEditor(`<div><t t-esc="test">Hello</t></div>`, {
        config,
    });
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            `<div><t t-esc="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t></div>` +
            '<p data-selection-placeholder=""><br></p>'
    );

    setSelection({ anchorNode: el.querySelector("t[t-esc]").childNodes[0], anchorOffset: 1 });

    await tick();
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            `<div><t t-esc="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">H[]ello</t></div>` +
            '<p data-selection-placeholder=""><br></p>'
    );
    await dblclick("t");
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            `<div>[<t t-esc="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>]</div>` +
            '<p data-selection-placeholder=""><br></p>'
    );
});

test("select text inside t-field", async () => {
    const { el } = await setupEditor(`<div><t t-field="test">Hello</t></div>`, {
        config,
    });
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            `<div><t t-field="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t></div>` +
            '<p data-selection-placeholder=""><br></p>'
    );

    setSelection({ anchorNode: el.querySelector("t[t-field]").childNodes[0], anchorOffset: 1 });

    await tick();
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            `<div><t t-field="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">H[]ello</t></div>` +
            '<p data-selection-placeholder=""><br></p>'
    );
    await dblclick("t");
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            `<div>[<t t-field="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>]</div>` +
            '<p data-selection-placeholder=""><br></p>'
    );
});

test("cleaning removes content editable", async () => {
    const { el, editor } = await setupEditor(
        `
        <div>
            <t t-field="test">Hello</t>
            <t t-out="test">Hello</t>
            <t t-esc="test">Hello</t>
            <t t-raw="test">Hello</t>
        </div>`,
        {
            config: { Plugins: config.Plugins.filter((plugin) => plugin.id !== "editorVersion") },
        }
    );
    expect(getContent(el)).toBe(`
        <p data-selection-placeholder=""><br></p><div>
            <t t-field="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>
            <t t-out="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>
            <t t-esc="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>
            <t t-raw="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>
        </div><p data-selection-placeholder=""><br></p>`);

    expect(editor.getContent()).toBe(`
        <div>
            <t t-field="test">Hello</t>
            <t t-out="test">Hello</t>
            <t t-esc="test">Hello</t>
            <t t-raw="test">Hello</t>
        </div>`);
});

test("cleaning does not remove t-out links", async () => {
    const { el, editor } = await setupEditor(
        `
        <ul>
            <li><a href="xyz" t-out="xyz"/></li>
        </ul>
    `,
        { config }
    );
    expect(el.innerHTML.trim().replace(/\s+/g, " ")).toBe(
        `<ul> <li><a href="xyz" t-out="xyz" data-oe-protected="true" contenteditable="false"></a></li> </ul>`
    );
    expect(editor.getContent().trim().replace(/\s+/g, " ")).toBe(
        '<ul> <li><a href="xyz" t-out="xyz"></a></li> </ul>'
    );
});
