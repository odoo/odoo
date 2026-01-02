import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    edit,
    hover,
    queryAll,
    queryOne,
    select,
    waitFor,
    waitForNone,
    manuallyDispatchProgrammaticEvent,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { setupEditor, testEditor } from "../_helpers/editor";
import { cleanLinkArtifacts, unformat } from "../_helpers/format";
import { getContent, setSelection } from "../_helpers/selection";
import { deleteBackward, insertText } from "../_helpers/user_actions";

describe("button style", () => {
    test("editable button should have cursor text", async () => {
        const { el } = await setupEditor(
            '<p><a href="#" class="btn btn-fill-primary">Link styled as button</a></p>'
        );

        const button = el.querySelector("a");
        expect(button).toHaveStyle({ cursor: "text" });
    });
    test("non-editable .btn-link should have cursor pointer", async () => {
        const { el } = await setupEditor(
            // A simpliflied version of an embedded component with toolbar
            // buttons, as it happens in certain flows in Knowledge.
            unformat(`
                <div contenteditable="false" data-embedded="clipboard">
                    <span class="o_embedded_toolbar">
                        <button class="btn">I am a button</button>
                    </span>
                </div>
            `)
        );
        const button = el.querySelector(".o_embedded_toolbar button");
        expect(button).toHaveStyle({ cursor: "pointer" });
    });
    test("editable button is user-selectable", async () => {
        await setupEditor('<p><a href="#" class="btn test-btn">button</a></p>');
        expect(queryOne(".test-btn")).toHaveStyle({ userSelect: "auto" });
    });
    test("non-editable button should not be user-selectable", async () => {
        const { el } = await setupEditor('<p><a href="#" class="btn test-btn">button</a></p>');
        el.setAttribute("contenteditable", "false");
        expect(queryOne(".test-btn")).toHaveStyle({ userSelect: "none" });
    });
    test("Button styling should not override inner font size", async () => {
        onRpc("/test", () => ({}));
        onRpc("/html_editor/link_preview_internal", () => ({
            description: "test",
            link_preview_name: "test",
        }));
        const { el } = await setupEditor(
            unformat(`
                <div>
                    <span class="display-1-fs">a[b]c</span>
                </div>
            `)
        );
        await waitFor(".o-we-toolbar");
        await click("button[name='link']");
        await animationFrame();
        await click('select[name="link_type"]');
        await animationFrame();
        await select("primary");
        await animationFrame();
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("/test");

        // Ensure `.display-1-fs` overrides the `.btn`'s default font size.
        const link = el.querySelector("a.btn");
        const span = el.querySelector("span.display-1-fs");
        expect(getComputedStyle(link).fontSize).toBe(getComputedStyle(span).fontSize);

        expect(el).toHaveInnerHTML(
            unformat(`
                <div class="o-paragraph">
                    <span class="display-1-fs">a\ufeff<a href="/test" class="btn btn-primary">\ufeffb\ufeff</a>\ufeffc</span>
                </div>
            `)
        );
    });

    test("Should be able to change button style", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div class="o-paragraph">
                    <span class="display-1-fs">a<a class="btn btn-fill-primary" href="#">[b]</a>c</span>
                </div>
            `),
            stepFunction: (editor) => {
                editor.shared.format.formatSelection("setFontSizeClassName", {
                    formatProps: { className: "h1-fs" },
                    applyStyle: true,
                });
            },
            contentAfter: unformat(`
                <div>
                    <span class="display-1-fs">
                        a
                        <a class="btn btn-fill-primary" href="#">
                            <span class="h1-fs">[b]</span>
                        </a>
                        c
                    </span>
                </div>
            `),
        });
    });
});

const allowCustomOpt = {
    config: {
        allowCustomStyle: true,
    },
};
const allowTargetBlankOpt = {
    config: {
        allowTargetBlank: true,
    },
};
describe("Custom button style", () => {
    test("Editor don't allow custom style by default", async () => {
        await setupEditor('<p><a href="https://test.com/">link[]Label</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        const optionsvalues = [...queryOne('select[name="link_type"]').options].map(
            (opt) => opt.label
        );
        expect(optionsvalues).toInclude("Link");
        expect(optionsvalues).toInclude("Button Primary");
        expect(optionsvalues).toInclude("Button Secondary");
        expect(optionsvalues).not.toInclude("Custom");
    });
    test("Editor allow button size style by default", async () => {
        await setupEditor(
            '<p><a href="https://test.com/" class="btn btn-primary">link[]Label</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        const optionsValues = [...queryOne('select[name="link_style_size"]').options].map(
            (opt) => opt.label
        );
        expect(optionsValues).toInclude("Small");
        expect(optionsValues).toInclude("Medium");
        expect(optionsValues).toInclude("Large");
    });
    test("Editor don't allow target blank style by default", async () => {
        await setupEditor('<p><a href="https://test.com/">link[]Label</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        const count = queryAll(".target-blank-option").length;
        expect(count).toBe(0);
    });

    test("Editor allow custom Style if config is active", async () => {
        await setupEditor('<p><a href="https://test.com/">link[]Label</a></p>', allowCustomOpt);
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        const optionsvalues = [...queryOne('select[name="link_type"]').options].map(
            (opt) => opt.label
        );
        expect(optionsvalues).toInclude("Link");
        expect(optionsvalues).toInclude("Button Primary");
        expect(optionsvalues).toInclude("Button Secondary");
        expect(optionsvalues).toInclude("Custom");
    });
    test("The link popover should load the current custom format correctly", async () => {
        await setupEditor(
            '<p><a href="https://test.com/" class="btn btn-custom" style="color: rgb(0, 255, 0); background-color: rgb(0, 0, 255); border-width: 4px; border-color: rgb(255, 0, 0); border-style: dotted;">link[]Label</a></p>',
            allowCustomOpt
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        expect(".o_we_label_link").toHaveValue("linkLabel");
        expect(".o_we_href_input_link").toHaveValue("https://test.com/");
        expect(queryOne('select[name="link_type"]').selectedOptions[0].value).toBe("custom");
        expect(queryOne(".custom-text-picker").style.backgroundColor).toBe("rgb(0, 255, 0)");
        expect(queryOne(".custom-fill-picker").style.backgroundColor).toBe("rgb(0, 0, 255)");
        expect(queryOne(".custom-border-picker").style.backgroundColor).toBe("rgb(255, 0, 0)");
        expect(queryOne(".custom-border-size").value).toBe("4");
        expect(queryOne(".custom-border-style").value).toBe("dotted");
    });

    test.tags("desktop");
    test("The color preview should be reset after cursor is out of the colorpicker", async () => {
        await setupEditor(
            '<p><a href="https://test.com/" class="btn btn-custom" style="color: rgb(0, 255, 0); background-color: rgb(0, 0, 255); border-width: 4px; border-color: rgb(255, 0, 0); border-style: dotted;">link[]Label</a></p>',
            allowCustomOpt
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        await click(".custom-fill-picker");
        await animationFrame();
        await hover(".o_color_button[data-color='#00FF00']");
        await animationFrame();

        expect(queryOne(".custom-fill-picker").style.backgroundColor).toBe("rgb(0, 255, 0)");

        await hover(".custom-fill-picker"); // cursor out of the colorpicker
        await animationFrame();

        expect(queryOne(".custom-fill-picker").style.backgroundColor).toBe("rgb(0, 0, 255)");
    });

    test("should convert all selected text to a custom button", async () => {
        const { el } = await setupEditor("<p>[Hello]</p>", allowCustomOpt);
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("http://test.test/", {
            confirm: false,
        });
        await click('select[name="link_type"]');
        await select("custom");
        await animationFrame();

        await click(".custom-text-picker");
        await animationFrame();
        await click(".o_color_button[data-color='#FF0000']");
        await animationFrame();

        await click(".custom-fill-picker");
        await animationFrame();
        await click(".o_color_button[data-color='#00FF00']");
        await animationFrame();

        await click("input.custom-border-size");
        await edit("1");

        await click(waitFor(".custom-border-picker"));
        await animationFrame();
        await click(".o_color_button[data-color='#0000FF']");
        await animationFrame();

        await contains(".custom-border input.custom-border-size").edit("6", {
            confirm: false,
        });

        await click('select[name="link_style_border"]');
        await select("dotted");
        await animationFrame();

        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/" class="btn btn-custom" style="color: #FF0000; background-color: #00FF00; border-width: 6px; border-color: #0000FF; border-style: dotted; ">Hello</a></p>'
        );

        await click(".o_we_apply_link");
        await animationFrame();

        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/" class="btn btn-custom" style="color: #FF0000; background-color: #00FF00; border-width: 6px; border-color: #0000FF; border-style: dotted; ">Hello[]</a></p>'
        );
    });

    test("should allow target _blank on custom button", async () => {
        const { el } = await setupEditor("<p>[Hello]</p>", allowTargetBlankOpt);
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("http://test.test/", {
            confirm: false,
        });
        await click(".o-we-linkpopover .fa-gear");
        await contains(".o_advance_option_panel .target-blank-option").click();
        await click(".o_advance_option_panel .fa-angle-left");
        await waitFor(".o-we-linkpopover");

        await animationFrame();
        await click(".o_we_apply_link");
        await animationFrame();

        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/" target="_blank">Hello[]</a></p>'
        );
    });

    test("Editor allow custom shape if config is active", async () => {
        const { el } = await setupEditor(
            '<p><a href="https://test.com/">link[]Label</a></p>',
            allowCustomOpt
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        await click('select[name="link_type"]');
        await select("custom");
        await animationFrame();

        // test outline
        await click('select[name="link_style_shape"]');
        await select("outline");
        await animationFrame();
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="https://test.com/" class="btn btn-outline-custom" style="color: rgb(0, 0, 0); background-color: rgb(166, 227, 226); border-width: 1px; border-color: rgb(0, 143, 140); border-style: dashed; ">linkLabel</a></p>'
        );

        // test fill + rounded
        await click('select[name="link_style_shape"]');
        await select("fill rounded-circle");
        await animationFrame();
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="https://test.com/" class="rounded-circle btn btn-fill-custom" style="color: rgb(0, 0, 0); background-color: rgb(166, 227, 226); border-width: 1px; border-color: rgb(0, 143, 140); border-style: dashed; ">linkLabel</a></p>'
        );

        await click(".o_we_apply_link");
        await animationFrame();
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="https://test.com/" class="rounded-circle btn btn-fill-custom" style="color: rgb(0, 0, 0); background-color: rgb(166, 227, 226); border-width: 1px; border-color: rgb(0, 143, 140); border-style: dashed; ">link[]Label</a></p>'
        );
    });
});

describe("button edit", () => {
    test("button link should be editable with double click select", async () => {
        const { el, editor } = await setupEditor(
            '<p>this is a <a href="http://test.test/">link</a></p>'
        );
        await waitForNone(".o-we-linkpopover");
        const button = el.querySelector("a");
        // simulate double click selection
        setSelection({ anchorNode: button, anchorOffset: 0 });
        manuallyDispatchProgrammaticEvent(button, "mousedown", { detail: 2 });
        await animationFrame();
        expect(getContent(el)).toBe(
            '<p>this is a \ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[link]\ufeff</a>\ufeff</p>'
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.test/">[link]</a></p>'
        );
        await insertText(editor, "X");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.test/">X[]</a></p>'
        );
    });

    test("double click select on a link should stay inside the link (1)", async () => {
        const { el } = await setupEditor(
            '<p>this is a <a href="http://test.test/">test b[]tn</a><a href="http://test2.test/">test btn2</a></p>'
        );
        const link = el.querySelector("a[href='http://test.test/']");
        // simulate double click selection
        manuallyDispatchProgrammaticEvent(link, "mousedown", { detail: 2 });
        await animationFrame();
        expect(getContent(el)).toBe(
            '<p>this is a \ufeff<a href="http://test.test/" class="o_link_in_selection">\ufefftest [btn]\ufeff</a>\ufeff<a href="http://test2.test/">\ufefftest btn2\ufeff</a>\ufeff</p>'
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.test/">test [btn]</a><a href="http://test2.test/">test btn2</a></p>'
        );
    });

    test("double click select on a link should stay inside the link (2)", async () => {
        const { el } = await setupEditor(
            '<p>this is a <a href="http://test.test/">test btn</a><a href="http://test2.test/">t[]est btn2</a></p>'
        );
        const link = el.querySelector("a[href='http://test2.test/']");
        // simulate double click selection
        manuallyDispatchProgrammaticEvent(link, "mousedown", { detail: 2 });
        await animationFrame();
        expect(getContent(el)).toBe(
            '<p>this is a \ufeff<a href="http://test.test/">\ufefftest btn\ufeff</a>\ufeff<a href="http://test2.test/" class="o_link_in_selection">\ufeff[test] btn2\ufeff</a>\ufeff</p>'
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.test/">test btn</a><a href="http://test2.test/">[test] btn2</a></p>'
        );
    });

    test("triple click select should select the full button text", async () => {
        const { el, editor } = await setupEditor(
            '<p>this is a <a href="http://test.test/" class="btn btn-fill-primary">test b[]tn</a></p>'
        );
        const button = el.querySelector("a");
        // simulate triple click selection
        manuallyDispatchProgrammaticEvent(button, "mousedown", { detail: 3 });
        await animationFrame();
        expect(getContent(el)).toBe(
            '<p>this is a \ufeff<a href="http://test.test/" class="btn btn-fill-primary">[\ufefftest btn\ufeff]</a>\ufeff</p>'
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.test/" class="btn btn-fill-primary">[test btn]</a></p>'
        );
        await insertText(editor, "X");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.test/" class="btn btn-fill-primary">X[]</a></p>'
        );
    });

    test("Should not remove invisible button", async () => {
        const { el } = await setupEditor(
            '<p><a href="http://test.test/" class="invisible btn btn-primary">a[]</a></p>',
            {
                styleContent: `
                    .invisible {
                        visibility: hidden;
                    }
                `,
            }
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");

        await contains(".o-we-linkpopover input.o_we_label_link").fill("b");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/" class="invisible btn btn-primary">ab[]</a></p>'
        );
    });
});

test("button should never contain selection placeholder", async () => {
    await testEditor({
        contentBefore:
            '<button style="display: block" contenteditable="true"><div style="display: block" contenteditable="false">a</div></button>',
        contentBeforeEdit:
            '<button style="display: block" contenteditable="true"><div style="display: block" contenteditable="false">a</div></button>',
    });
});

test.tags("firefox");
describe("firefox", () => {
    test("text should be inserted inside link after backspace", async () => {
        const { el, editor } = await setupEditor('<p><a href="#">link</a>t[]est</p>');
        deleteBackward(editor);
        deleteBackward(editor);
        await insertText(editor, "X");
        expect(cleanLinkArtifacts(getContent(el))).toBe('<p><a href="#">linX[]</a>est</p>');
    });
});
