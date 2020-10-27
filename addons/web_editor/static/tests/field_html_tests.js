odoo.define('web_editor.field_html_tests', function (require) {
"use strict";

var ajax = require('web.ajax');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var weTestUtils = require('web_editor.test_utils');
var core = require('web.core');
var Wysiwyg = require('web_editor.wysiwyg');
var MediaDialog = require('wysiwyg.widgets.MediaDialog');
var FieldHtml = require('web_editor.field.html');

var _t = core._t;

QUnit.module('web_editor', {}, function () {

    QUnit.module('field html', {
        beforeEach: function () {
            this.data = weTestUtils.wysiwygData({
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
                    records: [{
                        id: 1,
                        display_name: "first record",
                        header: "<p>  &nbsp;&nbsp;  <br>   </p>",
                        body: "<p>toto toto toto</p><p>tata</p>",
                    }],
                },
                'mass.mailing': {
                    fields: {
                        display_name: {
                            string: "Displayed name",
                            type: "char"
                        },
                        body_html: {
                            string: "Message Body inline (to send)",
                            type: "html"
                        },
                        body_arch: {
                            string: "Message Body for edition",
                            type: "html"
                        },
                    },
                    records: [{
                        id: 1,
                        display_name: "first record",
                        body_html: "<div class='field_body' style='background-color: red;'>yep</div>",
                        body_arch: "<div class='field_body'>yep</div>",
                    }],
                },
                "ir.translation": {
                    fields: {
                        lang_code: {type: "char"},
                        value: {type: "char"},
                        res_id: {type: "integer"}
                    },
                    records: [{
                        id: 99,
                        res_id: 12,
                        value: '',
                        lang_code: 'en_US'
                    }]
                },
            });

            testUtils.mock.patch(ajax, {
                loadAsset: function (xmlId) {
                    if (xmlId === 'template.assets') {
                        return Promise.resolve({
                            cssLibs: [],
                            cssContents: ['body {background-color: red;}']
                        });
                    }
                    if (xmlId === 'template.assets_all_style') {
                        return Promise.resolve({
                            cssLibs: $('link[href]:not([type="image/x-icon"])').map(function () {
                                return $(this).attr('href');
                            }).get(),
                            cssContents: ['body {background-color: red;}']
                        });
                    }
                    throw 'Wrong template';
                },
            });
            testUtils.mock.patch(FieldHtml, {
                _createWysiwygIntance: weTestUtils.createWysiwyg
            });
        },
        afterEach: function () {
            testUtils.mock.unpatch(FieldHtml);
        },
    }, function () {

        QUnit.module('basic');

        QUnit.test('simple rendering', async function (assert) {
            assert.expect(3);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 1,
            });
            var $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(),
                '<p>toto toto toto</p><p>tata</p>',
                "should have rendered a div with correct content in readonly");
            assert.strictEqual($field.attr('style'), 'height: 100px',
                "should have applied the style correctly");

            await testUtils.form.clickEdit(form);
            await testUtils.nextTick();
            $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.find('.note-editable').html(),
                '<p>toto toto toto</p><p>tata</p>',
                "should have rendered the field correctly in edit");

            form.destroy();
        });
        QUnit.test('check if required field is set', async function (assert) {
            assert.expect(1);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                        '<field name="header" widget="html" style="height: 100px" />' +
                      '</form>',
                res_id: 1,
            });

            testUtils.mock.intercept(form, 'call_service', function (ev) {
                if (ev.data.service === 'notification') {
                    assert.deepEqual(ev.data.args[0], {
                        "className": undefined,
                        "message": "<ul><li>Header</li></ul>",
                        "sticky": undefined,
                        "title": "Invalid fields:",
                        "type": "danger"
                      });
                }
            }, true);

            await testUtils.form.clickEdit(form);
            await testUtils.nextTick();
            await testUtils.dom.click(form.$('.o_form_button_save'));

            form.destroy();
        });

        QUnit.test('colorpicker', async function (assert) {
            assert.expect(5);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 1,
            });

            // Summernote needs a RootWidget to set as parent of the ColorPaletteWidget. In the
            // tests, there is no RootWidget, so we set it here to the parent of the form view, which
            // can act as RootWidget, as it will honor rpc requests correctly (to the MockServer).
            const rootWidget = odoo.__DEBUG__.services['root.widget'];
            odoo.__DEBUG__.services['root.widget'] = form.getParent();

            await testUtils.form.clickEdit(form);
            await testUtils.nextTick();

            var $field = $('.oe_form_field[name="body"]');
            var pText = $field.find('.note-editable p').first().contents()[0];

            var wysiwyg = form.renderer.allFieldWidgets["note.note_1"][0].wysiwyg

            await testUtils.nextTick();
            // select the text
            await Wysiwyg.setRange(wysiwyg, pText, 1, pText, 9);
            // text is selected

            var range = await Wysiwyg.getRange($field[0]);
            assert.strictEqual(range.sc, pText,
                "should select the text");

            async function openColorpicker() {
                const $colorpickerButton = $('jw-toolbar jw-button[name=backgroundcolorpicker]');
                await testUtils.dom.click($colorpickerButton);
            }

            await testUtils.nextTick();
            await new Promise(resolve => setTimeout(resolve, 100));
            await openColorpicker();
            await testUtils.nextTick();
            await new Promise(resolve => setTimeout(resolve, 100));
            assert.ok($('.jw-dropdown-backgroundcolor .dropdown-menu').is(':visible'),
                "should display the color picker");

            await testUtils.dom.click($('.jw-dropdown-backgroundcolor .o_we_color_btn[style="background-color:#00FFFF;"]'));
            assert.ok(!$field.find('.o_colorpicker_container').is(':visible'),
                "should close the color picker");

            assert.strictEqual($field.find('.note-editable').html(),
                '<p>t<span style="background-color: rgb(0, 255, 255);">oto toto </span>toto</p><p>tata</p>',
                "should have rendered the field correctly in edit");

            var allContent = $field.find('.note-editable p').contents()[0];
            var fontContent = $field.find('.note-editable span').contents()[0];
            var rangeControl = {
                sc: allContent,
                so: 1,
                ec: fontContent,
                eo: fontContent.length,
            };
            range = Wysiwyg.getRange($field[0]);
            assert.deepEqual(_.pick(range, 'sc', 'so', 'ec', 'eo'), rangeControl,
                "should select the text after color change");

            // TODO : FIX THIS TEST
            // temporary skipping this QUnit tests about css class color
            // need to be improve in JW
            //
            // select the text
            // pText = $field.find('.note-editable p').first().contents()[2];
            // Wysiwyg.setRange(wysiwyg, fontContent, 5, pText, 2);
            // text is selected
            // await testUtils.nextTick();;
            // await openColorpicker();
            // await testUtils.nextTick();;
            // await testUtils.dom.click($('.jw-dropdown-backgroundcolor .o_we_color_btn.bg-o-color-3'));
            //
            // assert.strictEqual($field.find('.note-editable').html(),
            //     '<p>t<span style="background-color: rgb(0, 255, 255);">oto t</span><span style="" class="bg-o-color-3">oto&nbsp;</span><span class="bg-o-color-3" style="">to</span>to</p><p>tata</p>',
            //     "should have rendered the field correctly in edit");

            odoo.__DEBUG__.services['root.widget'] = rootWidget;
            form.destroy();
        });

        QUnit.test('media dialog: image', async function (assert) {
            assert.expect(1);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.model === 'ir.attachment') {
                        if (args.method === "generate_access_token") {
                            return Promise.resolve();
                        }
                    }
                    if (route.indexOf('/web/image/123/transparent.png') === 0) {
                        return Promise.resolve();
                    }
                    if (route.indexOf('/web_unsplash/fetch_images') === 0) {
                        return Promise.resolve();
                    }
                    if (route.indexOf('/web_editor/media_library_search') === 0) {
                        return Promise.resolve();
                    }
                    return this._super(route, args);
                },
            });
            await testUtils.form.clickEdit(form);
            await testUtils.nextTick();
            var $field = form.$('.oe_form_field[name="body"]');
            var wysiwyg = form.renderer.allFieldWidgets["note.note_1"][0].wysiwyg


            // the dialog load some xml assets
            var defMediaDialog = testUtils.makeTestPromise();
            testUtils.mock.patch(MediaDialog, {
                init: function () {
                    this._super.apply(this, arguments);
                    this.opened(defMediaDialog.resolve.bind(defMediaDialog));
                }
            });

            var pText = $field.find('.note-editable p').first().contents()[0];
            await Wysiwyg.setRange(wysiwyg, pText, 1, pText, 3);
            await testUtils.nextTick();
            await new Promise(resolve => setTimeout(resolve, 100));
            await testUtils.dom.click($('jw-toolbar jw-button[name=media]'));
            await testUtils.nextTick();

            // load static xml file (dialog, media dialog, unsplash image widget)
            await defMediaDialog;

            await testUtils.dom.click($('.modal #editor-media-image .o_existing_attachment_cell:first').removeClass('d-none'));

            var $editable = form.$('.oe_form_field[name="body"] .note-editable');
            assert.ok($editable.find('img')[0].dataset.src.includes('/web/image/123/transparent.png'),
                "should have the image in the dom");

            testUtils.mock.unpatch(MediaDialog);

            form.destroy();
        });

        QUnit.test('media dialog: icon', async function (assert) {
            assert.expect(1);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.model === 'ir.attachment') {
                        return Promise.resolve([]);
                    }
                    if (route.indexOf('/web_unsplash/fetch_images') === 0) {
                        return Promise.resolve();
                    }
                    return this._super(route, args);
                },
            });
            await testUtils.form.clickEdit(form);
            await testUtils.nextTick();
            var $field = form.$('.oe_form_field[name="body"]');
            var wysiwyg = form.renderer.allFieldWidgets["note.note_1"][0].wysiwyg

            // the dialog load some xml assets
            var defMediaDialog = testUtils.makeTestPromise();
            testUtils.mock.patch(MediaDialog, {
                init: function () {
                    this._super.apply(this, arguments);
                    this.opened(defMediaDialog.resolve.bind(defMediaDialog));
                }
            });

            var pText = $field.find('.note-editable p').first().contents()[0];

            await Wysiwyg.setRange(wysiwyg, pText, 1, pText, 3);
            await testUtils.nextTick();
            await new Promise(resolve => setTimeout(resolve, 100));
            await testUtils.dom.click($('jw-toolbar jw-button[name=media]'));
            await testUtils.nextTick();;

            // load static xml file (dialog, media dialog, unsplash image widget)
            await defMediaDialog;
            $('.modal .tab-content .tab-pane').removeClass('fade'); // to be sync in test
            await testUtils.dom.click($('.modal a[aria-controls="editor-media-icon"]'));
            await testUtils.dom.click($('.modal #editor-media-icon .font-icons-icon.fa-glass'));

            assert.strictEqual($field.find('.note-editable').html(),
                '<p>t​<span class="fa fa-glass"></span>​ toto toto</p><p>tata</p>',
                "should have the image in the dom");

            testUtils.mock.unpatch(MediaDialog);

            form.destroy();
        });

        QUnit.test('save', async function (assert) {
            assert.expect(1);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.strictEqual(args.args[1].body,
                            '<p>t<span style="background-color:#00FFFF;">oto toto </span>toto</p><p>tata</p>',
                            "should save the content");

                    }
                    return this._super.apply(this, arguments);
                },
            });
            await testUtils.form.clickEdit(form);
            await testUtils.nextTick();
            var $field = form.$('.oe_form_field[name="body"]');

            // select the text
            var pText = $field.find('.note-editable p').first().contents()[0];
            var wysiwyg = form.renderer.allFieldWidgets["note.note_1"][0].wysiwyg
            await Wysiwyg.setRange(wysiwyg, pText, 1, pText, 9);
            // text is selected

            async function openColorpicker() {
                const $colorpickerButton = $('jw-toolbar jw-button[name=backgroundcolorpicker]');
                await testUtils.dom.click($colorpickerButton);
            }

            await testUtils.nextTick();
            await new Promise((resolve) => wysiwyg.editor.execCommand(resolve));
            await openColorpicker();
            await testUtils.nextTick();

            await new Promise((resolve) => wysiwyg.editor.execCommand(resolve));
            await testUtils.dom.click($('jw-toolbar .o_we_color_btn[style="background-color:#00FFFF;"]'));
            await testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.module('cssReadonly');

        QUnit.test('rendering with iframe for readonly mode', async function (assert) {
            assert.expect(2);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px" options="{\'cssReadonly\': \'template.assets\'}"/>' +
                    '</form>',
                res_id: 1,
            });
            var $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field[0].shadowRoot.innerHTML,
                '<style type="text/css">body {background-color: red;}</style><p>toto toto toto</p><p>tata</p>',
                "should have rendered a div with correct content in readonly and should load the asset css");

            await testUtils.form.clickEdit(form);
            await testUtils.nextTick();

            $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.find('.note-editable').html(),
                '<p>toto toto toto</p><p>tata</p>',
                "should have rendered the field correctly in edit");

            form.destroy();
        });

        QUnit.module('translation');

        // TODO : need to be checked and fixed to pass with new JW editor
        QUnit.skip('field html translatable', async function (assert) {
            assert.expect(4);

            var multiLang = _t.database.multi_lang;
            _t.database.multi_lang = true;

            this.data['note.note'].fields.body.translate = true;

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="body" widget="html"/>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_button' && args.method === 'translate_fields') {
                        assert.deepEqual(args.args, ['note.note', 1, 'body'], "should call 'call_button' route");
                        return Promise.resolve({
                            domain: [],
                            context: {search_default_name: 'partnes,foo'},
                        });
                    }
                    if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                        return Promise.resolve([["en_US"], ["fr_BE"]]);
                    }
                    return this._super.apply(this, arguments);
                },
            });
            assert.strictEqual(form.$('.oe_form_field_html .o_field_translate').length, 0,
                "should not have a translate button in readonly mode");

            await testUtils.form.clickEdit(form);
            var $button = form.$('.oe_form_field_html .o_field_translate');
            assert.strictEqual($button.length, 1, "should have a translate button");
            await testUtils.dom.click($button);
            assert.containsOnce($(document), '.o_translation_dialog', 'should have a modal to translate');

            form.destroy();
            _t.database.multi_lang = multiLang;
        });
    });
});
});
