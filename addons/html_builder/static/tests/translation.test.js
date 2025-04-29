import { Builder } from "@html_builder/builder";
import { WebsiteBuilder } from "@html_builder/website_preview/website_builder_action";
import { EditWebsiteSystrayItem } from "@html_builder/website_preview/edit_website_systray_item";
import { setContent, setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { animationFrame, manuallyDispatchProgrammaticEvent, queryAllTexts } from "@odoo/hoot-dom";
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
    onRpc("/web_editor/field/translation/update", async (data) => {
        const { params } = await data.json();
        resultSave.push(params.translations.fr_BE.sourceSha);
        return true;
    });
    const { getEditor } = await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable("Hello"),
    });
    const editor = getEditor();
    const textNode = editor.editable.querySelector("span").firstChild;
    setSelection({ anchorNode: textNode, anchorOffset: 1 });
    await insertText(editor, "1");
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect(resultSave.length).toBe(1);
    expect(resultSave[0]).toBe("H1ello");
});

test("add text in translate mode do not split", async () => {
    const { getEditor } = await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable("Hello"),
    });
    const editor = getEditor();
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

test("translate attribute", async () => {
    const resultSave = [];
    onRpc("/web_editor/field/translation/update", async (data) => {
        const { params } = await data.json();
        resultSave.push(params.translations.fr_BE.sourceSha);
        return true;
    });
    onRpc("ir.ui.view", "save", ({ args }) => true);
    await setupSidebarBuilderForTranslation({
        websiteContent: `
            <img src="/web/image/website.s_text_image_default_image" class="img img-fluid mx-auto rounded o_editable" loading="lazy" title="<span data-oe-model=&quot;ir.ui.view&quot; data-oe-id=&quot;544&quot; data-oe-field=&quot;arch_db&quot; data-oe-translation-state=&quot;to_translate&quot; data-oe-translation-source-sha=&quot;sourceSha&quot;>title</span>" style="" contenteditable="false"></img>
        `,
    });
    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    await contains(":iframe img").click();
    await contains(".modal .modal-body input").edit("titre");
    await contains(".modal .btn:contains(Ok)").click();
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect(resultSave.length).toBe(1);
    expect(resultSave[0]).toBe("titre");
});

test("translate attribute history", async () => {
    const { getEditableContent } = await setupSidebarBuilderForTranslation({
        websiteContent: `
            <img src="/web/image/website.s_text_image_default_image" class="img img-fluid o_editable" loading="lazy" title="<span data-oe-model=&quot;ir.ui.view&quot; data-oe-id=&quot;544&quot; data-oe-field=&quot;arch_db&quot; data-oe-translation-state=&quot;to_translate&quot; data-oe-translation-source-sha=&quot;sourceSha&quot;>title</span>" style="" contenteditable="false"></img>
        `,
    });
    const editable = getEditableContent();
    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    await contains(":iframe img").click();
    await contains(".modal .modal-body input").edit("titre");
    await contains(".modal .btn:contains(Ok)").click();
    const getImg = ({ titleName, translated }) =>
        `<img src="/web/image/website.s_text_image_default_image" class="img img-fluid o_editable o_translatable_attribute${
            translated ? " oe_translated" : ""
        }" loading="lazy" title="${titleName}" style="" contenteditable="false" data-oe-translation-state="to_translate"></img>`;
    expect(editable).toHaveInnerHTML(getImg({ titleName: "titre", translated: true }));
    await contains(".o-snippets-menu button.fa-undo").click();
    expect(editable).toHaveInnerHTML(getImg({ titleName: "title", translated: false }));
    await contains(":iframe img").click();
    expect(".modal .modal-body input").toHaveValue("title");
});

test("translate select", async () => {
    await setupSidebarBuilderForTranslation({
        websiteContent: `
            <div class="row s_col_no_resize s_col_no_bgcolor">
                <label class="col-form-label col-sm-auto s_website_form_label">
                    <span data-oe-model="ir.ui.view" data-oe-id="544" data-oe-field="arch_db" data-oe-translation-state="to_translate" data-oe-translation-source-sha="sourceSha" class="o_editable">
                        <span class="s_website_form_label_content">Custom Text</span>
                    </span>
                    </label>
                <div class="col-sm">
                    <span data-oe-model="ir.ui.view" data-oe-id="544" data-oe-field="arch_db" data-oe-translation-state="to_translate" data-oe-translation-source-sha="sourceSha" class="o_editable">
                        <select class="form-select s_website_form_input" name="Custom Text" id="oojm1tjo6m19">
                            <option id="optionId1" value="Option 1">Option 1</option>
                            <option id="optionId2" value="Option 2">Option 2</option>
                        </select>
                    </span>
                </div>
            </div>
        `,
    });
    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    await contains(":iframe [data-initial-translation-value='Option 1']").click();
    await contains(".modal .modal-body input").edit("Option fr");
    await contains(".modal .btn:contains('Ok')").click();
    expect(queryAllTexts(":iframe [data-initial-translation-value='Option 1']")).toEqual([
        "Option fr",
    ]);
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
    const { websiteContent } = options;
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
    const { getEditor, getEditableContent, getIframeEl, openBuilderSidebar } =
        await setupWebsiteBuilder(websiteContent, {
            openEditor: false,
        });
    websiteServiceInTranslateMode.pageDocument = getIframeEl().contentDocument;
    await openBuilderSidebar();
    return { getEditor, getEditableContent };
}
