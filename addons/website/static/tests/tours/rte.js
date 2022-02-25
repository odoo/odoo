odoo.define('website.tour.rte', function (require) {
'use strict';

var ajax = require('web.ajax');
var session = require('web.session');
var tour = require('web_tour.tour');

var domReady = new Promise(function (resolve) {
    $(resolve);
});
var ready = Promise.all([domReady, session.is_bound, ajax.loadXML()]);

tour.register('rte_translator', {
    test: true,
    url: '/',
    wait_for: ready,
}, [{
    content: "click language dropdown",
    trigger: '.js_language_selector .dropdown-toggle',
}, {
    content: "click on Add a language",
    trigger: 'a.o_add_language',
}, {
    content: "select Parseltongue",
    trigger: 'select[name="lang"]',
    run: 'text "pa_GB"',
}, {
    content: "load Parseltongue",
    trigger: '.modal-footer button:first',
    extra_trigger: '.modal select[name="lang"]:propValueContains(pa_GB)',
}, {
    content: "click language dropdown (2)",
    trigger: '.js_language_selector .dropdown-toggle',
    timeout: 60000,
}, {
    content: "go to english version",
    trigger: '.js_language_selector a[data-url_code="en"]',
    extra_trigger: 'html[lang*="pa-GB"]',
}, {
    content: "Open new page menu",
    trigger: "body:has(#o_new_content_menu_choices.o_hidden) #new-content-menu > a",
    extra_trigger: 'a[data-action="edit"]',
    consumeVisibleOnly: true,
}, {
    content: "click on new page",
    trigger: 'a[data-action="new_page"]',
}, {
    content: "insert page name",
    trigger: '#editor_new_page input[type="text"]',
    run: 'text rte_translator',
}, {
    content: "create page",
    trigger: 'button.btn-continue',
    extra_trigger: 'input[type="text"]:propValue(rte_translator)',
}, {
    content: "drop a snippet",
    trigger: "#snippet_structure .oe_snippet:eq(1) .oe_snippet_thumbnail",
    run: 'drag_and_drop #wrap',
}, {
    content: "change content",
    trigger: '#wrap',
    run: function () {
        $("#wrap p:first").replaceWith('<p>Write one or <font style="background-color: yellow;">two paragraphs <b>describing</b></font> your product or\
                <font style="color: rgb(255, 0, 0);">services</font>. To be successful your content needs to be\
                useful to your <a href="/999">readers</a>.</p> <input placeholder="test translate placeholder"/>\
                <p>&lt;b&gt;&lt;/b&gt; is an HTML&nbsp;tag &amp; is empty</p>');
        $("#wrap img").attr("title", "test translate image title");
    }
}, {
    content: "save",
    trigger: 'button[data-action=save]',
    extra_trigger: '#wrap p:first b',
}, {
    content: "click language dropdown (3)",
    trigger: '.js_language_selector .dropdown-toggle',
    extra_trigger: 'body:not(.o_wait_reload):not(:has(.note-editor)) a[data-action="edit"]',
}, {
    content: "click on Parseltongue version",
    trigger: '.js_language_selector a[data-url_code="pa_GB"]',
    extra_trigger: 'html[lang*="en"]:not(:has(button[data-action=save]))',
}, {
    content: "translate",
    trigger: 'html:not(:has(#wrap p span)) .o_menu_systray a[data-action="translate"]',
}, {
    content: "close modal",
    trigger: '.modal-footer .btn-secondary',
}, {
    content: "check if translation is activate",
    trigger: '[data-oe-translation-id]',
}, {
    content: "translate text",
    extra_trigger: '.editor_started',
    trigger: '#wrap p font:first',
    run: function (actionHelper) {
        actionHelper.text('translated Parseltongue text');
        const Wysiwyg = odoo.__DEBUG__.services['web_editor.wysiwyg'];
        Wysiwyg.setRange(this.$anchor.contents()[0], 22);
        this.$anchor.trigger($.Event("keyup", {key: '_', keyCode: 95}));
        this.$anchor.trigger('input');
    },
}, {
    content: "translate text with special char",
    trigger: '#wrap input + p span:first',
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
    trigger: '#wrap input:first',
    extra_trigger: '#wrap .o_dirty font:first:contains(translated Parseltongue text)',
    run: 'click',
}, {
    content: "translate placeholder",
    trigger: 'input:first',
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
    trigger: '#wrap p font:first:contains(translated Parseltongue text)',
    extra_trigger: 'body:not(.o_wait_reload):not(:has(.note-editor)) a[data-action="edit_master"]',
    run: function () {}, // it's a check
}, {
    content: "check: content with special char is translated",
    trigger: "#wrap input + p:contains(<{translated}><b></b> is an HTML\xa0tag & )",
    run: function () {}, // it's a check

}, {
    content: "check: placeholder translation",
    trigger: 'input[placeholder="test Parseltongue placeholder"]',
    run: function () {}, // it's a check

}, {
    content: "open language selector",
    trigger: '.js_language_selector button:first',
    extra_trigger: 'html[lang*="pa-GB"]:not(:has(#wrap p span))',
}, {
    content: "return to english version",
    trigger: '.js_language_selector a[data-url_code="en"]',
}, {
    content: "edit english version",
    trigger: 'a[data-action=edit]',
    extra_trigger: 'body:not(:has(#wrap p font:first:containsExact(paragraphs <b>describing</b>)))',
}, {
    content: "select text",
    extra_trigger: '#oe_snippets.o_loaded',
    trigger: '#wrap p',
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
    trigger: '.js_language_selector .dropdown-toggle',
    extra_trigger: 'body:not(.o_wait_reload):not(:has(.note-editor)) a[data-action="edit"]',
}, {
    content: "return in Parseltongue",
    trigger: 'html[lang="en-US"] .js_language_selector .js_change_lang[data-url_code="pa_GB"]',
}, {
    content: "check bis: content is translated",
    trigger: '#wrap p font:first:contains(translated Parseltongue text)',
    extra_trigger: 'html[lang*="pa-GB"] body:not(:has(button[data-action=save]))',
}, {
    content: "check bis: placeholder translation",
    trigger: 'input[placeholder="test Parseltongue placeholder"]',
}, {
    content: "Open customize menu",
    trigger: "#customize-menu > .dropdown-toggle",
}, {
    content: "Open HTML editor",
    trigger: "[data-action='ace']",
}, {
    content: "Check that the editor is not showing translated content (1)",
    trigger: '.ace_text-layer .ace_line:contains("an HTML")',
    run: function (actions) {
        var lineEscapedText = $(this.$anchor.text()).text();
        if (lineEscapedText !== "&lt;b&gt;&lt;/b&gt; is an HTML&nbsp;tag &amp; is empty") {
            console.error('The HTML editor should display the correct untranslated content');
            $('body').addClass('rte_translator_error');
        }
    },
}, {
    content: "Check that the editor is not showing translated content (2)",
    trigger: 'body:not(.rte_translator_error)',
    run: function () {},
}]);
});
