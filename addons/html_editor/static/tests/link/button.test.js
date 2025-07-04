import { describe, expect, test } from "@odoo/hoot";
import { click, queryOne, queryAll, select, waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "../_helpers/editor";
import { cleanLinkArtifacts, unformat } from "../_helpers/format";
import { contains } from "../../../../web/static/tests/_framework/dom_test_helpers";
import { getContent, simulateDoubleClickSelect } from "../_helpers/selection";
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
    test("Editor allow target blank style if config is active", async () => {
        await setupEditor(
            '<p><a href="https://test.com/">link[]Label</a></p>',
            allowTargetBlankOpt
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        await waitFor(".target-blank-option");
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

        await click(".custom-border-picker");
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
            '<p><a href="http://test.test/" class="btn btn-fill-custom" style="color: #FF0000; background-color: #00FF00; border-width: 6px; border-color: #0000FF; border-style: dotted; ">Hello</a></p>'
        );

        await click(".o_we_apply_link");
        await animationFrame();

        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/" class="btn btn-fill-custom" style="color: #FF0000; background-color: #00FF00; border-width: 6px; border-color: #0000FF; border-style: dotted; ">Hello[]</a></p>'
        );
    });

    test("should allow target _blank on custom button", async () => {
        const { el } = await setupEditor("<p>[Hello]</p>", allowTargetBlankOpt);
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("http://test.test/", {
            confirm: false,
        });

        await click(".target-blank-option input[type='checkbox']");
        await animationFrame();
        await click(".o_we_apply_link");
        await animationFrame();

        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/" target="_blank">Hello[]</a></p>'
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
        await simulateDoubleClickSelect(button);
        expect(getContent(el)).toBe(
            '<p>this is a \ufeff<a href="http://test.test/" class="o_link_in_selection">[\ufefflink]\ufeff</a>\ufeff</p>'
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.test/">[link]</a></p>'
        );
        await insertText(editor, "X");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.test/">X[]</a></p>'
        );
    });
});
