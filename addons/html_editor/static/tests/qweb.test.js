import { describe, expect, test } from "@odoo/hoot";
import { click, dblclick, queryAll, queryAllTexts, queryOne, select } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { QWebPlugin } from "@html_editor/others/qweb_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { dispatchClean } from "./_helpers/dispatch";

import { bold, setColor, setFontSize } from "./_helpers/user_actions";
import { unformat } from "./_helpers/format";

const config = { Plugins: [...MAIN_PLUGINS, QWebPlugin] };
describe("qweb picker", () => {
    test("switch selected value to t-else value", async () => {
        const { el, editor } = await setupEditor(
            `<div><t t-if="test">yes</t><t t-else="">no</t></div>`,
            { config }
        );
        expect(getContent(el)).toBe(
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t></div>`
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
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0" data-oe-t-group-active="true">no</t></div>`
        );

        dispatchClean(editor);
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
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t></div>`
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
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t></div>`
        );
    });

    test("switch selected value between each value", async () => {
        const { el } = await setupEditor(
            `<div><t t-if="test">if</t><t t-elif="test2">elif</t><t t-elif="test3">elif 3</t><t t-else="">else</t></div>`,
            { config }
        );
        expect(getContent(el)).toBe(
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">if</t><t t-elif="test2" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif</t><t t-elif="test3" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif 3</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">else</t></div>`
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
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true">if</t><t t-elif="test2" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0" data-oe-t-group-active="true">elif</t><t t-elif="test3" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif 3</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">else</t></div>`
        );

        await click(".o-we-qweb-picker select");
        await select("0,2"); // t-elif test2
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(".o-we-qweb-picker select option:selected").toHaveText("elif: test3");
        expect(getContent(el)).toBe(
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true">if</t><t t-elif="test2" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif</t><t t-elif="test3" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0" data-oe-t-group-active="true">elif 3</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">else</t></div>`
        );

        await click(".o-we-qweb-picker select");
        await select("0,3"); // t-else
        await animationFrame();
        expect(".o-we-qweb-picker").toHaveCount(1);
        expect(".o-we-qweb-picker select option:selected").toHaveText("else");
        expect(getContent(el)).toBe(
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true">if</t><t t-elif="test2" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif</t><t t-elif="test3" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">elif 3</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0" data-oe-t-group-active="true">else</t></div>`
        );
    });

    test("switch selected value with multi group", async () => {
        const { el } = await setupEditor(
            `<div><t t-if="test">yes</t><t t-else="">no</t><t t-if="test2">hello</t><t t-else="">bye</t></div>`,
            { config }
        );
        expect(getContent(el)).toBe(
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t><t t-if="test2" data-oe-t-inline="true" data-oe-t-group="1" data-oe-t-selectable="true" data-oe-t-group-active="true">hello</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="1">bye</t></div>`
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
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t><t t-if="test2" data-oe-t-inline="true" data-oe-t-group="1" data-oe-t-selectable="true">hello</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="1" data-oe-t-group-active="true">bye</t></div>`
        );
    });

    test("click outside to close it", async () => {
        const { el } = await setupEditor(`<div><t t-if="test">yes</t><t t-else="">no</t></div>`, {
            config,
        });
        expect(getContent(el)).toBe(
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">yes</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">no</t></div>`
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
            `<div><t t-if="test" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true"><t t-if="sub-test" data-oe-t-inline="true" data-oe-t-group="1" data-oe-t-selectable="true" data-oe-t-group-active="true">Sub if</t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="1">Sub Else</t></t><t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">Else</t></div>`
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
        `<div><t t-out="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t></div>`
    );

    setSelection({ anchorNode: el.querySelector("t[t-out]").childNodes[0], anchorOffset: 1 });

    await tick();
    expect(getContent(el)).toBe(
        `<div><t t-out="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">H[]ello</t></div>`
    );
    await dblclick("t");
    expect(getContent(el)).toBe(
        `<div>[<t t-out="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>]</div>`
    );
});

test("select text inside t-esc", async () => {
    const { el } = await setupEditor(`<div><t t-esc="test">Hello</t></div>`, {
        config,
    });
    expect(getContent(el)).toBe(
        `<div><t t-esc="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t></div>`
    );

    setSelection({ anchorNode: el.querySelector("t[t-esc]").childNodes[0], anchorOffset: 1 });

    await tick();
    expect(getContent(el)).toBe(
        `<div><t t-esc="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">H[]ello</t></div>`
    );
    await dblclick("t");
    expect(getContent(el)).toBe(
        `<div>[<t t-esc="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>]</div>`
    );
});

test("select text inside t-field", async () => {
    const { el } = await setupEditor(`<div><t t-field="test">Hello</t></div>`, {
        config,
    });
    expect(getContent(el)).toBe(
        `<div><t t-field="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t></div>`
    );

    setSelection({ anchorNode: el.querySelector("t[t-field]").childNodes[0], anchorOffset: 1 });

    await tick();
    expect(getContent(el)).toBe(
        `<div><t t-field="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">H[]ello</t></div>`
    );
    await dblclick("t");
    expect(getContent(el)).toBe(
        `<div>[<t t-field="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>]</div>`
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
        <div>
            <t t-field="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>
            <t t-out="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>
            <t t-esc="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>
            <t t-raw="test" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Hello</t>
        </div>`);

    expect(editor.getContent()).toBe(`
        <div>
            <t t-field="test">Hello</t>
            <t t-out="test">Hello</t>
            <t t-esc="test">Hello</t>
            <t t-raw="test">Hello</t>
        </div>`);
});

describe("toolbar visibility on contenteditable false elements", () => {
    test("should open the toolbar when the selected t-out is contenteditable false", async () => {
        const { el } = await setupEditor(
            '<div contenteditable="false"><t t-out="">a[]bc</t></div>',
            { config }
        );
        await dblclick("t");
        await animationFrame();
        expect(".o-we-toolbar").toHaveCount(1);
        expect(getContent(el)).toBe(
            `[<div contenteditable="false"><t t-out="" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">abc</t></div>]`
        );
    });

    test("should open the toolbar when the selected t-field is contenteditable false", async () => {
        const { el } = await setupEditor(
            '<div contenteditable="false"><t t-field="">a[]bc</t></div>',
            { config }
        );
        await dblclick("t");
        await animationFrame();
        expect(".o-we-toolbar").toHaveCount(1);
        expect(getContent(el)).toBe(
            `[<div contenteditable="false"><t t-field="" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">abc</t></div>]`
        );
    });

    test("should open the toolbar when the selected t-esc is contenteditable=false", async () => {
        const { el } = await setupEditor(
            '<div contenteditable="false"><t t-esc="">a[]bc</t></div>',
            { config }
        );
        await dblclick("t");
        await animationFrame();
        expect(".o-we-toolbar").toHaveCount(1);
        expect(getContent(el)).toBe(
            `[<div contenteditable="false"><t t-esc="" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">abc</t></div>]`
        );
    });
});

