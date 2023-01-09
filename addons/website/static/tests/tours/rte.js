odoo.define('website.tour.rte', function (require) {
'use strict';

var session = require('web.session');
const wTourUtils = require('website.tour_utils');

var domReady = new Promise(function (resolve) {
    $(resolve);
});
var ready = Promise.all([domReady, session.is_bound]);

wTourUtils.registerWebsitePreviewTour('rte_translator', {
    test: true,
    url: '/',
    wait_for: ready,
}, [{
    content: "click language dropdown",
    trigger: 'iframe .js_language_selector .dropdown-toggle',
}, {
    content: "click on Add a language",
    trigger: 'iframe a.o_add_language',
}, {
    content: "type Parseltongue",
    trigger: 'div[name="lang_ids"] .o_input_dropdown input',
    run: 'text Parseltongue',
}, {
    content: 'select Parseltongue',
    trigger: '.dropdown-item:contains(Parseltongue)',
}, {
    content: "load Parseltongue",
    trigger: '.modal-footer .btn-primary',
    extra_trigger: '.modal-dialog div[name="lang_ids"] .rounded-pill .o_tag_badge_text:contains(Parseltongue)',
}, {
    content: "click language dropdown (2)",
    trigger: 'iframe .js_language_selector .dropdown-toggle',
    timeout: 60000,
}, {
    content: "go to english version",
    trigger: 'iframe .js_language_selector a[data-url_code="en"]',
    extra_trigger: 'iframe html[lang*="pa-GB"]',
}, {
    content: "Open new page menu",
    trigger: ".o_menu_systray .o_new_content_container > a",
    extra_trigger: 'iframe html[lang*="en-US"]',
    consumeVisibleOnly: true,
}, {
    content: "click on new page",
    trigger: '.o_new_content_element a',
}, {
    content: "insert file name",
    trigger: '.modal-dialog input[type="text"]',
    run: 'text rte_translator.xml',
}, {
    content: "create file",
    trigger: '.modal-dialog button.btn-primary',
    extra_trigger: 'input[type="text"]:propValue(rte_translator.xml)',
}, {
    content: "click on the 'page manager' button",
    trigger: 'button[name="website.action_website_pages_list"]',
}, {
    content: "click on the record to display the xml file in the iframe",
    trigger: 'td:contains("rte_translator.xml")',
}, {
    content: "Open new page menu",
    trigger: ".o_menu_systray .o_new_content_container > a",
    consumeVisibleOnly: true,
}, {
    content: "click on new page",
    trigger: '.o_new_content_element a',
}, {
    content: "insert page name",
    trigger: '.modal-dialog input[type="text"]',
    run: 'text rte_translator',
}, {
    content: "create page",
    trigger: '.modal-dialog button.btn-primary',
    extra_trigger: 'input[type="text"]:propValue(rte_translator)',
}, {
    content: "drop a snippet",
    trigger: "#snippet_structure .oe_snippet:eq(1) .oe_snippet_thumbnail",
    run: 'drag_and_drop iframe #wrap',
}, {
    content: "change content",
    trigger: 'iframe #wrap',
    run: function () {
        $('iframe:not(.o_ignore_in_tour)').contents().find("#wrap p:first").replaceWith('<p>Write one or <font style="background-color: yellow;">two paragraphs <b>describing</b></font> your product or\
                <font style="color: rgb(255, 0, 0);">services</font>. To be successful your content needs to be\
                useful to your <a href="/999">readers</a>.</p> <input placeholder="test translate placeholder"/>\
                <p>&lt;b&gt;&lt;/b&gt; is an HTML&nbsp;tag &amp; is empty</p>');
        $('iframe:not(.o_ignore_in_tour)').contents().find("#wrap img").attr("title", "test translate image title");
    }
}, {
    content: "save",
    trigger: 'button[data-action=save]',
    extra_trigger: 'iframe #wrap p:first b',
}, {
    content: "click language dropdown (3)",
    trigger: 'iframe .js_language_selector .dropdown-toggle',
    extra_trigger: 'iframe body:not(.editor_enable)',
}, {
    content: "click on Parseltongue version",
    trigger: 'iframe .js_language_selector a[data-url_code="pa_GB"]',
    extra_trigger: 'iframe html[lang*="en"]',
}, {
    content: "translate",
    trigger: '.o_menu_systray .o_translate_website_container > a',
    extra_trigger: 'iframe html:not(:has(#wrap p span))',
}, {
    content: "close modal",
    trigger: '.modal-footer .btn-secondary',
}, {
    content: "check if translation is activate",
    trigger: 'iframe [data-oe-translation-initial-sha]',
}, {
    content: "translate text",
    extra_trigger: '#oe_snippets.o_loaded',
    trigger: 'iframe #wrap p font:first',
    run: function (actionHelper) {
        actionHelper.text('translated Parseltongue text');
        const Wysiwyg = odoo.__DEBUG__.services['web_editor.wysiwyg'];
        Wysiwyg.setRange(this.$anchor.contents()[0], 22);
        this.$anchor.trigger($.Event("keyup", {key: '_', keyCode: 95}));
        this.$anchor.trigger('input');
    },
}, {
    content: "translate text with special char",
    trigger: 'iframe #wrap input + p span:first',
    run: function (actionHelper) {
        actionHelper.click();
        this.$anchor.prepend('&lt;{translated}&gt;');
        const Wysiwyg = odoo.__DEBUG__.services['web_editor.wysiwyg'];
        Wysiwyg.setRange(this.$anchor.contents()[0], 0);
        this.$anchor.trigger($.Event("keyup", {key: '_', keyCode: 95}));
        this.$anchor.trigger('input');
    },
}, {
    content: "click on input",
    trigger: 'iframe #wrap input:first',
    extra_trigger: 'iframe #wrap .o_dirty font:first:contains(translated Parseltongue text)',
    run: 'click',
}, {
    content: "translate placeholder",
    trigger: '.modal-dialog input:first',
    run: 'text test Parseltongue placeholder',
}, {
    content: "close modal",
    trigger: '.modal-footer .btn-primary',
    extra_trigger: '.modal input:propValue(test Parseltongue placeholder)',
}, {
    content: "save translation",
    trigger: 'button[data-action=save]',
}, {
    content: "check: content is translated",
    trigger: 'iframe #wrap p font:first:contains(translated Parseltongue text)',
    extra_trigger: 'iframe body:not(.editor_enable)',
    run: function () {}, // it's a check
}, {
    content: "check: content with special char is translated",
    trigger: "iframe #wrap input + p:contains(<{translated}><b></b> is an HTML\xa0tag & )",
    run: function () {}, // it's a check

}, {
    content: "check: placeholder translation",
    trigger: 'iframe input[placeholder="test Parseltongue placeholder"]',
    run: function () {}, // it's a check

}, {
    content: "open language selector",
    trigger: 'iframe .js_language_selector button:first',
    extra_trigger: 'iframe html[lang*="pa-GB"]:not(:has(#wrap p span))',
}, {
    content: "return to english version",
    trigger: 'iframe .js_language_selector a[data-url_code="en"]',
}, {
    content: "edit english version",
    trigger: '.o_edit_website_container > a',
    extra_trigger: 'iframe body:not(:has(#wrap p font:first:containsExact(paragraphs <b>describing</b>)))',
}, {
    content: "select text",
    extra_trigger: '#oe_snippets.o_loaded',
    trigger: 'iframe #wrap p',
    run: function (actionHelper) {
        actionHelper.click();
        var el = this.$anchor[0];
        var mousedown = document.createEvent('MouseEvents');
        mousedown.initMouseEvent('mousedown', true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
        el.dispatchEvent(mousedown);
        var mouseup = document.createEvent('MouseEvents');
        const Wysiwyg = odoo.__DEBUG__.services['web_editor.wysiwyg'];
        Wysiwyg.setRange(el.childNodes[2], 6, el.childNodes[2], 13);
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
}, {
    content: "save new change",
    trigger: 'button[data-action=save]',
    // See comment above.
    // extra_trigger: '#wrap.o_dirty p span[style*="text-decoration-line: underline;"]',
}, {
    content: "click language dropdown (4)",
    trigger: 'iframe .js_language_selector .dropdown-toggle',
    extra_trigger: 'iframe body:not(.editor_enable)',
}, {
    content: "return in Parseltongue",
    trigger: 'iframe html[lang="en-US"] .js_language_selector .js_change_lang[data-url_code="pa_GB"]',
}, {
    content: "check bis: content is translated",
    trigger: 'iframe #wrap p font:first:contains(translated Parseltongue text)',
    extra_trigger: 'iframe html[lang*="pa-GB"]',
}, {
    content: "check bis: placeholder translation",
    trigger: 'iframe input[placeholder="test Parseltongue placeholder"]',
}, {
    content: "open site menu",
    trigger: 'button[data-menu-xmlid="website.menu_site"]',
}, {
    content: "Open HTML editor",
    trigger: 'a[data-menu-xmlid="website.menu_ace_editor"]',
}, {
    content: "Check that the editor is not showing translated content (1)",
    trigger: '.ace_text-layer .ace_line:contains("an HTML")',
    run: function (actions) {
        var lineEscapedText = $(this.$anchor.text()).text();
        if (lineEscapedText !== "&lt;b&gt;&lt;/b&gt; is an HTML&nbsp;tag &amp; is empty") {
            console.error('The HTML editor should display the correct untranslated content');
            $('iframe:not(.o_ignore_in_tour)').contents().find('body').addClass('rte_translator_error');
        }
    },
}, {
    content: "Check that the editor is not showing translated content (2)",
    trigger: 'iframe body:not(.rte_translator_error)',
    run: function () {},
}]);
});
