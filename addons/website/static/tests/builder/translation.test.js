import { Builder } from "@html_builder/builder";
import { EditWebsiteSystrayItem } from "@website/client_actions/website_preview/edit_website_systray_item";
import { setContent, setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, manuallyDispatchProgrammaticEvent, queryAllTexts } from "@odoo/hoot-dom";
import { contains, mockService, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, invisibleEl, setupWebsiteBuilder } from "./website_helpers";
import { expectElementCount } from "@html_editor/../tests/_helpers/ui_expectations";

defineWebsiteModels();

const websiteServiceInTranslateMode = {
    currentWebsite: {
        metadata: {
            lang: "fr_BE",
            langName: " Français (BE)",
            translatable: true,
            defaultLangName: "English (US)",
        },
        default_lang_id: {
            code: "en_US",
        },
    },
    // Minimal context to avoid crashes.
    context: { showNewContentModal: false },
    websites: [
        {
            id: 1,
            metadata: {},
        },
    ],
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
                default_lang_id: {
                    code: "en_US",
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
    expect(".o-snippets-tabs button:contains('Add')").toHaveAttribute("disabled");
    expect(".o-snippets-tabs button:contains('THEME')").toHaveAttribute("disabled");
    expect(".o-snippets-tabs button:contains('Edit')").toHaveClass("active");
    expect(".o-snippets-tabs button:contains('Edit')").not.toHaveAttribute("disabled");
});

test("invisible elements in translate mode", async () => {
    await setupSidebarBuilderForTranslation({ websiteContent: invisibleEl });
    expect(
        ".o_we_invisible_el_panel  .o_we_invisible_entry:contains('Invisible Element')"
    ).toHaveCount(1);
});

test("show invisible elements in translate mode", async () => {
    await setupSidebarBuilderForTranslation({ websiteContent: invisibleEl });

    expect(":iframe .o_snippet_invisible").toHaveAttribute("data-invisible", "1");
    await contains(
        ".o_we_invisible_el_panel  .o_we_invisible_entry:contains('Invisible Element') i.fa-eye-slash"
    ).click();
    expect(":iframe .o_snippet_invisible").not.toHaveAttribute("data-invisible");
});

test("translate text", async () => {
    const resultSave = [];
    onRpc("/web_editor/field/translation/update", async (data) => {
        const { params } = await data.json();
        resultSave.push(params.translations.fr_BE.sourceSha);
        return true;
    });
    const { getEditor } = await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable({ inWrap: "Hello" }),
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
        websiteContent: getTranslateEditable({ inWrap: "Hello" }),
    });
    const editor = getEditor();
    setContent(editor.editable.querySelector("#wrap"), getTranslateEditable({ inWrap: "Hello[]" }));
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
            this.websiteContext = this.websiteService.context;
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
            <img src="/web/image/website.s_text_image_default_image" class="img img-fluid mx-auto rounded o_editable" loading="lazy" title="<span data-oe-model=&quot;ir.ui.view&quot; data-oe-id=&quot;544&quot; data-oe-field=&quot;arch_db&quot; data-oe-translation-state=&quot;to_translate&quot; data-oe-translation-source-sha=&quot;sourceSha&quot;>title</span>" style=""></img>
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
            <img src="/web/image/website.s_text_image_default_image" class="img img-fluid o_editable" loading="lazy" title="<span data-oe-model=&quot;ir.ui.view&quot; data-oe-id=&quot;544&quot; data-oe-field=&quot;arch_db&quot; data-oe-translation-state=&quot;to_translate&quot; data-oe-translation-source-sha=&quot;sourceSha&quot;>title</span>" style=""></img>
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
        }" loading="lazy" title="${titleName}" style="" data-oe-translation-state="to_translate"></img>`;
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

test("test that powerbox should not open in translate mode", async () => {
    const { getEditor } = await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable("&nbsp;"),
    });
    const editor = getEditor();
    const textNode = editor.editable.querySelector("span").firstChild;
    expect(textNode.nodeType).toBe(Node.TEXT_NODE);
    setSelection({ anchorNode: textNode, anchorOffset: 0 });
    await animationFrame();
    // Simulate typing `/`
    await insertText(editor, "/");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 0);
});

describe("save translation", () => {
    beforeEach(async () => {
        onRpc("/web_editor/field/translation/update", async (data) => {
            const { params } = await data.json();
            expect.step(params.translations.fr_BE);
            return true;
        });
    });
    const srcSha1 = "srcSha1";
    const srcSha2 = "srcSha2";
    async function modifyBothTextsAndSave(editor) {
        await contains(".modal .btn:contains(Ok, never show me this again)").click();
        const textFirstNode = editor.editable.querySelector(
            `[data-oe-translation-source-sha=${srcSha1}]`
        ).firstChild;
        setSelection({ anchorNode: textFirstNode, anchorOffset: 1 });
        await insertText(editor, "1");
        const textSecondNode = editor.editable.querySelector(
            `[data-oe-translation-source-sha=${srcSha2}]`
        ).firstChild;
        setSelection({ anchorNode: textSecondNode, anchorOffset: 1 });
        await insertText(editor, "1");
        await contains(".o-snippets-top-actions button:contains(Save)").click();
    }

    test("save translation of contents of the same view", async () => {
        const { getEditor } = await setupSidebarBuilderForTranslation({
            websiteContent: `${getTranslateEditable({
                inWrap: "abc",
                sourceSha: srcSha1,
            })} ${getTranslateEditable({ inWrap: "def", sourceSha: srcSha2 })}`,
        });
        await modifyBothTextsAndSave(getEditor());
        expect.verifySteps([{ srcSha1: "a1bc", srcSha2: "d1ef" }]);
    });

    test("save translation of contents of different views", async () => {
        const { getEditor } = await setupSidebarBuilderForTranslation({
            websiteContent: `${getTranslateEditable({
                inWrap: "abc",
                oeId: 1,
                sourceSha: srcSha1,
            })} ${getTranslateEditable({ inWrap: "def", oeId: 2, sourceSha: srcSha2 })}`,
        });
        await modifyBothTextsAndSave(getEditor());
        expect.verifySteps([{ srcSha1: "a1bc" }, { srcSha2: "d1ef" }]);
    });
});

function getTranslateEditable({ inWrap, oeId = "526", sourceSha = "sourceSha" }) {
    return `
        <div class="container s_allow_columns">
            <p>
                <span data-oe-model="ir.ui.view" data-oe-id="${oeId}" data-oe-field="arch_db" data-oe-translation-state="to_translate" data-oe-translation-source-sha="${sourceSha}" class="o_editable">${inWrap}</span>
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
            this.websiteContext = this.websiteService.context;
        },
    });
    const { getEditor, getEditableContent, openBuilderSidebar } = await setupWebsiteBuilder(
        websiteContent,
        {
            openEditor: false,
            translateMode: true,
            onIframeLoaded: (iframe) => {
                websiteServiceInTranslateMode.pageDocument = iframe.contentDocument;
            },
        }
    );
    await openBuilderSidebar();
    return { getEditor, getEditableContent };
}