test("should create a history step when applying bold to a QWeb tag", async () => {
    const { editor, el } = await setupEditor(
        `<div><p t-esc="'Test'" contenteditable="false">T[e]st</p></div>`,
        { config }
    );
    await dblclick("[t-esc]");
    await animationFrame();
    bold(editor);
    expect(getContent(el)).toBe(
        `<div>[<p t-esc="'Test'" contenteditable="false" data-oe-protected="true" style="font-weight: bolder;">Test</p>]</div>`
    );
    expect(queryOne(`p[contenteditable="false"]`).childNodes.length).toBe(1);
    const historySteps = editor.shared.history.getHistorySteps();
    expect(historySteps.length).toBe(2);
    const lastStep = historySteps.at(-1);
    expect(lastStep.mutations.length).toBe(1);
    expect(lastStep.mutations[0].type).toBe("attributes");
    expect(lastStep.mutations[0].attributeName).toBe("style");
    expect(lastStep.mutations[0].value).toBe("font-weight: bolder;");
});

test("should wrap `t` in `span and be able to remove it`", async () => {
    const { editor, el } = await setupEditor(`<p>x[<t t-out="hello">abc</t>]x</p>`, { config });
    expect(getContent(el)).toBe(
        `<p>x[<t t-out="hello" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">abc</t>]x</p>`
    );
    setFontSize("10px")(editor);
    expect(getContent(el)).toBe(
        `<p>x[<span style="font-size: 10px;"><t t-out="hello" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">abc</t></span>]x</p>`
    );
    setFontSize("")(editor);
    expect(getContent(el)).toBe(
        `<p>x[<t t-out="hello" data-oe-protected="true" contenteditable="false" data-oe-t-inline="true">abc</t>]x</p>`
    );
});

