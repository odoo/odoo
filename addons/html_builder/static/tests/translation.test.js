import { Builder } from "@html_builder/builder";
import { WebsiteBuilder } from "@html_builder/website_preview/website_builder_action";
import { EditWebsiteSystrayItem } from "@html_builder/website_preview/edit_website_systray_item";
import { setContent, setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { animationFrame, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { contains, mockService, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, invisibleEl, setupWebsiteBuilder } from "./website_helpers";

defineWebsiteModels();

const websiteServiceInTranslateMode = {
    currentWebsite: {
        metadata: {
            lang: "fr_BE",
            langName: " Français (BE)",
            translatable: true,
            defaultLangName: "English (US)",
        },
    },
    // Minimal context to avoid crashes.
    context: { showNewContentModal: false },
};

test("systray in translate mode", async () => {
    mockService("website", {
        get currentWebsite() {
            return {
                metadata: {
                    lang: "fr_BE",
                    langName: " Français (BE)",
                    translatable: true,
                    defaultLangName: "English (US)",
                },
            };
        },
    });
    await setupWebsiteBuilder(`<h1> Homepage </h1>`, { openEditor: false });
    await contains(".o-website-btn-custo-primary").click();
    expect(".o_popover .o_translate_website_dropdown_item:contains('Translate')").toHaveCount(1);
    expect(".o_popover .o_edit_website_dropdown_item:contains('Edit')").toHaveCount(1);
});

test("snippets menu in translate mode", async () => {
    await setupSidebarBuilderForTranslation({ websiteContent: `<h1> Homepage </h1>` });
    expect(".o-snippets-tabs button:contains('BLOCKS')").toHaveAttribute("disabled");
    expect(".o-snippets-tabs button:contains('THEME')").toHaveAttribute("disabled");
    expect(".o-snippets-tabs button:contains('CUSTOMIZE')").toHaveClass("active");
    expect(".o-snippets-tabs button:contains('CUSTOMIZE')").not.toHaveAttribute("disabled");
});

test("invisible elements in translate mode", async () => {
    await setupSidebarBuilderForTranslation({ websiteContent: invisibleEl });
    expect(
        ".o_we_invisible_el_panel  .o_we_invisible_entry:contains('Invisible Element')"
    ).toHaveCount(1);
});

test("translate text", async () => {
    const resultSave = [];
    onRpc("ir.ui.view", "web_update_field_translations", ({ args }) => {
        resultSave.push(args[2]["fr_BE"]["sourceSha"]);
        return true;
    });
    const editor = await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable("Hello"),
    });
    const textNode = editor.editable.querySelector("span").firstChild;
    setSelection({ anchorNode: textNode, anchorOffset: 1 });
    await insertText(editor, "1");
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect(resultSave.length).toBe(1);
    expect(resultSave[0]).toBe("H1ello");
});

test("add text in translate mode do not split", async () => {
    const editor = await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable("Hello"),
    });
    setContent(editor.editable.querySelector("#wrap"), getTranslateEditable("Hello[]"));
    // Event trigger when you press "Enter" => create a new paragraph
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    await insertText(editor, "1");
    await animationFrame();
    expect(":iframe .s_allow_columns p").toHaveCount(1);
});

test("404 page in translate mode", async () => {
    patchWithCleanup(EditWebsiteSystrayItem.prototype, {
        setup() {
            websiteServiceInTranslateMode.is404 = () => true;
            this.websiteService = websiteServiceInTranslateMode;
        },
    });
    await setupWebsiteBuilder(`<h1> Homepage </h1>`, { openEditor: false });
    await contains(".o-website-btn-custo-primary").click();
    expect(
        ".o_popover .o_translate_website_dropdown_item:contains('Translate 404 page')"
    ).toHaveCount(1);
    expect(".o_popover .o_edit_website_dropdown_item:contains('Edit 404 page')").toHaveCount(1);
    expect(".o_popover .o_edit_website_dropdown_item:contains('Create page')").toHaveCount(1);
});

function getTranslateEditable(inWrap) {
    return `
        <div class="container s_allow_columns">
            <p>
                <span data-oe-model="ir.ui.view" data-oe-id="526" data-oe-field="arch_db" data-oe-translation-state="to_translate" data-oe-translation-source-sha="sourceSha" class="o_editable">${inWrap}</span>
            </p>
        </div>`;
}

async function setupSidebarBuilderForTranslation(options) {
    const { websiteContent, openEditor = true } = options;
    // Hack: configure the snippets menu as in translate mode when clicking
    // on the "Edit" button of the systray. The goal of this hack is to avoid
    // the handling of an extra reload of the action to arrive in translate
    // mode.
    patchWithCleanup(Builder.prototype, {
        setup() {
            super.setup();
            this.env.services.website = websiteServiceInTranslateMode;
            this.websiteService = websiteServiceInTranslateMode;
        },
    });
    patchWithCleanup(WebsiteBuilder.prototype, {
        setup() {
            super.setup();
            this.translation = true;
        },
    });
    const { getEditor } = await setupWebsiteBuilder(websiteContent, { openEditor: openEditor });
    return getEditor();
}
