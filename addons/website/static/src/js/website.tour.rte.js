odoo.define('website.tour.rte', function (require) {
'use strict';

var Tour = require('web.Tour');

Tour.register({
    id:   'rte_translator',
    name: "Test translator",
    mode: 'test',
    steps: [
        {
            title:     "click on Add a language",
            element:   '.js_language_selector a:has(i.fa)',
        },
        {
            title:     "select french",
            element:   '.modal select[name="lang"]',
            sampleText: '"fr_BE"',
        },
        {
            title:     "load french",
            waitFor:   '.modal select[name="lang"]:propValueContains(fr_BE)',
            element:   '.modal .modal-footer button:first',
        },
        {
            title:     "go to english version",
            waitFor:   'html[lang*="fr"]',
            element:   '.js_language_selector a[data-lang="en_US"]',
            onload: function () {
                localStorage.removeItem('website_translator_nodialog');
            }
        },
        {
            title:     "Open content menu",
            element:   '#content-menu-button',
        },
        {
            title:     "click on new page",
            element:   '[data-action="new_page"]',
        },
        {
            title:     "insert page name",
            element:   '#editor_new_page input[type="text"]',
            sampleText: 'rte_translator',
        },
        {
            title:     "create page",
            waitFor:   'input[type="text"]:propValue(rte_translator)',
            element:   '.modal:has(#editor_new_page) button.btn-continue',
        },
        {
            title:     "drop a snippet",
            snippet:   '#snippet_structure .oe_snippet:eq(1)',
        },
        {
            title:     "change content",
            waitFor:   '.oe_overlay_options .oe_options:visible',
            onload: function () {
                $("#wrap p:first").replaceWith('<p>Write one or <font style="background-color: yellow;">two paragraphs <b>describing</b></font> your product or\
                        <font style="color: rgb(255, 0, 0);">services</font>. To be successful your content needs to be\
                        useful to your <a href="/999">readers</a>.</p> <input placeholder="test translate placeholder"/>\
                        <p>&lt;b&gt;&lt;/b&gt; is an HTML&nbsp;tag &amp; is empty</p>');
                $("#wrap img").attr("title", "test translate image title");
            }
        },
        {
            title:     "save",
            waitFor:   '#wrap p:first b',
            element:   'button[data-action=save]',
        },
        {
            title:     "click on french version",
            waitFor:   'html[lang*="en"]',
            waitNot:   'button[data-action=save]',
            element:   '.js_language_selector a[data-lang="fr_BE"]',
        },
        {
            title:     "translate",
            waitNot:   '#wrap p span',
            element:   '#oe_editzone button[data-action="translate"]',
        },
        {
            title:     "check if translation is activate",
            waitFor:   '[data-oe-translation-id]',
        },
        {
            title:     "close modal",
            element:   '.modal button[data-action="activate"]',
        },
        {
            title:     "translate text",
            element:   '#wrap p font:first',
            sampleText: 'translated french text',
            onload: function () {
                $(this.element).closest('[data-oe-translation-id]').addClass('o_dirty').trigger('keyup');
            },
        },
        {
            title:     "click on input",
            waitFor:   '#wrap .o_dirty font:first:contains(translated french text)',
            element:   'input:first',
        },
        {
            title:     "translate text with special char",
            onload: function () {
                $('#wrap input + p').find(':last').prepend('&lt;{translated}&gt;')
                  .closest('[data-oe-translation-id]').addClass('o_dirty').trigger('keyup');
            },
        },
        {
            title:     "translate placeholder",
            element:   '.modal.web_editor-dialog input:first',
            sampleText: 'test french placeholder',
        },
        {
            title:     "close modal",
            waitFor:   '.web_editor-dialog input:propValue(test french placeholder)',
            element:   '.web_editor-dialog button',
        },
        {
            title:     "close modal",
            waitNot:   '.web_editor-dialog',
            element:   'button[data-action=save]',
        },
        {
            title:     "check: content is translated",
            waitNot:   'button[data-action=save]',
            waitFor:   '#wrap p font:first:contains(translated french text)',
        },
        {
            title:     "check: content with special char is translated",
            waitFor:   "#wrap input + p:contains(<{translated}><b></b> is an HTML\xa0tag & )",
        },
        {
            title:     "check: placeholder translation",
            waitFor:   'input[placeholder="test french placeholder"]',
        },
        {
            title:     "return to english version",
            waitFor:   'html[lang*="fr"]',
            waitNot:   '#wrap p span',
            element:   '.js_language_selector a[data-lang="en_US"]',
        },
        {
            title:     "edit english version",
            waitNot:   '#wrap p font:first:containsExact(paragraphs <b>describing</b>)',
            element:   'button[data-action=edit]',
        },
        {
            title:     "select text",
            waitFor:   'button[data-action=save]',
            element:   '#wrap p',
            onload: function () {
                var el = $(this.element)[0];
                var evt = document.createEvent("MouseEvents");
                $.summernote.core.range.create(el.childNodes[2], 6, el.childNodes[2], 13).select();
                evt.initMouseEvent('mouseup', true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
                el.dispatchEvent(evt);
            },
        },
        {
            title:     "underline",
            element:   '.note-air-popover button[data-event="underline"]',
        },
        {
            title:     "save new change",
            waitFor:   '#wrap p u',
            element:   'button[data-action=save]',
        },
        {
            title:     "return in french",
            waitFor:   'html[lang*="en"]',
            waitNot:   'button[data-action=save]',
            element:   'html[lang="en-US"] .js_language_selector a[data-lang="fr_BE"]',
        },
        {
            title:     "check bis: content is translated",
            waitNot:   'button[data-action=save]',
            waitFor:   '#wrap p font:first:contains(translated french text)',
        },
        {
            title:     "check bis: placeholder translation",
            waitFor:   'input[placeholder="test french placeholder"]',
        },
    ]
});

});