test("should apply font size to the span parent when `t` tag is the sole child of a span and be able to remove it", async () => {
    const { editor, el } = await setupEditor(`<p><span>[<t t-out="'Test'">Test</t>]</span></p>`, {
        config,
    });
    expect(getContent(el)).toBe(
        `<p><span>[<t t-out="'Test'" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Test</t>]</span></p>`
    );
    setFontSize("10px")(editor);
    expect(getContent(el)).toBe(
        `<p><span style="font-size: 10px;">[<t t-out="'Test'" data-oe-protected="true" contenteditable="false" data-oe-t-inline="true">Test</t>]</span></p>`
    );
    setFontSize("")(editor);
    expect(getContent(el)).toBe(
        `<p>[<t t-out="'Test'" data-oe-protected="true" contenteditable="false" data-oe-t-inline="true">Test</t>]</p>`
    );
});

test("should color `t` with `span` and be able to remove it", async () => {
    const { editor, el } = await setupEditor(
        `<p>x<span style="color: rgb(255, 0, 0)">[<t t-out="hello">abc</t>]</span>x</p>`,
        { config }
    );
    expect(getContent(el)).toBe(
        `<p>x<span style="color: rgb(255, 0, 0)">[<t t-out="hello" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">abc</t>]</span>x</p>`
    );
    setColor("", "color")(editor);
    expect(getContent(el)).toBe(
        `<p>x[<t t-out="hello" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">abc</t>]x</p>`
    );
});

