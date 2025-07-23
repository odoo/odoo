import {
    clickOnEditAndWaitEditModeInTranslatedPage,
    clickOnSave,
    insertSnippet,
    goToTheme,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";
import { setSelection } from '@web_editor/js/editor/odoo-editor/src/utils/utils';
import { whenReady } from "@odoo/owl";
import { editorsWeakMap } from "@html_editor/../tests/tours/helpers/editor";

registerWebsitePreviewTour('rte_translator', {
    url: '/',
    edition: true,
    wait_for: whenReady(),
}, () => [
...goToTheme(),
{
    content: "click on Add a language",
    trigger: "button[data-action-id='addLanguage']",
    run: "click",
}, {
    content: "confirm leave editor",
    trigger: ".modal-dialog button.btn-primary",
    run: "click",
}, {
    content: "type Parseltongue",
    trigger: 'div[name="lang_ids"] .o_input_dropdown input',
    run: "edit Parseltongue",
}, {
    content: 'select Parseltongue',
    trigger: '.dropdown-item:contains(Parseltongue)',
    run: "click",
},
{
    trigger: '.modal-dialog div[name="lang_ids"] .rounded-pill .o_tag_badge_text:contains(Parseltongue)',
},
{
    content: "load Parseltongue",
    trigger: '.modal-footer .btn-primary',
    run: "click",
}, {
    content: "click language dropdown (2)",
    trigger: ':iframe .js_language_selector .dropdown-toggle',
    timeout: 60000,
    run: "click",
},
{
    trigger: ':iframe html[lang*="pa-GB"]',
},
{
    content: "go to english version",
    trigger: ':iframe .o_header_language_selector a[data-url_code="en"]',
    run: "click",
},
{
    trigger: ':iframe html[lang*="en-US"]',
},
{
    content: "Open new page menu",
    trigger: ".o_menu_systray .o_new_content_container > button",
    run: "click",
}, {
    content: "click on new page",
    trigger: ".o_new_content_element button",
    run: "click",
}, {
    content: "click on Use this template",
    trigger: ".o_page_template .o_button_area:not(:visible)",
    run: "click",
}, {
    content: "insert file name",
    trigger: ".modal:not(.o_inactive_modal):contains(new page) .modal-body input[type=text]",
    run: "edit rte_translator.xml && press Enter",
},
{
    trigger: '.modal:not(.o_inactive_modal):contains(new page) .modal-body input[type="text"]:value(rte_translator.xml)',
},
{
    content: "create file",
    trigger: ".modal:not(.o_inactive_modal):contains(new page) button.btn-primary:contains(create)",
    run: "click",
}, {
    content: "click on the 'page manager' button",
    trigger: 'button[name="website.action_website_pages_list"]',
    run: "click",
}, {
    content: "click on the record to display the xml file in the iframe",
    trigger: 'td:contains("rte_translator.xml")',
    run: "click",
}, {
    content: "Open new page menu",
    trigger: ".o_menu_systray .o_new_content_container > button",
    run: "click",
}, {
    content: "click on new page",
    trigger: '.o_new_content_element button',
    run: "click",
}, {
    content: "click on Use this template",
    trigger: ".o_page_template .o_button_area:not(:visible)",
    run: "click",
}, {
    content: "insert page name",
    trigger: '.modal .modal-dialog .modal-body input[type="text"]',
    run: "edit rte_translator",
},
{
    trigger: 'input[type="text"]:value(rte_translator)',
},
{
    content: "create page",
    trigger: ".modal button.btn-primary:contains(create)",
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
...insertSnippet({
    id: "s_cover",
    name: "Cover",
    groupName: "Intro",
}), {
    content: "change content",
    trigger: ':iframe #wrap',
    run() {
        this.anchor.querySelector("p").innerHTML = '<p>Write one or <font style="background-color: yellow;">two paragraphs <b>describing</b></font> your product or\
            <font style="color: rgb(255, 0, 0);">services</font>. To be successful your content needs to be\
            useful to your <a href="/999">readers</a>.</p> <input value="test translate default value" placeholder="test translate placeholder"/>\
            <p>&lt;b&gt;&lt;/b&gt; is an HTML&nbsp;tag &amp; is empty</p>';
        this.anchor.querySelector(".oe_img_bg").title ="test translate image title";
        const editor = editorsWeakMap.get(this.anchor.ownerDocument);
        editor.shared.history.addStep();
    }
    }, {
    content: "ensure change was applied",
    trigger: ':iframe #wrap p:first b',
},
...clickOnSave(),
{
    content: "click language dropdown (3)",
    trigger: ':iframe .js_language_selector .dropdown-toggle',
    run: "click",
},
{
    trigger: ':iframe html[lang*="en"]',
},
{
    content: "click on Parseltongue version",
    trigger: ':iframe .js_language_selector a[data-url_code="pa_GB"]',
    run: "click",
}, {
    content: "edit",
    trigger: ".o-website-btn-custo-primary.dropdown-toggle:contains('edit')",
    run: "click",
},
{
    trigger: ":iframe html:not(:has(#wrap p span))",
},
{
    content: "translate",
    trigger: '.o_translate_website_dropdown_item',
    run: "click",
}, {
    content: "close modal",
    trigger: '.modal-footer .btn-secondary',
    run: "click",
}, {
    content: "check if translation is activate",
    trigger: ':iframe [data-oe-translation-source-sha]',
},
{
    trigger: ".o_builder_sidebar_open",
},
{
    content: "translate text",
    trigger: ':iframe #wrap p font:first',
    async run(actionHelper) {
        await actionHelper.editor('translated Parseltongue text');
        setSelection({ anchorNode: this.anchor.childNodes[0], anchorOffset: 22 })
        this.anchor.dispatchEvent(new KeyboardEvent("keyup", {bubbles: true, key: "_"}));
        this.anchor.dispatchEvent(new InputEvent("input", {bubbles: true}));
    },
}, {
    content: "translate text with special char",
    trigger: ':iframe #wrap input + p span:first',
    async run(actionHelper) {
        await actionHelper.click();
        this.anchor.textContent = '<{translated}>' + this.anchor.textContent;
        const editor = editorsWeakMap.get(this.anchor.ownerDocument);
        editor.shared.history.addStep();
        setSelection({ anchorNode: this.anchor.childNodes[0], anchorOffset: 0 })
        this.anchor.dispatchEvent(new KeyboardEvent("keyup", {bubbles: true, key: "_"}));
        this.anchor.dispatchEvent(new InputEvent("input", {bubbles: true}));
    },
},
{
    trigger: ':iframe #wrap .o_dirty font:first:contains(translated Parseltongue text)',
},
{
    content: "click on input",
    trigger: ':iframe #wrap input:first',
    run: 'click',
}, {
    content: "translate placeholder",
    trigger: '.modal-dialog input:first',
    run: "edit test Parseltongue placeholder",
}, {
    content: "translate default value",
    trigger: '.modal-dialog input:last',
    run: "edit test Parseltongue default value",
},
{
    trigger: '.modal input:value("test Parseltongue placeholder")',
},
{
    content: "close modal",
    trigger: '.modal-footer .btn-primary',
    run: "click",
}, {
    content: "check: input marked as translated",
    trigger: ':iframe input[placeholder="test Parseltongue placeholder"].oe_translated',
},
...clickOnSave(),
{
    content: "check: content is translated",
    trigger: ':iframe #wrap p font:first:contains(translated Parseltongue text)',
}, {
    content: "check: content with special char is translated",
    trigger: ":iframe #wrap input + p:contains(<{translated}><b></b> is an HTML tag & )",
}, {
    content: "check: placeholder translation",
    trigger: ':iframe input[placeholder="test Parseltongue placeholder"]',
}, {
    content: "check: default value translation",
    trigger: ':iframe input[value="test Parseltongue default value"]',
},
{
    trigger: ':iframe html[lang*="pa-GB"]:not(:has(#wrap p span))',
},
{
    content: "open language selector",
    trigger: ':iframe .js_language_selector button:first',
    run: "click",
}, {
    content: "return to english version",
    trigger: ':iframe .js_language_selector a[data-url_code="en"]',
    run: "click",
}, {
    content: "Check body",
    trigger: ":iframe body:not(:has(#wrap p font:first:contains(/^paragraphs <b>describing</b>$/)))",
},
...clickOnEditAndWaitEditModeInTranslatedPage(),
{
    content: "select text",
    trigger: ':iframe #wrap p',
    async run(actionHelper) {
        await actionHelper.click();
        var el = this.anchor;
        var mousedown = document.createEvent('MouseEvents');
        mousedown.initMouseEvent('mousedown', true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
        el.dispatchEvent(mousedown);
        var mouseup = document.createEvent('MouseEvents');
        setSelection({ anchorNode: this.anchor.childNodes[0], anchorOffset: 6, focusNode: el.childNodes[2], focusOffset: 13 });
        mouseup.initMouseEvent('mouseup', true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
        el.dispatchEvent(mouseup);
    },
// This is disabled for now because it reveals a bug that is fixed in saas-15.1
// and considered a tradeoff in 15.0. The bug concerns the invalidation of
// translations when inserting tags with more than one character. Whereas <u>
// didn't trigger an invalidation, <span style="text-decoration-line: underline;">
// does.
// }, {
//     content: "underline",
//     trigger: '.oe-toolbar #underline',
},
...clickOnSave(),
{
    content: "click language dropdown (4)",
    trigger: ':iframe .js_language_selector .dropdown-toggle',
    run: "click",
}, {
    content: "return in Parseltongue",
    trigger: ':iframe html[lang="en-US"] .js_language_selector .js_change_lang[data-url_code="pa_GB"]',
    run: "click",
},
{
    trigger: ':iframe html[lang*="pa-GB"]',
},
{
    content: "check bis: content is translated",
    trigger: ':iframe #wrap p font:first:contains(translated Parseltongue text)',
    run: "click",
}, {
    content: "check bis: placeholder translation",
    trigger: ':iframe input[placeholder="test Parseltongue placeholder"]',
    run: "edit Test",
}, {
    content: "open site menu",
    trigger: 'button[data-menu-xmlid="website.menu_site"]',
    run: "click",
}, {
    content: "Open HTML editor",
    trigger: 'a[data-menu-xmlid="website.menu_ace_editor"]',
    run: "click",
}, {
    content: "Check that the editor is not showing translated content (1)",
    trigger: '.ace_text-layer .ace_line:contains("an HTML")',
    run() {
        const parser = new DOMParser();
        const doc = parser.parseFromString(this.anchor.textContent, 'text/html');
        const lineEscapedText = doc.body.querySelector("p:last-child").textContent;
        if (lineEscapedText !== "&lt;b&gt;&lt;/b&gt; is an HTML&nbsp;tag &amp; is empty") {
            console.error('The HTML editor should display the correct untranslated content');
            document.querySelector('iframe:not(.o_ignore_in_tour)').contentDocument.body.classList.add('rte_translator_error');
            const editor = editorsWeakMap.get(this.anchor.ownerDocument);
            editor.shared.history.addStep();
        }
    },
}, {
    content: "Check that the editor is not showing translated content (2)",
    trigger: ':iframe body:not(.rte_translator_error)',
}]);
