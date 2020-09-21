odoo.define('website.tour.rte', function (require) {
'use strict';

var ajax = require('web.ajax');
var session = require('web.session');
var tour = require('web_tour.tour');
var Wysiwyg = require('web_editor.wysiwyg');

var domReady = new Promise(function (resolve) {
    $(resolve);
});
var ready = Promise.all([domReady, session.is_bound, ajax.loadXML()]);

tour.register('rte_translator', {
    test: true,
    url: '/fr_BE',
    wait_for: ready,
}, [{
    content : "click language dropdown",
    trigger : '.js_language_selector .dropdown-toggle',
}, {
    content: "go to english version",
    trigger: '.js_language_selector a[data-url_code="en"]',
    extra_trigger: 'html[lang*="fr"]',
}, {
    content: "Open new page menu",
    trigger: '#new-content-menu > a',
    extra_trigger: 'a[data-action="edit"]',
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
    run: async (action_helper) => {
        action_helper.drag_and_drop('#wrap');
        // wait the last operation of the editor before saving.
        $('#wrap').addClass('action-loading');
        await new Promise(r => setTimeout(r, 0));
        await new Promise(r => setTimeout(r, 0));
        $('#wrap').removeClass('action-loading');
    },
}, {
    content: "change content",
    trigger: '#wrap:not(.action-loading)',
    run: async function () {
        const wysiwyg = $('#wrapwrap').data('wysiwyg');
        await wysiwyg.editor.execCommand(async (params)=> {
            await wysiwyg.editorHelpers.replace(params, document.querySelector('#wrap p'),
                    '<p>Write one or <font style="background-color: yellow;">two paragraphs <b>describing</b></font> your product or\
                    <font style="color: rgb(255, 0, 0);">services</font>. To be successful your content needs to be\
                    useful to your <a href="/999">readers</a>.</p> <input placeholder="test translate placeholder"/>\
                    <p>&lt;b&gt;&lt;/b&gt; is an HTML&nbsp;tag &amp; is empty</p>');
            await wysiwyg.editorHelpers.setAttribute(params, document.querySelectorAll("#wrap img"), "title", "test translate image title");
        });
    }
}, {
    content: "save",
    trigger: 'button[data-action=save]',
    extra_trigger: '#wrap p:first b',
}, {
    content : "click language dropdown",
    trigger : '.js_language_selector .dropdown-toggle',
    extra_trigger: 'body:not(.o_wait_reload):not(:has(.note-editor)) a[data-action="edit"]',
}, {
    content: "click on french version",
    trigger: '.js_language_selector a[data-url_code="fr_BE"]',
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
    trigger: '#wrap p font:first',
    run: async function (action_helper) {
        const wysiwyg = $('#wrapwrap').data('wysiwyg');
        await wysiwyg.editorHelpers.text(wysiwyg.editor, document.querySelector('#wrap p font'), 'translated french text');
        this.$anchor.trigger($.Event( "keyup", {key: '_', keyCode: 95}));
        this.$anchor.trigger('input');
    },
}, {
    content: "translate text with special char",
    trigger: '#wrap input + p span:first',
    run: async function (action_helper) {
        action_helper.click();
        const element = document.querySelector('#wrap input + p span');
        const wysiwyg = $('#wrapwrap').data('wysiwyg');
        await wysiwyg.editorHelpers.text(wysiwyg.editor, element, '<{translated}>' + element.innerText);
        this.$anchor.trigger($.Event( "keyup", {key: '_', keyCode: 95}));
        this.$anchor.trigger('input');
    },
}, {
    content: "click on input",
    trigger: '#wrap input:first',
    extra_trigger: '#wrap font:contains(translated french text)',
    run: function (action_helper) {
        $('#wrap input:first').mousedown();
    },
}, {
    content: "translate placeholder",
    trigger: 'input:first',
    run: 'text test french placeholder',
}, {
    content: "close modal",
    trigger: '.modal-footer .btn-primary',
    extra_trigger: '.modal input:propValue(test french placeholder)',
}, {
    content: "save translation",
    trigger: 'button[data-action=save]',
}, {
    content: "check: content is translated",
    trigger: '#wrap p font:contains(translated french text)',
    extra_trigger: 'body:not(.o_wait_reload):not(:has(.note-editor)) a[data-action="edit_master"]',
    run: function () {}, // it's a check
}, {
    content: "check: content with special char is translated",
    trigger: "#wrap input + p:contains(<{translated}><b></b> is an HTML\xa0tag & )",
    run: function () {}, // it's a check

}, {
    content: "check: placeholder translation",
    trigger: 'input[placeholder="test french placeholder"]',
    run: function () {}, // it's a check

}, {
    content: "open language selector",
    trigger: '.js_language_selector button:first',
    extra_trigger: 'html[lang*="fr"]:not(:has(#wrap p span))',
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
    run: function (action_helper) {
        action_helper.click();
        var el = this.$anchor[0];
        var mousedown = document.createEvent('MouseEvents');
        mousedown.initMouseEvent('mousedown', true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
        el.dispatchEvent(mousedown);
        var mouseup = document.createEvent('MouseEvents');
        const wysiwyg = $('#wrapwrap').data('wysiwyg');
        Wysiwyg.setRange(wysiwyg, el.childNodes[2], 6, el.childNodes[2], 13);
        mouseup.initMouseEvent('mouseup', true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
        el.dispatchEvent(mouseup);
    },
}, {
    content: "underline",
    trigger: 'jw-toolbar jw-button[name="underline"]',
}, {
    content: "save new change",
    trigger: 'button[data-action=save]',
    extra_trigger: '#wrap p u',

    }, {
    content : "click language dropdown",
    trigger : '.js_language_selector .dropdown-toggle',
    extra_trigger: 'body:not(.o_wait_reload):not(:has(.note-editor)) a[data-action="edit"]',
}, {
    content: "return in french",
    trigger : 'html[lang="en-US"] .js_language_selector .js_change_lang[data-url_code="fr_BE"]',
}, {
    content: "check bis: content is translated",
    trigger: '#wrap p font:first:contains(translated french text)',
    extra_trigger: 'html[lang*="fr"] body:not(:has(button[data-action=save]))',
}, {
    content: "check bis: placeholder translation",
    trigger: 'input[placeholder="test french placeholder"]',
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
