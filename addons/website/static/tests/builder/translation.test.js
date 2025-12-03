import { Builder } from "@html_builder/builder";
import { EditWebsiteSystrayItem } from "@website/client_actions/website_preview/edit_website_systray_item";
import { setContent, setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText, pasteHtml, pasteText } from "@html_editor/../tests/_helpers/user_actions";
import { beforeEach, delay, describe, expect, globals, press, test } from "@odoo/hoot";
import {
    animationFrame,
    manuallyDispatchProgrammaticEvent,
    queryAllTexts,
    queryOne,
} from "@odoo/hoot-dom";
import { contains, mockService, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    getStructureSnippet,
    invisibleEl,
    setupWebsiteBuilder,
} from "./website_helpers";
import { expectElementCount } from "@html_editor/../tests/_helpers/ui_expectations";
import { uniqueId } from "@web/core/utils/functions";
import { TranslationPlugin } from "@website/builder/plugins/translation_plugin";
import { dummyBase64Img } from "@html_builder/../tests/helpers";
import { getTranslatedElements } from "./translated_elements_getter.hoot";

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
    context: {},
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

test("hide snippets menu in translate mode", async () => {
    await setupSidebarBuilderForTranslation({ websiteContent: `<h1> Homepage </h1>` });
    expect(".o-snippets-tabs").toHaveCount(0);
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
    onRpc("/website/field/translation/update", async (data) => {
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

test("only have translation editors on deepest nodes", async () => {
    await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable({
            inWrap: getTranslateEditable({ inWrap: "Hello" }).match(/<span.*<\/span>/)[0],
        }),
    });
    expect(":iframe [data-oe-model]:has([data-oe-model])").not.toHaveAttribute("contenteditable");
    expect(":iframe [data-oe-model] [data-oe-model]").toHaveAttribute("contenteditable", "true");
});

test("translate field", async () => {
    onRpc("ir.ui.view", "save", ({ args }) => {
        expect.step(args[1]);
        return true;
    });
    const { getEditor } = await setupSidebarBuilderForTranslation({
        websiteContent: `
            <div data-oe-model="test" data-oe-field="field" data-oe-id="1"><p id="sectionId">Title</p></div>
        `,
    });
    const editor = getEditor();
    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    expect(":iframe [data-oe-model='test']").toHaveClass("o_editable");
    setSelection({ anchorNode: queryOne(":iframe #sectionId"), anchorOffset: 0 });
    await insertText(editor, "New");
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect.verifySteps([
        `<div data-oe-model="test" data-oe-field="field" data-oe-id="1" class=""><p id="sectionId">NewTitle</p></div>`,
    ]);
});

test("Translate link of a mega menu", async () => {
    const { getEditor } = await setupSidebarBuilderForTranslation({
        websiteContent: `
            <div data-oe-model="test">
                <section>
                    <div class="container s_allow_columns">
                        <a href="#" class="nav-link d-inline">
                            <span data-oe-model="ir.ui.view" data-oe-id="526" data-oe-field="arch_db" data-oe-translation-state="to_translate" data-oe-translation-source-sha="123" class="o_editable translate_branding">
                                Hello
                            </span>
                        </a>
                    </div>
                </section>
            </div>
        `,
    });
    const editor = getEditor();
    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    const textNode = editor.editable.querySelector("[data-oe-id='526']").childNodes[0];
    setSelection({
        anchorNode: textNode,
        anchorOffset: 0,
        focusOffset: 5,
    });
    pasteText(editor, "x");
    expect(":iframe a [data-oe-model].o_dirty").toHaveCount(1);
});

test("cascade of [data-oe-model] in translation", async () => {
    await setupSidebarBuilderForTranslation({
        websiteContent: `
            <div data-oe-model="test"><section>${getTranslateEditable({
                inWrap: "Hello",
            })}</section></div>
        `,
    });
    expect(":iframe [data-oe-model='test']").not.toHaveClass("o_editable");
    expect(":iframe .container").not.toHaveAttribute("contenteditable");
    expect(":iframe .container span.o_editable").toHaveAttribute("contenteditable", "true");
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
    onRpc("/website/field/translation/update", async (data) => {
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
            <img src="/web/image/website.s_text_image_default_image" class="img img-fluid" loading="lazy" title="<span data-oe-model=&quot;ir.ui.view&quot; data-oe-id=&quot;544&quot; data-oe-field=&quot;arch_db&quot; data-oe-translation-state=&quot;to_translate&quot; data-oe-translation-source-sha=&quot;sourceSha&quot;>title</span>" style=""></img>
        `,
    });
    const editable = getEditableContent();
    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    await contains(":iframe img").click();
    await contains(".modal .modal-body input").edit("titre");
    await contains(".modal .btn:contains(Ok)").click();
    const getImg = ({ titleName, translated }) =>
        `<img src="/web/image/website.s_text_image_default_image" class="img img-fluid o_editable_attribute o_translatable_attribute${
            translated ? " oe_translated" : ""
        }" loading="lazy" title="${titleName}" style="" data-oe-translation-state="to_translate"></img>`;
    expect(editable).toHaveInnerHTML(getImg({ titleName: "titre", translated: true }));
    await contains(".o-snippets-menu button.fa-undo").click();
    expect(editable).toHaveInnerHTML(getImg({ titleName: "title", translated: false }));
    await contains(":iframe img").click();
    expect(".modal .modal-body input").toHaveValue("title");
});

test("undo shortcut in translate", async () => {
    const { getEditor } = await setupSidebarBuilderForTranslation({
        websiteContent: `<h1>Homepage</h1>`,
    });
    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    setSelection({ anchorNode: queryOne(":iframe h1"), anchorOffset: 0 });
    await insertText(getEditor(), "New ");
    expect(":iframe h1").toHaveText("New Homepage");
    await press(["ctrl", "z"]);
    await getEditor().shared.operation.next();
    expect(":iframe h1").not.toHaveText("New Homepage");
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

describe("paste in translate", () => {
    test("paste html in a translated span should not add blocks", async () => {
        const { getEditor } = await setupSidebarBuilderForTranslation({
            websiteContent: getTranslateEditable({ inWrap: "a<b>c</b>a" }),
        });
        setSelection({ anchorNode: queryOne(":iframe b") });
        pasteHtml(getEditor(), `<h1><u>hello</u></h1>`);
        expect(":iframe b u").toHaveText("hello");
        expect(":iframe h1").toHaveCount(0);
    });

    test("paste html in translate mode should not add img", async () => {
        const { getEditor } = await setupSidebarBuilderForTranslation({
            websiteContent: getTranslateEditable({ inWrap: "a<b>c</b>a" }),
        });
        setSelection({ anchorNode: queryOne(":iframe b") });
        pasteHtml(getEditor(), `<img src="${dummyBase64Img}"/>`);
        expect(":iframe img").toHaveCount(0);
    });

    test("paste html in translate mode should add o_translate_inline on `a` element", async () => {
        const { getEditor } = await setupSidebarBuilderForTranslation({
            websiteContent: getTranslateEditable({ inWrap: "a<b>c</b>a" }),
        });
        setSelection({ anchorNode: queryOne(":iframe b") });
        pasteHtml(getEditor(), `<a href="/">link</a>`);
        expect(":iframe b a").toHaveClass("o_translate_inline");
    });
});

test("test that powerbox should not open in translate mode", async () => {
    const { getEditor } = await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable("&nbsp;"),
    });
    const editor = getEditor();
    const textNode = editor.editable.querySelector("span").firstChild;
    expect(textNode.nodeType).toBe(Node.TEXT_NODE);
    setSelection({ anchorNode: textNode, anchorOffset: 0 });
    // Simulate typing `/`
    await insertText(editor, "/");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 0);
});

test("copy of a translated span should not copy branding attributes", async () => {
    const { getEditor } = await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable({ inWrap: "a<b>c</b>a" }),
    });
    await contains(":iframe [contenteditable=true]").focus();
    const editor = getEditor();
    const textNode = editor.editable.querySelector("b").firstChild;
    expect(textNode.nodeType).toBe(Node.TEXT_NODE);
    setSelection({ anchorNode: textNode, anchorOffset: 0, focusNode: textNode, focusOffset: 1 });
    const clipboardData = new DataTransfer();
    await press(["ctrl", "c"], { dataTransfer: clipboardData });
    expect(clipboardData.getData("text/plain")).toBe("c");
    expect(clipboardData.getData("text/html")).toBe(`<b>c</b>`);
});

