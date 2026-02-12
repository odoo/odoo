import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    queryAll,
    queryOne,
    waitFor,
    waitForNone,
    manuallyDispatchProgrammaticEvent,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { setupEditor, testEditor } from "../_helpers/editor";
import { cleanLinkArtifacts, unformat } from "../_helpers/format";
import { getContent, setSelection } from "../_helpers/selection";
import { insertText } from "../_helpers/user_actions";

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
        await click("button[name='link_type']");
        await animationFrame();
        await click(".o-we-link-type-dropdown .dropdown-item:contains('Button Primary')");
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
        await click("button[name='link_type']");
        await animationFrame();
        const dropdownItems = queryAll(".o-we-link-type-dropdown .dropdown-item");
        const labels = dropdownItems.map((item) => item.textContent.trim());
        expect(labels).toInclude("Link");
        expect(labels).toInclude("Button Primary");
        expect(labels).toInclude("Button Secondary");
        expect(labels).not.toInclude("Custom");
    });
    test("Editor allow button size style by default", async () => {
        await setupEditor(
            `<p><a href="https://test.com/" class="btn btn-primary">link[]Label</a></p>`
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        const optionsValues = [...queryOne("select[name='link_style_size']").options].map(
            (opt) => opt.label
        );
        expect(optionsValues).toInclude("Small");
        expect(optionsValues).toInclude("Medium");
        expect(optionsValues).toInclude("Large");
    });

    test("Editor allow button shape style by default", async () => {
        await setupEditor(
            `<p><a href="https://test.com/" class="btn btn-primary">link[]Label</a></p>`
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        const optionsValues = [...queryOne("select[name='link_style_shape']").options].map(
            (opt) => opt.label
        );
        expect(optionsValues).toInclude("Default");
        expect(optionsValues).toInclude("Default + Rounded");
        expect(optionsValues).toInclude("Outline");
        expect(optionsValues).toInclude("Outline + Rounded");
        expect(optionsValues).toInclude("Fill");
        expect(optionsValues).toInclude("Fill + Rounded");
        expect(optionsValues).toInclude("Flat");
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
        await setupEditor('<p><a href="https://test.com/">link[]Label</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        await click("button[name='link_type']");
        await animationFrame();
        const dropdownItems = queryAll(".o-we-link-type-dropdown .dropdown-item");
        const labels = dropdownItems.map((item) => item.textContent.trim());
        expect(labels).toInclude("Link");
        expect(labels).toInclude("Button Primary");
        expect(labels).toInclude("Button Secondary");
        expect(labels).not.toInclude("Custom");
    });

    test("should convert selected text to a button", async () => {
        const { el } = await setupEditor("<p>[Hello]</p>");

        await contains(".o-we-toolbar .fa-link").click();
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("http://test.test/", {
            confirm: false,
        });

        await contains("button[name='link_type']").click();
        await contains(
            ".o-we-link-type-dropdown .dropdown-item:contains('Button Primary')"
        ).click();
        await contains("select[name='link_style_size']").select("lg");
        await contains("select[name='link_style_shape']").select("fill rounded-circle");

        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/" class="btn btn-lg rounded-circle btn-fill-primary">Hello</a></p>'
        );

        await contains(".o_we_apply_link").click();

        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/" class="btn btn-lg rounded-circle btn-fill-primary">Hello[]</a></p>'
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

    test("Editor allow custom shape", async () => {
        await setupEditor('<p><a href="https://test.com/">link[]Label</a></p>');
        const a = queryOne("p > a");

        await contains(".o-we-linkpopover .o_we_edit_link").click();
        await contains("button[name='link_type']").click();
        await contains(".dropdown-item span:contains('Button Primary')").click();

        // test outline
        await contains('select[name="link_style_shape"]').select("outline");
        expect(a).toHaveClass("btn btn-outline-primary");

        // test fill + rounded
        await contains('select[name="link_style_shape"]').select("fill rounded-circle");
        expect(a).toHaveClass("btn btn-fill-primary rounded-circle");

        await contains(".o_we_apply_link").click();

        expect(a).toHaveClass("btn btn-fill-primary rounded-circle");
        expect(cleanLinkArtifacts(getContent(a))).toBe("link[]Label");
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
