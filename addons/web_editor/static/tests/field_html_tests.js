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
                    }, {
                        id: 2,
                        display_name: "second record",
                        header: "<p>  &nbsp;&nbsp;  <br>   </p>",
                        body: `
<div class="o_form_sheet_bg">
  <div class="clearfix position-relative o_form_sheet" style="width: 1140px;">
    <div class="o_notebook">
      <div class="tab-content">
        <div class="tab-pane active" id="notebook_page_820">
          <div class="oe_form_field oe_form_field_html o_field_widget" name="description" style="margin-bottom: 5px;">
            hacky code to test
          </div>
        </div>
      </div>
    </div>
  </div>
</div>`,
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
        },
        afterEach: function () {
            testUtils.mock.unpatch(ajax);
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

        QUnit.test('notebooks defined inside HTML field widgets are ignored when calling setLocalState', async function (assert) {
            assert.expect(1);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 2,
            });
            // check that there is no error on clicking Edit
            await testUtils.form.clickEdit(form);
            await testUtils.nextTick();
            assert.containsOnce(form, '.o_form_editable');

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
            assert.expect(6);

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
            var $field = form.$('.oe_form_field[name="body"]');

            // select the text
            var pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 1, pText, 10);
            // text is selected

            var range = Wysiwyg.getRange($field[0]);
            assert.strictEqual(range.sc, pText,
                "should select the text");

            async function openColorpicker(selector) {
                const $colorpicker = $field.find(selector);
                const openingProm = new Promise(resolve => {
                    $colorpicker.one('shown.bs.dropdown', () => resolve());
                });
                await testUtils.dom.click($colorpicker.find('button:first'));
                return openingProm;
            }

            await openColorpicker('.note-toolbar .note-back-color-preview');
            assert.ok($field.find('.note-back-color-preview').hasClass('show'),
                "should display the color picker");

            await testUtils.dom.click($field.find('.note-toolbar .note-back-color-preview .o_we_color_btn[style="background-color:#00FFFF;"]'));

            assert.ok(!$field.find('.note-back-color-preview').hasClass('show'),
                "should close the color picker");

            assert.strictEqual($field.find('.note-editable').html(),
                '<p>t<font style="background-color: rgb(0, 255, 255);">oto toto&nbsp;</font>toto</p><p>tata</p>',
                "should have rendered the field correctly in edit");

            var fontContent = $field.find('.note-editable font').contents()[0];
            var rangeControl = {
                sc: fontContent,
                so: 0,
                ec: fontContent,
                eo: fontContent.length,
            };
            range = Wysiwyg.getRange($field[0]);
            assert.deepEqual(_.pick(range, 'sc', 'so', 'ec', 'eo'), rangeControl,
                "should select the text after color change");

            // select the text
            pText = $field.find('.note-editable p').first().contents()[2];
            Wysiwyg.setRange(fontContent, 5, pText, 2);
            // text is selected

            await openColorpicker('.note-toolbar .note-back-color-preview');
            await testUtils.dom.click($field.find('.note-toolbar .note-back-color-preview .o_we_color_btn.bg-o-color-3'));

            assert.strictEqual($field.find('.note-editable').html(),
                '<p>t<font style="background-color: rgb(0, 255, 255);">oto t</font><font style="" class="bg-o-color-3">oto&nbsp;</font><font class="bg-o-color-3" style="">to</font>to</p><p>tata</p>',
                "should have rendered the field correctly in edit");

            odoo.__DEBUG__.services['root.widget'] = rootWidget;
            form.destroy();
        });

    QUnit.test('media dialog: upload', async function (assert) {
            /**
             * Ensures _onAttachmentChange from FieldHTML is called on file upload
             */
            assert.expect(1);
            const onAttachmentChangeTriggered = testUtils.makeTestPromise();
            testUtils.mock.patch(FieldHtml, {
                '_onAttachmentChange': function (event) {
                    onAttachmentChangeTriggered.resolve(true);
                }
            });

            const form = await testUtils.createView({
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
                    if (route.indexOf('/web_editor/attachment/add_data') === 0) {
                        return Promise.resolve({"id": 5, "name": "test.jpg", "description": false, "mimetype": "image/jpeg", "checksum": "7951a43bbfb08fd742224ada280913d1897b89ab",
                                                "url": false, "type": "binary", "res_id": 1, "res_model": "note.note", "public": false, "access_token": false,
                                                "image_src": "/web/image/1-a0e63e61/test.jpg", "image_width": 1, "image_height": 1, "original_id": false
                                                });
                        }
                    return this._super(route, args);
                },
            });
            await testUtils.form.clickEdit(form);
            const $field = form.$('.oe_form_field[name="body"]');

            //init mock file data
            const fileB64 = '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigD//2Q==';
            const fileBytes = new Uint8Array(atob(fileB64).split('').map(char => char.charCodeAt(0)));

            // the dialog load some xml assets
            const defMediaDialog = testUtils.makeTestPromise();
            testUtils.mock.patch(MediaDialog, {
                init: function () {
                    this._super.apply(this, arguments);
                    this.opened(defMediaDialog.resolve.bind(defMediaDialog));
                    this.opened(()=>{
                        const input = this.activeWidget.$fileInput.get(0);
                        Object.defineProperty(input, 'files', {
                            value: [new File(fileBytes, "test.jpg", { type: 'image/jpeg' })],
                        });
                        this.activeWidget._onFileInputChange();
                        })
                },
            });

            const pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 1);

            await testUtils.dom.click($field.find('.note-toolbar .note-insert button:has(.fa-file-image-o)'));

            // load static xml file (dialog, media dialog, unsplash image widget)
            await defMediaDialog;

            assert.ok(await Promise.race([onAttachmentChangeTriggered, new Promise((res, _) => setTimeout(() => res(false), 400))]),
                      "_onAttachmentChange was not called with the new attachment, necessary for unsused upload cleanup on backend");

            testUtils.mock.unpatch(MediaDialog);
            testUtils.mock.unpatch(FieldHtml)
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
            var $field = form.$('.oe_form_field[name="body"]');

            // the dialog load some xml assets
            var defMediaDialog = testUtils.makeTestPromise();
            testUtils.mock.patch(MediaDialog, {
                init: function () {
                    this._super.apply(this, arguments);
                    this.opened(defMediaDialog.resolve.bind(defMediaDialog));
                }
            });

            var pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 1);

            await testUtils.dom.click($field.find('.note-toolbar .note-insert button:has(.fa-file-image-o)'));

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
            var $field = form.$('.oe_form_field[name="body"]');

            // the dialog load some xml assets
            var defMediaDialog = testUtils.makeTestPromise();
            testUtils.mock.patch(MediaDialog, {
                init: function () {
                    this._super.apply(this, arguments);
                    this.opened(defMediaDialog.resolve.bind(defMediaDialog));
                }
            });

            var pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 1);

            await testUtils.dom.click($field.find('.note-toolbar .note-insert button:has(.fa-file-image-o)'));

            // load static xml file (dialog, media dialog, unsplash image widget)
            await defMediaDialog;
            $('.modal .tab-content .tab-pane').removeClass('fade'); // to be sync in test
            await testUtils.dom.click($('.modal a[aria-controls="editor-media-icon"]'));
            await testUtils.dom.click($('.modal #editor-media-icon .font-icons-icon.fa-glass'));

            var $editable = form.$('.oe_form_field[name="body"] .note-editable');

            assert.strictEqual($editable.data('wysiwyg').getValue(),
                '<p>t<span class="fa fa-glass"></span>oto toto toto</p><p>tata</p>',
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
                            '<p>t<font class="bg-o-color-3">oto toto&nbsp;</font>toto</p><p>tata</p>',
                            "should save the content");

                    }
                    return this._super.apply(this, arguments);
                },
            });
            await testUtils.form.clickEdit(form);
            var $field = form.$('.oe_form_field[name="body"]');

            // select the text
            var pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 1, pText, 10);
            // text is selected

            async function openColorpicker(selector) {
                const $colorpicker = $field.find(selector);
                const openingProm = new Promise(resolve => {
                    $colorpicker.one('shown.bs.dropdown', () => resolve());
                });
                await testUtils.dom.click($colorpicker.find('button:first'));
                return openingProm;
            }

            await openColorpicker('.note-toolbar .note-back-color-preview');
            await testUtils.dom.click($field.find('.note-toolbar .note-back-color-preview .o_we_color_btn.bg-o-color-3'));

            await testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.module('cssReadonly');

        QUnit.test('rendering with iframe for readonly mode', async function (assert) {
            assert.expect(3);

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
            var $iframe = $field.find('iframe.o_readonly');
            await $iframe.data('loadDef');
            var doc = $iframe.contents()[0];
            assert.strictEqual($(doc).find('#iframe_target').html(),
                '<p>toto toto toto</p><p>tata</p>',
                "should have rendered a div with correct content in readonly");

            assert.strictEqual(doc.defaultView.getComputedStyle(doc.body).backgroundColor,
                'rgb(255, 0, 0)',
                "should load the asset css");

            await testUtils.form.clickEdit(form);

            $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.find('.note-editable').html(),
                '<p>toto toto toto</p><p>tata</p>',
                "should have rendered the field correctly in edit");

            form.destroy();
        });

        QUnit.module('translation');

        QUnit.test('field html translatable', async function (assert) {
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