describe("save translation", () => {
    beforeEach(async () => {
        onRpc("/website/field/translation/update", async (data) => {
            const { params } = await data.json();
            expect.step({ [params.record_id[0]]: params.translations.fr_BE });
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
        expect.verifySteps([{ 526: { srcSha1: "a1bc", srcSha2: "d1ef" } }]);
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
        expect.verifySteps([{ 1: { srcSha1: "a1bc" } }, { 2: { srcSha2: "d1ef" } }]);
    });

    test("save delayed translation even if not dirty", async () => {
        const websiteContent = `
            ${getTranslateEditable({ inWrap: "abc", oeId: 1, sourceSha: srcSha1 })}
            ${getTranslateEditable({ inWrap: "def", oeId: 2, sourceSha: srcSha2 })}
            ${getTranslateEditable({ inWrap: "ghi", oeId: 2, sourceSha: "srcSha3" })}
            ${getTranslateEditable({ inWrap: "jkl", oeId: 3, sourceSha: "srcSha4" })}
            ${getTranslateEditable({ inWrap: "mno", oeId: 4, sourceSha: "srcSha5" })}
        `.replace(/ translate_branding">(?!jkl<)/g, ' o_delay_translation translate_branding">');
        const { getEditor } = await setupSidebarBuilderForTranslation({
            websiteContent: websiteContent,
        });
        await modifyBothTextsAndSave(getEditor());
        expect.verifySteps([{ 4: {} }, { 1: { srcSha1: "a1bc" } }, { 2: { srcSha2: "d1ef" } }]);
    });
});

test("table of content snippet headings' translation updates its navbar items", async () => {
    const snippet = "s_table_of_content";
    const websiteContent = (await getStructureSnippet(snippet)).outerHTML;
    const { getEditor } = await setupSidebarBuilderForTranslation({ websiteContent });
    const editor = getEditor();
    const oldTitle = editor.editable.querySelector("#table_of_content_heading_1_1").textContent;
    expect(":iframe .s_table_of_content_navbar .table_of_content_link:first-child").toHaveText(
        oldTitle
    );
    const titleEl = editor.editable.querySelector("#table_of_content_heading_1_1");
    setSelection({ anchorNode: titleEl });
    await insertText(editor, "New title");
    expect(":iframe .s_table_of_content_navbar .table_of_content_link:first-child").toHaveText(
        `New title${oldTitle}`
    );
});

test("'Translate to' button should be visible in translate mode", async () => {
    await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable({ inWrap: "Hello" }),
    });
    onRpc("/html_editor/generate_text", () =>
        JSON.stringify([
            {
                id: "t_" + parseInt(uniqueId() - 1),
                text: "Bonjour",
            },
        ])
    );
    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    expectElementCount("button[data-action-id='translateWebpageAI']", 1);
    await contains("button[data-action-id='translateWebpageAI']").click();
    await animationFrame();
    expect(":iframe .o_editable").toHaveText("Bonjour");
});

test("trying to translate an element inside a .o_not_editable should add a notification", async () => {
    mockService("notification", {
        add(message, options = {}) {
            expect(message).toBe("This translation is not editable.");
        },
    });
    await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable({
            inWrap: "Hello",
            oeId: 10,
            containerEditable: false,
        }),
    });
    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    await contains(":iframe [data-oe-id='10']").click();
});