test("should not apply font tag to t nodes (protects if else nodes separation)", async () => {
    const { editor, el } = await setupEditor(
        unformat(`[
            <p>
                <t t-if="object.partner_id.parent_id">
                   <t t-out="object.partner_id.parent_id.name or ''">Azure Interior</t>
                </t>
                <t t-else="">
                    <t t-out="object.partner_id.name or ''">Brandon Freeman</t>
                </t>
            </p>
        ]`),
        { config }
    );
    expect(getContent(el)).toBe(
        unformat(`[
            <p>
                <t t-if="object.partner_id.parent_id" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">
                    <t t-out="object.partner_id.parent_id.name or ''" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">AzureInterior</t>
                </t>
                <t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">
                    <t t-out="object.partner_id.name or ''" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">BrandonFreeman</t>
                </t>
            </p>
        ]`)
    );
    setColor("red", "color")(editor);
    expect(getContent(el)).toBe(
        unformat(`[
            <p>
                <t t-if="object.partner_id.parent_id" data-oe-t-inline="true" data-oe-t-group="1" data-oe-t-selectable="true" data-oe-t-group-active="true">
                    <font style="color: red;">
                        <t t-out="object.partner_id.parent_id.name or ''" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">AzureInterior</t>
                    </font>
                </t>
                <t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="1">
                    <font style="color: red;">
                        <t t-out="object.partner_id.name or ''" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">BrandonFreeman</t>
                    </font>
                </t>
            </p>
        ]`)
    );
});
describe("formatting QWeb conditional branches (t-if, t-elif, t-else)", () => {
    describe("font size", () => {
        test("formatting a lone `t-if` wraps only that node and not the sibling span", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="cond" t-out="val">Value</t>]<span>other</span></p>`,
                { config }
            );
            setFontSize("12px")(editor);
            const span = el.querySelector("span[style]");
            expect(span).not.toBe(null);
            expect(span.querySelector("t[t-if]")).not.toBe(null);
            expect(span.querySelector("span:not([style])")).toBe(null);
        });

        test("formatting `t-if` also wraps its `t-else`", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="cond" t-out="a">A</t>]<t t-else="" t-out="b">B</t></p>`,
                { config }
            );
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper).not.toBe(null);
            expect(wrapper.querySelector("t[t-if]")).not.toBe(null);
            expect(wrapper.querySelector("t[t-else]")).not.toBe(null);
            expect(wrapper.children.length).toBe(2);
        });

        test("formatting `t-if` also wraps its `t-elif` and `t-else`", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-elif="b" t-out="b">B</t><t t-else="" t-out="c">C</t></p>`,
                { config }
            );
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper).not.toBe(null);
            expect(wrapper.querySelector("t[t-if]")).not.toBe(null);
            expect(wrapper.querySelector("t[t-elif]")).not.toBe(null);
            expect(wrapper.querySelector("t[t-else]")).not.toBe(null);
            expect(wrapper.children.length).toBe(3);
        });

        test("formatting `t-if` also wraps multiple `t-elif` and the `t-else`", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-elif="b" t-out="b">B</t><t t-elif="c" t-out="c">C</t><t t-else="" t-out="d">D</t></p>`,
                { config }
            );
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper).not.toBe(null);
            expect(wrapper.querySelector("t[t-if]")).not.toBe(null);
            expect(wrapper.querySelectorAll("t[t-elif]").length).toBe(2);
            expect(wrapper.querySelector("t[t-else]")).not.toBe(null);
            expect(wrapper.children.length).toBe(4);
        });

        test("formatting `t-else` also wraps its preceding `t-if`", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="cond" t-out="a">A</t>[<t t-else="" t-out="b">B</t>]</p>`,
                { config }
            );
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper).not.toBe(null);
            expect(wrapper.querySelector("t[t-if]")).not.toBe(null);
            expect(wrapper.querySelector("t[t-else]")).not.toBe(null);
            expect(wrapper.children.length).toBe(2);
        });

        test("formatting `t-elif` wraps the whole group (`t-if`, `t-elif`, `t-else`)", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t>[<t t-elif="b" t-out="b">B</t>]<t t-else="" t-out="c">C</t></p>`,
                { config }
            );
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper).not.toBe(null);
            expect(wrapper.querySelector("t[t-if]")).not.toBe(null);
            expect(wrapper.querySelector("t[t-elif]")).not.toBe(null);
            expect(wrapper.querySelector("t[t-else]")).not.toBe(null);
            expect(wrapper.children.length).toBe(3);
        });

        test("formatting `t-else` after multiple `t-elif` wraps the whole group", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t><t t-elif="b" t-out="b">B</t><t t-elif="c" t-out="c">C</t>[<t t-else="" t-out="d">D</t>]</p>`,
                { config }
            );
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper).not.toBe(null);
            expect(wrapper.querySelector("t[t-if]")).not.toBe(null);
            expect(wrapper.querySelectorAll("t[t-elif]").length).toBe(2);
            expect(wrapper.querySelector("t[t-else]")).not.toBe(null);
            expect(wrapper.children.length).toBe(4);
        });

        test("formatting the first group leaves the second group outside the wrapper", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-else="" t-out="b">B</t><t t-if="c" t-out="c">C</t><t t-else="" t-out="d">D</t></p>`,
                { config }
            );
            setFontSize("12px")(editor);
            const wrappers = el.querySelectorAll("span[style]");
            expect(wrappers.length).toBe(1);
            const wrapper = wrappers[0];
            expect(wrapper.querySelector("t[t-if]")).not.toBe(null);
            expect(wrapper.querySelector("t[t-else]")).not.toBe(null);
            const allTIf = el.querySelectorAll("t[t-if]");
            expect(allTIf.length).toBe(2);
            expect(wrapper.contains(allTIf[1])).toBe(false);
        });

        test("removing it restores `t-if` and `t-else` without any wrapper", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="cond" t-out="a">A</t>]<t t-else="" t-out="b">B</t></p>`,
                { config }
            );
            setFontSize("12px")(editor);
            setFontSize("")(editor);
            expect(el.querySelector("span[style]")).toBe(null);
            expect(el.querySelector("t[t-if]")).not.toBe(null);
            expect(el.querySelector("t[t-else]")).not.toBe(null);
        });

        test("removing it restores `t-if`, `t-elif` and `t-else` without any wrapper", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-elif="b" t-out="b">B</t><t t-else="" t-out="c">C</t></p>`,
                { config }
            );
            setFontSize("12px")(editor);
            setFontSize("")(editor);
            expect(el.querySelector("span[style]")).toBe(null);
            expect(el.querySelector("t[t-if]")).not.toBe(null);
            expect(el.querySelector("t[t-elif]")).not.toBe(null);
            expect(el.querySelector("t[t-else]")).not.toBe(null);
        });

        test("formatting the first of two consecutive `t-if` wraps only that one", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-if="b" t-out="b">B</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']")];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting the second of two consecutive `t-if` wraps only that one", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t>[<t t-if="b" t-out="b">B</t>]</p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='b']")];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting the middle of three consecutive `t-if` wraps only that one", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t>[<t t-if="b" t-out="b">B</t>]<t t-if="c" t-out="c">C</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='b']")];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-else` does not wrap a following `t-if`", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t>[<t t-else="" t-out="b">B</t>]<t t-if="c" t-out="c">C</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']"), el.querySelector("t[t-out='b']")];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-if` does not wrap a `t-if` that follows the `t-else`", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-else="" t-out="b">B</t><t t-if="c" t-out="c">C</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']"), el.querySelector("t[t-out='b']")];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting the `t-if` of a second group wraps only the second group", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t><t t-else="" t-out="b">B</t>[<t t-if="c" t-out="c">C</t>]<t t-else="" t-out="d">D</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='c']"), el.querySelector("t[t-out='d']")];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting the `t-else` of a second group does not reach into the first group", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t><t t-else="" t-out="b">B</t><t t-if="c" t-out="c">C</t>[<t t-else="" t-out="d">D</t>]</p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='c']"), el.querySelector("t[t-out='d']")];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-elif` does not wrap a following `t-if` group", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t>[<t t-elif="b" t-out="b">B</t>]<t t-else="" t-out="c">C</t><t t-if="d" t-out="d">D</t><t t-else="" t-out="e">E</t></p>`,
                { config }
            );
            const expected = [
                el.querySelector("t[t-out='a']"),
                el.querySelector("t[t-out='b']"),
                el.querySelector("t[t-out='c']"),
            ];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-elif` does not wrap a preceding group", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t><t t-else="" t-out="b">B</t><t t-if="c" t-out="c">C</t>[<t t-elif="d" t-out="d">D</t>]<t t-else="" t-out="e">E</t></p>`,
                { config }
            );
            const expected = [
                el.querySelector("t[t-out='c']"),
                el.querySelector("t[t-out='d']"),
                el.querySelector("t[t-out='e']"),
            ];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("a selection spanning two groups wraps all nodes of both groups", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t><t t-else="" t-out="b">B</t><t t-if="c" t-out="c">C</t><t t-else="" t-out="d">D</t>]</p>`,
                { config }
            );
            const expected = [
                el.querySelector("t[t-out='a']"),
                el.querySelector("t[t-out='b']"),
                el.querySelector("t[t-out='c']"),
                el.querySelector("t[t-out='d']"),
            ];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("a `t-else` separated from its `t-if` by another element is not wrapped", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<b>x</b><t t-else="" t-out="b">B</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']")];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting an orphan `t-else` wraps only that node", async () => {
            const { editor, el } = await setupEditor(
                `<p><span>x</span>[<t t-else="" t-out="b">B</t>]</p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='b']")];
            setFontSize("12px")(editor);
            const wrapper = el.querySelector("span[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("removing it from a selection spanning two groups restores both groups intact", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t><t t-else="" t-out="b">B</t><t t-if="c" t-out="c">C</t><t t-else="" t-out="d">D</t>]</p>`,
                { config }
            );
            const expected = [
                el.querySelector("t[t-out='a']"),
                el.querySelector("t[t-out='b']"),
                el.querySelector("t[t-out='c']"),
                el.querySelector("t[t-out='d']"),
            ];
            setFontSize("12px")(editor);
            setFontSize("")(editor);
            expect(el.querySelector("span[style]")).toBe(null);
            const p = el.querySelector("p");
            expect(p.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(p.children[i] === node).toBe(true));
        });
    });

    describe("bold", () => {
        test("formatting a lone `t-if` wraps only that node and not the sibling span", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<span>other</span></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']")];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-if` also wraps its `t-else`", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="cond" t-out="a">A</t>]<t t-else="" t-out="b">B</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']"), el.querySelector("t[t-out='b']")];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-if` also wraps its `t-elif` and `t-else`", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-elif="b" t-out="b">B</t><t t-else="" t-out="c">C</t></p>`,
                { config }
            );
            const expected = [
                el.querySelector("t[t-out='a']"),
                el.querySelector("t[t-out='b']"),
                el.querySelector("t[t-out='c']"),
            ];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-elif` wraps the whole group (`t-if`, `t-elif`, `t-else`)", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t>[<t t-elif="b" t-out="b">B</t>]<t t-else="" t-out="c">C</t></p>`,
                { config }
            );
            const expected = [
                el.querySelector("t[t-out='a']"),
                el.querySelector("t[t-out='b']"),
                el.querySelector("t[t-out='c']"),
            ];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-else` after multiple `t-elif` wraps the whole group", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t><t t-elif="b" t-out="b">B</t><t t-elif="c" t-out="c">C</t>[<t t-else="" t-out="d">D</t>]</p>`,
                { config }
            );
            const expected = [
                el.querySelector("t[t-out='a']"),
                el.querySelector("t[t-out='b']"),
                el.querySelector("t[t-out='c']"),
                el.querySelector("t[t-out='d']"),
            ];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-if` does not wrap a `t-if` that follows the `t-else`", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-else="" t-out="b">B</t><t t-if="c" t-out="c">C</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']"), el.querySelector("t[t-out='b']")];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting the first of two consecutive `t-if` wraps only that one", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-if="b" t-out="b">B</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']")];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting the middle of three consecutive `t-if` wraps only that one", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t>[<t t-if="b" t-out="b">B</t>]<t t-if="c" t-out="c">C</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='b']")];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting the `t-else` of a second group does not reach into the first group", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t><t t-else="" t-out="b">B</t><t t-if="c" t-out="c">C</t>[<t t-else="" t-out="d">D</t>]</p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='c']"), el.querySelector("t[t-out='d']")];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("a selection spanning two groups wraps all nodes of both groups", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t><t t-else="" t-out="b">B</t><t t-if="c" t-out="c">C</t><t t-else="" t-out="d">D</t>]</p>`,
                { config }
            );
            const expected = [
                el.querySelector("t[t-out='a']"),
                el.querySelector("t[t-out='b']"),
                el.querySelector("t[t-out='c']"),
                el.querySelector("t[t-out='d']"),
            ];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("a `t-else` separated from its `t-if` by another element is not wrapped", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<b>x</b><t t-else="" t-out="b">B</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']")];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting an orphan `t-else` wraps only that node", async () => {
            const { editor, el } = await setupEditor(
                `<p><span>x</span>[<t t-else="" t-out="b">B</t>]</p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='b']")];
            bold(editor);
            const wrapper = el.querySelector("strong");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("toggling it off restores `t-if` and `t-else` without any wrapper", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-else="" t-out="b">B</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']"), el.querySelector("t[t-out='b']")];
            bold(editor);
            bold(editor);
            expect(el.querySelector("strong")).toBe(null);
            const p = el.querySelector("p");
            expect(p.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(p.children[i] === node).toBe(true));
        });

        test("toggling it off on a selection spanning two groups restores both groups intact", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t><t t-else="" t-out="b">B</t><t t-if="c" t-out="c">C</t><t t-else="" t-out="d">D</t>]</p>`,
                { config }
            );
            const expected = [
                el.querySelector("t[t-out='a']"),
                el.querySelector("t[t-out='b']"),
                el.querySelector("t[t-out='c']"),
                el.querySelector("t[t-out='d']"),
            ];
            bold(editor);
            bold(editor);
            expect(el.querySelector("strong")).toBe(null);
            const p = el.querySelector("p");
            expect(p.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(p.children[i] === node).toBe(true));
        });
    });

    describe("color", () => {
        test("formatting a lone `t-if` wraps only that node and not the sibling span", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<span>other</span></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']")];
            setColor("red", "color")(editor);
            const wrapper = el.querySelector("font[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-if` also wraps its `t-else`", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-else="" t-out="b">B</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']"), el.querySelector("t[t-out='b']")];
            setColor("red", "color")(editor);
            const wrapper = el.querySelector("font[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-elif` wraps the whole group (`t-if`, `t-elif`, `t-else`)", async () => {
            const { editor, el } = await setupEditor(
                `<p><t t-if="a" t-out="a">A</t>[<t t-elif="b" t-out="b">B</t>]<t t-else="" t-out="c">C</t></p>`,
                { config }
            );
            const expected = [
                el.querySelector("t[t-out='a']"),
                el.querySelector("t[t-out='b']"),
                el.querySelector("t[t-out='c']"),
            ];
            setColor("red", "color")(editor);
            const wrapper = el.querySelector("font[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("formatting `t-if` does not wrap a `t-if` that follows the `t-else`", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-else="" t-out="b">B</t><t t-if="c" t-out="c">C</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']"), el.querySelector("t[t-out='b']")];
            setColor("red", "color")(editor);
            const wrapper = el.querySelector("font[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });

        test("removing it restores `t-if` and `t-else` without any wrapper", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-else="" t-out="b">B</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']"), el.querySelector("t[t-out='b']")];
            setColor("red", "color")(editor);
            setColor("", "color")(editor);
            expect(el.querySelector("font")).toBe(null);
            const p = el.querySelector("p");
            expect(p.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(p.children[i] === node).toBe(true));
        });

        test("removing it restores `t-if`, `t-elif` and `t-else` without any wrapper", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-elif="b" t-out="b">B</t><t t-else="" t-out="c">C</t></p>`,
                { config }
            );
            const expected = [
                el.querySelector("t[t-out='a']"),
                el.querySelector("t[t-out='b']"),
                el.querySelector("t[t-out='c']"),
            ];
            setColor("red", "color")(editor);
            setColor("", "color")(editor);
            expect(el.querySelector("font")).toBe(null);
            const p = el.querySelector("p");
            expect(p.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(p.children[i] === node).toBe(true));
        });

        test("removing it when none is applied leaves the structure untouched", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-else="" t-out="b">B</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']"), el.querySelector("t[t-out='b']")];
            setColor("", "color")(editor);
            expect(el.querySelector("font")).toBe(null);
            const p = el.querySelector("p");
            expect(p.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(p.children[i] === node).toBe(true));
        });
    });

    describe("background color", () => {
        test("formatting `t-if` also wraps its `t-else`", async () => {
            const { editor, el } = await setupEditor(
                `<p>[<t t-if="a" t-out="a">A</t>]<t t-else="" t-out="b">B</t></p>`,
                { config }
            );
            const expected = [el.querySelector("t[t-out='a']"), el.querySelector("t[t-out='b']")];
            setColor("red", "backgroundColor")(editor);
            const wrapper = el.querySelector("font[style]");
            expect(wrapper.children.length).toBe(expected.length);
            expected.forEach((node, i) => expect(wrapper.children[i] === node).toBe(true));
        });
    });
});
