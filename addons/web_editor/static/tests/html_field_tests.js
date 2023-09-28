/** @odoo-module **/

import * as ajax from "web.ajax";
import { click, editInput, getFixture, makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { FormController } from '@web/views/form/form_controller';
import { HtmlField } from "@web_editor/js/backend/html_field";
import { parseHTML } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { onRendered } from "@odoo/owl";
import { wysiwygData } from "web_editor.test_utils";
import Wysiwyg from 'web_editor.wysiwyg';
import { useEffect } from "@odoo/owl";
import testUtils from "web.test_utils";
import * as legacyTestUtils from "web.test_utils";
import { MediaDialogWrapper } from "@web_editor/components/media_dialog/media_dialog";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { registry } from "@web/core/registry";

// Legacy
import legacyEnv from 'web.commonEnv';

const serviceRegistry = registry.category("services");

const COLOR_PICKER_TEMPLATE = `
    <colorpicker>
        <div class="o_colorpicker_section" data-name="theme" data-display="Theme Colors" data-icon-class="fa fa-flask">
            <button data-color="o-color-1"/>
            <button data-color="o-color-2"/>
            <button data-color="o-color-3"/>
            <button data-color="o-color-4"/>
            <button data-color="o-color-5"/>
        </div>
        <div class="o_colorpicker_section" data-name="transparent_grayscale" data-display="Transparent Colors" data-icon-class="fa fa-eye-slash">
            <button class="o_btn_transparent"/>
            <button data-color="black-25"/>
            <button data-color="black-50"/>
            <button data-color="black-75"/>
            <bu/** @odoo-module **/
tton data-color="white-25"/>
            <button data-color="white-50"/>
            <button data-color="white-75"/>
        </div>
        <div class="o_colorpicker_section" data-name="common" data-display="Common Colors" data-icon-class="fa fa-paint-brush">
            <button data-color="black"></button>
            <button data-color="900"></button>
            <button data-color="800"></button>
            <button data-color="700" class="d-none"></button>
            <button data-color="600"></button>
            <button data-color="500" class="d-none"></button>
            <button data-color="400"></button>
            <button data-color="300" class="d-none"></button>
            <button data-color="200"></button>
            <button data-color="100"></button>
            <button data-color="white"></button>
        </div>
    </colorpicker>
`;
const SNIPPETS_TEMPLATE = `
    <h2 id="snippets_menu">Add blocks</h2>
    <div id="o_scroll">
        <div id="snippet_structure" class="o_panel">
            <div class="o_panel_header">First Panel</div>
            <div class="o_panel_body">
                <div name="Separator" data-oe-type="snippet" data-oe-thumbnail="/web_editor/static/src/img/snippets_thumbs/s_hr.svg">
                    <div class="s_hr pt32 pb32">
                        <hr class="s_hr_1px s_hr_solid w-100 mx-auto"/>
                    </div>
                </div>
                <div name="Content" data-oe-type="snippet" data-oe-thumbnail="/website/static/src/img/snippets_thumbs/s_text_block.png">
                    <section name="Content+Options" class="test_option_all pt32 pb32" data-oe-type="snippet" data-oe-thumbnail="/website/static/src/img/snippets_thumbs/s_text_block.png">
                        <div class="container">
                            <div class="row">
                                <div class="col-lg-10 offset-lg-1 pt32 pb32">
                                    <h2>Title</h2>
                                    <p class="lead o_default_snippet_text">Content</p>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    </div>
    <div id="snippet_options" class="d-none">
        <div data-js="many2one" data-selector="[data-oe-many2one-model]:not([data-oe-readonly])" data-no-check="true"/>
        <div data-js="content"
            data-selector=".s_hr, .test_option_all"
            data-drop-in=".note-editable"
            data-drop-near="p, h1, h2, h3, blockquote, .s_hr"/>
        <div data-js="sizing_y" data-selector=".s_hr, .test_option_all"/>
        <div data-selector=".test_option_all">
            <we-colorpicker string="Background Color" data-select-style="true" data-css-property="background-color" data-color-prefix="bg-"/>
        </div>
        <div data-js="BackgroundImage" data-selector=".test_option_all">
            <we-button data-choose-image="true" data-no-preview="true">
                <i class="fa fa-picture-o"/> Background Image
            </we-button>
        </div>
        <div data-js="option_test" data-selector=".s_hr">
            <we-select string="Alignment">
                <we-button data-select-class="align-items-start">Top</we-button>
                <we-button data-select-class="align-items-center">Middle</we-button>
                <we-button data-select-class="align-items-end">Bottom</we-button>
                <we-button data-select-class="align-items-stretch">Equal height</we-button>
            </we-select>
        </div>
    </div>`;

const wait = async (ms = 150) => {
    await new Promise((res) => setTimeout(res, ms))
}

async function iframeReady(iframe) {
    const iframeLoadPromise = makeDeferred();
    iframe.addEventListener("load", function () {
        iframeLoadPromise.resolve();
    });
    if (!iframe.contentDocument.body) {
        await iframeLoadPromise;
    }
    await nextTick(); // ensure document is loaded
}

QUnit.module("WebEditor.HtmlField", ({ beforeEach }) => {
    let serverData;
    let target;

    beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        txt: { string: "txt", type: "html", trim: true },
                    },
                    records: [],
                },
                'note.note': {
                    fields: {
                        display_name: {
                            string: "Displayed name",
                            type: "char"
                        },
                        header: {
                            string: "Header",
                            type: "html",
                            required: true,
                        },
                        body: {
                            string: "Message",
                            type: "html"
                        },
                    },
                    records: [],
                },
                'mail.compose.message': {
                    fields: {
                        display_name: {
                            string: "Displayed name",
                            type: "char"
                        },
                        body: {
                            string: "Message Body inline (to send)",
                            type: "html"
                        },
                        attachment_ids: {
                            string: "Attachments",
                            type: "many2many",
                            relation: "ir.attachment",
                        }
                    },
                    records: [],
                }
            },
        };
        target = getFixture();

        setupViewRegistries();
    });

    QUnit.module('basic');


    QUnit.test('simple rendering', async function (assert) {
        assert.expect(2);
        serverData.models['note.note'].records = [{
            id: 1,
            display_name: "first record",
            header: "<p>  &nbsp;&nbsp;  <br>   </p>",
            body: "<p>toto toto toto</p><p>tata</p>",
        }];

        await makeView({
            type: "form",
            resId: 1,
            resModel: "note.note",
            serverData,
            arch: `
                <form>
                    <field name="body" widget="html" style="height: 100px"/>
                </form>`,
        });

        const field = target.querySelector('.o_field_html[name="body"]');
        const editable = field.querySelector("[contenteditable='true']");
        assert.strictEqual(editable.innerHTML,
            '<p>toto toto toto</p><p>tata</p>',
            "should have rendered a div with correct content");
        assert.strictEqual(field.getAttribute('style'), 'height: 100px',
            "should have applied the style correctly");
    });

    QUnit.test('check if required field is set', async function (assert) {
        assert.expect(3);

        serverData.models['note.note'].records = [{
            id: 1,
            display_name: "first record",
            header: "",
            body: "<p>toto toto toto</p><p>tata</p>",
        }];

        await makeView({
            type: "form",
            resId: 1,
            resModel: "note.note",
            serverData,
            arch: `
                <form>
                    <field name="header" widget="html" style="height: 100px"/>
                </form>`,
        });
        await click(target, '.o_form_button_save');
        assert.containsOnce(target, ".o_notification");
        const notif = target.querySelector(".o_notification");
        assert.strictEqual(
            notif.querySelector(".o_notification_content").textContent,
            "Header"
        );
        assert.hasClass(notif, "border-danger");

    });

    QUnit.test('colorpicker', async function (assert) {
        assert.expect(10);

        serverData.models['note.note'].records = [{
            id: 1,
            display_name: "first record",
            header: "<p>  &nbsp;&nbsp;  <br>   </p>",
            body: "<p>toto toto toto</p><p>tata</p>",
        }];

        // Add the ajax service (legacy), because wysiwyg RPCs use it.
        patchWithCleanup(legacyEnv, {
            services: {
                ...legacyEnv.services,
                ajax: {
                    rpc: async (route, args) => {
                        if (args.model === "ir.ui.view" && args.method === 'render_public_asset') {
                            if (args.args[0] === "web_editor.colorpicker") {
                                return COLOR_PICKER_TEMPLATE;
                            }
                            if (args.args[0] === "web_editor.snippets") {
                                return SNIPPETS_TEMPLATE;
                            }
                        }
                    },
                },
            }
        });

        await makeView({
            type: "form",
            resId: 1,
            resModel: "note.note",
            serverData,
            arch: `
                <form>
                    <field name="body" widget="html" style="height: 100px"/>
                </form>`,
        });

        const field = target.querySelector('.o_field_html[name="body"]');
        const editable = field.querySelector("[contenteditable='true']");
        await click(editable);

        assert.strictEqual(
            window.getComputedStyle(document.querySelector("#toolbar")).getPropertyValue("visibility"),
            "hidden",
            "should hide the toolbar");

        // select the text
        const pText = editable.querySelector("p").firstChild
        Wysiwyg.setRange(pText, 1, pText, 10);
        // text is selected

        var range = Wysiwyg.getRange();

        assert.strictEqual(range.sc, pText,
            "should select the text");

        await wait(1);
        assert.strictEqual(
            window.getComputedStyle(document.querySelector("#toolbar")).getPropertyValue("visibility"),
            "visible",
            "should show the toolbar");


        assert.ok(!document.querySelector(".colorpicker-menu.show"),
            "should hide the color picker");
        await click(document.querySelector("#oe-fore-color"), undefined, true);
        assert.ok(document.querySelector('.o_we_color_btn'),
            "should display some button");
        assert.ok(document.querySelector(".colorpicker-menu.show"),
            "should show the color picker");
        await click(document.querySelector('.o_we_color_btn[style="background-color:#F7C6CE;"]'), undefined, true);
        await wait(100)
        assert.ok(!document.querySelector(".colorpicker-menu.show"),
            "should close the color picker");
        assert.strictEqual(editable.innerHTML,
            "<p>t<font style=\"background-color: rgb(247, 198, 206);\">oto toto </font>toto</p><p>tata</p>",
            "should have rendered the field correctly");

        var fontElement = document.querySelector('.note-editable font');
        var rangeControl = {
            sc: fontElement,
            so: 0,
            ec: fontElement,
            eo: 1,
        };
        range = Wysiwyg.getRange();
        assert.deepEqual(_.pick(range, 'sc', 'so', 'ec', 'eo'), rangeControl,
            "should keep the selected the selected text after color change");

        // select the text
        const pText2 = [...document.querySelector('.note-editable p').childNodes][2];
        Wysiwyg.setRange(fontElement.firstChild, 3, pText2, 2);
        // text is selected

        await wait(1);
        await click(document.querySelector('.o_we_color_btn[data-color="800"]'), undefined, true);
        await wait(100)
        assert.strictEqual(document.querySelector('.note-editable').innerHTML,
            '<p>t<font style="background-color: rgb(247, 198, 206);">oto</font><font style=\"\" class=\"bg-800\"> toto to</font>to</p><p>tata</p>',
            "should have rendered the field correctly");
    });

    QUnit.module('media dialog')

    QUnit.test('media dialog: image', async function (assert) {
        assert.expect(1);

        serverData.models['note.note'].records = [{
            id: 1,
            display_name: "first record",
            header: "<p>  &nbsp;&nbsp;  <br>   </p>",
            body: "<p>toto toto toto</p><p>tata</p>",
        }];

        await makeView({
            type: "form",
            resId: 1,
            resModel: "note.note",
            serverData,
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
        });

        const field = document.querySelector('.o_field_html[name="body"]');
        const pText = field.querySelector('.note-editable p').firstChild;
        Wysiwyg.setRange(pText, 1, pText, 2);

        await new Promise((resolve) => setTimeout(resolve));

        let wysiwyg = [...Wysiwyg.activeWysiwygs]
        wysiwyg = wysiwyg[wysiwyg.length - 1]

        // Mock the MediaDialogWrapper
        const defMediaDialog = testUtils.makeTestPromise();
        patchWithCleanup(MediaDialogWrapper.prototype, {
            setup() {
                useEffect(() => {
                    this.save();
                }, () => []);
            },
            save() {
                const imageEl = document.createElement('img');
                imageEl.src = '/web/image/123/transparent.png';
                this.props.save(imageEl);
                defMediaDialog.resolve();
            },
        });

        wysiwyg.openMediaDialog();
        await defMediaDialog;

        var $editable = wysiwyg.$editable;
        assert.ok($editable.find('img')[0].dataset.src.includes('/web/image/123/transparent.png'),
            "should have the image in the dom");

    });

    QUnit.test('media dialog: icon', async function (assert) {
        assert.expect(1);

        serverData.models['note.note'].records = [{
            id: 1,
            display_name: "first record",
            header: "<p>  &nbsp;&nbsp;  <br>   </p>",
            body: "<p>toto toto toto</p><p>tata</p>",
        }];

        await makeView({
            type: "form",
            resId: 1,
            resModel: "note.note",
            serverData,
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
        });

        const field = document.querySelector('.o_field_html[name="body"]');

        const pText = field.querySelector('.note-editable p').firstChild;
        Wysiwyg.setRange(pText, 1, pText, 2);

        let wysiwyg = [...Wysiwyg.activeWysiwygs];
        wysiwyg = wysiwyg[wysiwyg.length - 1];

        // Mock the MediaDialogWrapper
        const defMediaDialog = testUtils.makeTestPromise();
        patchWithCleanup(MediaDialogWrapper.prototype, {
            setup() {
                useEffect(() => {
                    this.save();
                }, () => []);
            },
            save() {
                const iconEl = document.createElement('span');
                iconEl.classList.add('fa', 'fa-glass');
                this.props.save(iconEl);
                defMediaDialog.resolve();
            },
        });

        wysiwyg.openMediaDialog();
        await defMediaDialog;

        let $editable = wysiwyg.$editable;

        assert.strictEqual($editable.data('wysiwyg').getValue(),
            '<p>t<span class="fa fa-glass"></span>to toto toto</p><p>tata</p>',
            "should have the image in the dom");
    });

    QUnit.test("editor spellcheck is disabled on blur", async function (assert) {
        const target = getFixture();

        serverData.models['note.note'].records = [{
            id: 1,
            display_name: "first record",
            header: "<p>  &nbsp;&nbsp;  <br>   </p>",
            body: "<p>toto toto toto</p><p>tata</p>",
        }];

        await makeView({
            type: "form",
            resModel: "note.note",
            resId: 1,
            serverData,
            arch: `<form><field name="body" widget="html" /></form>`,
        });

        const textarea = target.querySelector(".odoo-editor-editable");
        textarea.focus();
        assert.strictEqual(textarea.spellcheck, true, "spellcheck is enabled");
        textarea.blur();
        assert.strictEqual(
            textarea.spellcheck,
            false,
            "spellcheck is disabled once the field has lost its focus"
        );
        textarea.focus();
        assert.strictEqual(textarea.spellcheck, true, "spellcheck is re-enabled once the field is focused");
    });

    QUnit.module('cssReadonly');

    QUnit.test('rendering with iframe for readonly mode', async function (assert) {
        assert.expect(2);

        legacyTestUtils.mock.patch(ajax, {
            loadAsset: function (xmlId) {
                if (xmlId === 'template.assets') {
                    return Promise.resolve({
                        cssLibs: [],
                        cssContents: ['.o_in_iframe {background-color: red;}'],
                        jsContents: ['window.odoo = {define: function(){}}; // inline asset'],
                    });
                }
                if (xmlId === 'template.assets_all_style') {
                    return Promise.resolve({
                        cssLibs: $('link[href]:not([type="image/x-icon"])').map(function () {
                            return $(this).attr('href');
                        }).get(),
                        cssContents: ['.o_in_iframe {background-color: red;}']
                    });
                }
                if (xmlId === 'web_editor.wysiwyg_iframe_editor_assets') {
                    return Promise.resolve({});
                }
                throw 'Wrong template';
            },
        });

        serverData.models['note.note'].records = [{
            id: 1,
            display_name: "first record",
            header: "<p>  &nbsp;&nbsp;  <br>   </p>",
            body: "<p>toto toto toto</p><p>tata</p>",
        }];

        await makeView({
            type: "form",
            resId: 1,
            resModel: "note.note",
            serverData,
            arch: '<form>' +
                '<field name="body" widget="html" class="oe_read_only" style="height: 100px" options="{\'cssReadonly\': \'template.assets\'}"/>' +
                '</form>',
            mode: "readonly"
        });

        const $field = $('.o_field_html[name="body"]');

        const $iframe = $field.find('iframe.o_readonly');
        await $iframe.data('loadDef');
        const doc = $iframe.contents()[0];
        assert.strictEqual($(doc).find('#iframe_target').html(),
            '<p>toto toto toto</p><p>tata</p>',
            "should have rendered a div with correct content in readonly");

        assert.strictEqual(doc.defaultView.getComputedStyle(doc.body).backgroundColor,
            'rgb(255, 0, 0)',
            "should load the asset css");

        legacyTestUtils.mock.unpatch(ajax);
    });

    QUnit.module('translation');

    QUnit.test('field html translatable', async function (assert) {
        assert.expect(3);

        serverData.models['note.note'].records = [{
            id: 1,
            display_name: "first record",
            header: "<p>  &nbsp;&nbsp;  <br>   </p>",
            body: "<p>toto toto toto</p><p>tata</p>",
        }];
        serverData.models['note.note'].fields.body.translate = true;
        serviceRegistry.add("localization", makeFakeLocalizationService({ multiLang: true }), {
            force: true,
        });

        await makeView({
            type: "form",
            resId: 1,
            resModel: "note.note",
            serverData,
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/note.note/get_field_translations") {
                    assert.deepEqual(args.args, [[1], "body"], "should translate the body field of the record");
                    return Promise.resolve([
                        [{ lang: "en_US", source: "first paragraph", value: "first paragraph" },
                        { lang: "en_US", source: "second paragraph", value: "second paragraph" },
                        { lang: "fr_BE", source: "first paragraph", value: "premier paragraphe" },
                        { lang: "fr_BE", source: "second paragraph", value: "deuxième paragraphe" }],
                        { translation_type: "text", translation_show_source: true },
                    ]);
                }
                if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                    return Promise.resolve([["en_US", "English"], ["fr_BE", "French (Belgium)"]]);
                }
            }
        });

        const fixture = document.querySelector("#qunit-fixture")
        const buttons = [...fixture.querySelectorAll('.o_field_translate')];
        const button = buttons[0];
        assert.strictEqual(buttons.length, 1, "should have a translate button");
        await click(button, undefined, true);
        assert.strictEqual([...document.querySelectorAll('.o_translation_dialog')].length, 1, 'should have a modal to translate');
    });

    QUnit.module('Sandboxed Preview');

    QUnit.test("complex html is automatically in sandboxed preview mode", async (assert) => {
        serverData.models.partner.records = [{
            id: 1,
            txt: `
            <!DOCTYPE HTML>
            <html xml:lang="en" lang="en">
                <head>

                    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
                    <meta name="format-detection" content="telephone=no"/>
                    <style type="text/css">
                        body {
                            color: blue;
                        }
                    </style>
                </head>
                <body>
                    Hello
                </body>
            </html>
            `,
        }];
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
        });

        assert.containsOnce(target, '.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]');
    });

    QUnit.test("readonly sandboxed preview", async (assert) => {
        serverData.models.partner.records = [{
            id: 1,
            txt: `
            <!DOCTYPE HTML>
            <html xml:lang="en" lang="en">
                <head>

                    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
                    <meta name="format-detection" content="telephone=no"/>
                    <style type="text/css">
                        body {
                            color: blue;
                        }
                    </style>
                </head>
                <body>
                    Hello
                </body>
            </html>`,
        }];
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form string="Partner">
                    <field name="txt" widget="html" readonly="1" options="{'sandboxedPreview': true}"/>
                </form>`,
        });

        const readonlyIframe = target.querySelector('.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]');
        assert.ok(readonlyIframe);
        await iframeReady(readonlyIframe);
        assert.strictEqual(readonlyIframe.contentDocument.body.innerText, 'Hello');
        assert.strictEqual(readonlyIframe.contentWindow.getComputedStyle(readonlyIframe.contentDocument.body).color, 'rgb(0, 0, 255)');

        assert.containsN(target, '#codeview-btn-group > button', 0, 'Codeview toggle should not be possible in readonly mode.');
    });

    QUnit.test("sandboxed preview display and editing", async (assert) => {
        let codeViewState = false;
        const togglePromises = [makeDeferred(), makeDeferred()];
        let togglePromiseId = 0;
        const writePromise = makeDeferred();
        patchWithCleanup(HtmlField.prototype, {
            setup: function () {
                this._super(...arguments);
                onRendered(() => {
                    if (codeViewState !== this.state.showCodeView) {
                        togglePromises[togglePromiseId].resolve();
                    }
                    codeViewState = this.state.showCodeView;
                });
            },
        });
        const htmlDocumentTextTemplate = (text, color) => `
        <html>
            <head>
                <style>
                    body {
                        color: ${color};
                    }
                </style>
            </head>
            <body>
                ${text}
            </body>
        </html>
        `;
        serverData.models.partner.records = [{
            id: 1,
            txt: htmlDocumentTextTemplate('Hello', 'red'),
        }];
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                                <page string="Body" name="body">
                                    <field name="txt" widget="html" options="{'sandboxedPreview': true}"/>
                                </page>
                        </notebook>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "write" && args.model === 'partner') {
                    assert.equal(args.args[1].txt, htmlDocumentTextTemplate('Hi', 'blue'));
                    writePromise.resolve();
                }
            }
        });

        // check original displayed content
        let iframe = target.querySelector('.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]');
        assert.ok(iframe, 'Should use a sanboxed iframe');
        await iframeReady(iframe);
        assert.strictEqual(iframe.contentDocument.body.textContent.trim(), 'Hello');
        assert.strictEqual(iframe.contentDocument.head.querySelector('style').textContent.trim().replace(/\s/g, ''),
            'body{color:red;}', 'Head nodes should remain unaltered in the head');
        assert.equal(iframe.contentWindow.getComputedStyle(iframe.contentDocument.body).color, 'rgb(255, 0, 0)');
        // check button is there
        assert.containsOnce(target, '#codeview-btn-group > button');
        // edit in xml editor
        await click(target, '#codeview-btn-group > button');
        await togglePromises[togglePromiseId];
        togglePromiseId++;
        assert.containsOnce(target, '.o_field_html[name="txt"] textarea');
        await editInput(target, '.o_field_html[name="txt"] textarea', htmlDocumentTextTemplate('Hi', 'blue'));
        await click(target, '#codeview-btn-group > button');
        await togglePromises[togglePromiseId];
        // check dispayed content after edit
        iframe = target.querySelector('.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]');
        await iframeReady(iframe);
        assert.strictEqual(iframe.contentDocument.body.textContent.trim(), 'Hi');
        assert.strictEqual(iframe.contentDocument.head.querySelector('style').textContent.trim().replace(/\s/g, ''),
            'body{color:blue;}', 'Head nodes should remain unaltered in the head');
        assert.equal(iframe.contentWindow.getComputedStyle(iframe.contentDocument.body).color, 'rgb(0, 0, 255)',
            'Style should be applied inside the iframe.');

        const saveButton = target.querySelector('.o_form_button_save');
        assert.ok(saveButton);
        await click(saveButton);
        await writePromise;
    });


    QUnit.test("sanboxed preview mode not automatically enabled for regular values", async (assert) => {
        serverData.models.partner.records = [{
            id: 1,
            txt: `
                <body>
                    <p>Hello</p>
                </body>
            `,
        }];
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
        });

        assert.containsN(target, '.o_field_html[name="txt"] iframe[sandbox]', 0);
        assert.containsN(target, '.o_field_html[name="txt"] textarea', 0);
    });

    QUnit.test("sandboxed preview option applies even for simple text", async (assert) => {
        serverData.models.partner.records = [{
            id: 1,
            txt: `
                Hello
            `,
        }];
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="txt" widget="html" options="{'sandboxedPreview': true}"/>
                </form>`,
        });

        assert.containsOnce(target, '.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]');
    });

    QUnit.module('Readonly mode');

    QUnit.test("Links should open on a new tab", async (assert) => {
        assert.expect(6);
        serverData.models.partner.records = [{
            id: 1,
            txt: `
                <body>
                    <a href="/contactus">Relative link</a>
                    <a href="${location.origin}/contactus">Internal link</a>
                    <a href="https://google.com">External link</a>
                </body>`,
        }];
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="txt" widget="html" readonly="1"/>
                </form>`,
        });

        for (const link of target.querySelectorAll('a')) {
            assert.strictEqual(link.getAttribute('target'), '_blank');
            assert.strictEqual(link.getAttribute('rel'), 'noreferrer');
        }
    });

    QUnit.module('Save scenarios');

    QUnit.test("Ensure that urgentSave works even with modified image to save", async (assert) => {
        assert.expect(5);
        let formController;
        // Patch to get the controller instance.
        patchWithCleanup(FormController.prototype, {
            setup() {
                this._super(...arguments);
                formController = this;
            }
        });
        // Patch to get a promise to get the htmlField component instance when
        // the wysiwyg is instancied.
        const htmlFieldPromise = makeDeferred();
        patchWithCleanup(HtmlField.prototype, {
            async startWysiwyg() {
                await this._super(...arguments);
                await nextTick();
                htmlFieldPromise.resolve(this);
            }
        });
        // Add a partner record and ir.attachments model and record.
        serverData.models.partner.records.push({
            id: 1,
            txt: "<p class='test_target'><br></p>",
        });
        serverData.models["ir.attachment"] = wysiwygData({})["ir.attachment"];
        const imageRecord = serverData.models["ir.attachment"].records[0];
        // Method to get the html of a cropped image.
        // Use `data-src` instead of `src` when the SRC is an URL that would
        // make a call to the server.
        const getImageContainerHTML = (src, isModified) => {
            return `
                <p>
                    <img
                        class="img img-fluid o_we_custom_image o_we_image_cropped${isModified ? ' o_modified_image_to_save' : ''}"
                        data-original-id="${imageRecord.id}"
                        data-original-src="${imageRecord.image_src}"
                        data-mimetype="image/png"
                        data-width="50"
                        data-height="50"
                        data-scale-x="1"
                        data-scale-y="1"
                        data-aspect-ratio="0/0"
                        ${src.startsWith("/web") ? 'data-src="' : 'src="'}${src}"
                    >
                    <br>
                </p>
            `.replace(/(?:\s|(?:\r\n))+/g, ' ')
                .replace(/\s?(<|>)\s?/g, '$1');
        };
        // Promise to resolve when we want the response of the modify_image RPC.
        const modifyImagePromise = makeDeferred();
        let writeCount = 0;
        let modifyImageCount = 0;
        // Valid base64 encoded image in its transitory modified state.
        const imageContainerHTML = getImageContainerHTML(
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII",
            true
        );
        // New src URL to assign to the image when the modification is
        // "registered".
        const newImageSrc = "/web/image/1234/cropped_transparent.png";
        const mockRPC = async function (route, args) {
            if (
                route === '/web/dataset/call_kw/partner/write' &&
                args.model === 'partner'
            ) {
                if (writeCount === 0) {
                    // Save normal value without image.
                    assert.equal(args.args[1].txt, `<p class="test_target"><br></p>`);
                } else if (writeCount === 1) {
                    // Save image with unfinished modification changes.
                    assert.equal(args.args[1].txt, imageContainerHTML);
                } else if (writeCount === 2) {
                    // Save the modified image.
                    assert.equal(args.args[1].txt, getImageContainerHTML(newImageSrc, false));
                } else {
                    // Fail the test if too many write are called.
                    assert.ok(writeCount === 2, "Write should only be called 3 times during this test");
                }
                writeCount += 1;
            } else if (
                route === `/web_editor/modify_image/${imageRecord.id}`
            ) {
                if (modifyImageCount === 0) {
                    assert.equal(args.res_model, 'partner');
                    assert.equal(args.res_id, 1);
                    await modifyImagePromise;
                    return newImageSrc;
                } else {
                    // Fail the test if too many modify_image are called.
                    assert.ok(modifyImageCount === 0, "The image should only have been modified once during this test");
                }
                modifyImageCount += 1;
            }
        };
        // Add the ajax service (legacy), because wysiwyg RPCs use it.
        patchWithCleanup(legacyEnv, {
            services: {
                ...legacyEnv.services,
                ajax: {
                    rpc: mockRPC,
                },
            }
        });
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
            mockRPC: mockRPC,
        });
        // Let the htmlField be mounted and recover the Component instance.
        const htmlField = await htmlFieldPromise;
        const editor = htmlField.wysiwyg.odooEditor;

        // Simulate an urgent save without any image in the content.
        await formController.beforeUnload();
        await nextTick();

        // Replace the empty paragraph with a paragrah containing an unsaved
        // modified image
        const imageContainerElement = parseHTML(imageContainerHTML).firstChild;
        let paragraph = editor.editable.querySelector(".test_target");
        editor.editable.replaceChild(imageContainerElement, paragraph);
        editor.historyStep();

        // Simulate an urgent save before the end of the RPC roundtrip for the
        // image.
        await formController.beforeUnload();
        await nextTick();

        // Resolve the image modification (simulate end of RPC roundtrip).
        modifyImagePromise.resolve();
        await modifyImagePromise;
        await nextTick();

        // Simulate the last urgent save, with the modified image.
        await formController.beforeUnload();
        await nextTick();
    });

    QUnit.test("Pasted/dropped images are converted to attachments on save", async (assert) => {
        assert.expect(6);

        // Patch to get a promise to get the htmlField component instance when
        // the wysiwyg is instancied.
        const htmlFieldPromise = makeDeferred();
        patchWithCleanup(HtmlField.prototype, {
            async startWysiwyg() {
                await this._super(...arguments);
                await nextTick();
                htmlFieldPromise.resolve(this);
            }
        });
        // Add a partner record
        serverData.models.partner.records.push({
            id: 1,
            txt: "<p class='test_target'><br></p>",
        });

        const mockRPC = async function (route, args) {
            if (route === '/web_editor/attachment/add_data') {
                // Check that the correct record model and id were sent.
                assert.equal(args.res_model, 'partner');
                assert.equal(args.res_id, 1);
                return {
                    image_src: '/test_image_url.png',
                    access_token: '1234',
                    public: false,
                }
            }
        };

        const pasteImage = async (editor) => {
            // Create image file.
            const base64ImageData = "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII"
            const binaryImageData = atob(base64ImageData);
            const uint8Array = new Uint8Array(binaryImageData.length);
            for (let i = 0; i < binaryImageData.length; i++) {
                uint8Array[i] = binaryImageData.charCodeAt(i);
            }
            const file = new File([uint8Array], "test_image.png", { type: 'image/png' });

            // Create a promise to get the created img elements
            const pasteImagePromise = makeDeferred();
            const observer = new MutationObserver(mutations => {
                mutations
                    .filter(mutation => mutation.type === 'childList')
                    .forEach(mutation => {
                        mutation.addedNodes.forEach(node => {
                            if (node instanceof HTMLElement) {
                                pasteImagePromise.resolve(node);
                            }
                        });
                    });
            });
            observer.observe(editor.editable, { subtree: true, childList: true });

            // Simulate paste.
            editor._onPaste({
                preventDefault() { },
                clipboardData: {
                    getData() { },
                    items: [{
                        kind: 'file',
                        type: 'image/png',
                        getAsFile: () => file,
                    }],
                },
            });

            const img = await pasteImagePromise;
            observer.disconnect();
            return img;
        }

        // Add the ajax service (legacy), because wysiwyg RPCs use it.
        patchWithCleanup(legacyEnv, {
            services: {
                ...legacyEnv.services,
                ajax: {
                    rpc: mockRPC,
                },
            }
        });
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
            mockRPC: mockRPC,
        });
        // Let the htmlField be mounted and recover the Component instance.
        const htmlField = await htmlFieldPromise;
        const editor = htmlField.wysiwyg.odooEditor;

        const paragraph = editor.editable.querySelector(".test_target");
        Wysiwyg.setRange(paragraph);

        // Paste image.
        const img = await pasteImage(editor);
        // Test environment replaces 'src' by 'data-src'.
        assert.ok(/^data:image\/png;base64,/.test(img.dataset['src']));
        assert.ok(img.classList.contains('o_b64_image_to_save'));

        // Save changes.
        // Restore 'src' attribute so that SavePendingImages can do its job.
        img.src = img.dataset['src'];
        await htmlField.commitChanges();
        assert.equal(img.dataset['src'], '/test_image_url.png?access_token=1234');
        assert.ok(!img.classList.contains('o_b64_image_to_save'));
    });
});