test("trying to translate an attribute of an image inside a .o_not_editable should add a notification", async () => {
    expect.assertions(2);
    mockService("notification", {
        add(message, options = {}) {
            expect(message).toBe("This translation is not editable.");
        },
    });
    await setupSidebarBuilderForTranslation({
        websiteContent: `
            <div class="o_not_editable">
                <img src="/web/image/website.s_text_image_default_image" class="img img-fluid mx-auto rounded o_editable" loading="lazy" title="<span data-oe-model=&quot;ir.ui.view&quot; data-oe-id=&quot;544&quot; data-oe-field=&quot;arch_db&quot; data-oe-translation-state=&quot;to_translate&quot; data-oe-translation-source-sha=&quot;sourceSha&quot;>title</span>" style=""></img>
            <div/>
        `,
    });
    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    await contains(":iframe img").click();
    expect(".modal .modal-body input").toHaveCount(0);
});

test("it should be possible to translate the attribute of an image that has the o_editable_media even if it is inside a o_not_editable area", async () => {
    await setupSidebarBuilderForTranslation({
        websiteContent: `
            <div class="o_not_editable">
                <img src="/web/image/website.s_text_image_default_image" class="img img-fluid mx-auto rounded o_editable_media" loading="lazy" title="<span data-oe-model=&quot;ir.ui.view&quot; data-oe-id=&quot;544&quot; data-oe-field=&quot;arch_db&quot; data-oe-translation-state=&quot;to_translate&quot; data-oe-translation-source-sha=&quot;sourceSha&quot;>title</span>" style=""></img>
            <div/>
        `,
    });
    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    await contains(":iframe img").click();
    expect(".modal .modal-body input").toHaveCount(1);
});

test("Ensure the contenteditable attributes have been set before the TranslationPlugin checks for the node to be translated", async () => {
    patchWithCleanup(TranslationPlugin.prototype, {
        prepareTranslation() {
            expect(":iframe .translate_branding").toHaveAttribute("contenteditable", "true");
            super.prepareTranslation();
        },
    });
    await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable({ inWrap: "Hello" }),
    });
});

test("sidebar should open even when translated elements fetch is slow", async () => {
    const originalFetch = globals.fetch;

    patchWithCleanup(globals, {
        async fetch(url, options) {
            if (url === "/website/get_translated_elements") {
                await delay(100);
            }
            return originalFetch.call(this, url, options);
        },
    });
    await setupSidebarBuilderForTranslation({
        websiteContent: getTranslateEditable({ inWrap: "Hello" }),
    });
    expect(".o_builder_sidebar_open").toHaveCount(1);
});

function getTranslateEditable({
    inWrap,
    oeId = "526",
    sourceSha = "sourceSha",
    containerEditable = true,
}) {
    return `
        <div class="container s_allow_columns${containerEditable ? "" : " o_not_editable"}">
            <p>
                <span data-oe-model="ir.ui.view" data-oe-id="${oeId}" data-oe-field="arch_db" data-oe-translation-state="to_translate" data-oe-translation-source-sha="${sourceSha}" class="o_editable translate_branding">${inWrap}</span>
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
    await getTranslatedElements();
    await openBuilderSidebar();
    return { getEditor, getEditableContent };
}
