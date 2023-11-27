odoo.define('web_editor.field_html_tests', function (require) {
"use strict";

var ajax = require('web.ajax');
var FormController = require('web.FormController');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var weTestUtils = require('web_editor.test_utils');
var core = require('web.core');
var Wysiwyg = require('web_editor.wysiwyg');
const { MediaDialogWrapper } = require('@web_editor/components/media_dialog/media_dialog');
var LinkDialog = require('wysiwyg.widgets.LinkDialog');

const { legacyExtraNextTick, patchWithCleanup } = require("@web/../tests/helpers/utils");

const { useEffect } = require("@odoo/owl");

var _t = core._t;

let _formResolveTestPromise;
FormController.include({
    _setEditMode: async function () {
        await this._super.apply(this, arguments);
        if (_formResolveTestPromise) {
            _formResolveTestPromise();
        }
    }
});

QUnit.module('web_editor', {}, function () {

    QUnit.module('field html', {
        beforeEach: function () {
            this.linkDialogTestHtml = '<p><a href="https://www.external.com" target="_blank">External website</a></p>' +
                                      '<p><a href="' + window.location.href + '/test">This website</a></p>' +
                                      '<p>New external link</p><p>New internal link</p>';

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
                        header: "<p>Hello World</p>",
                        body: '<p><a href="https://www.external.com" target="_blank">External website</a></p>',
                    }, {
                        id: 3,
                        display_name: "third record",
                        header: "<p>Hello World</p>",
                        body: '<p><a href="' + window.location.href + '/test">This website</a></p>',
                    }, {
                        id: 4,
                        display_name: "fourth record",
                        header: "<p>Hello World</p>",
                        body: '<p>New external link</p>',
                    }, {
                        id: 5,
                        display_name: "fifth record",
                        header: "<p>Hello World</p>",
                        body: '<p>New internal link</p>',
                    }, {
                        id: 6,
                        display_name: "sixth record",
                        header: "<p>Hello World</p>",
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
                    }, {
                        id: 7,
                        display_name: "seventh record",
                        header: "<p>Hello World</p>",
                        body: `
<p class="a">
    a
</p>
<p class="b o_not_editable">
    b
</p>`,
                    }, {
                        id: 8,
                        display_name: "eighth record",
                        header: "<p>Hello World</p>",
                        body: `<p><br></p>`,
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

            const promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;
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
                res_id: 6,
            });
            // check that there is no error on clicking Edit
            const promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;
            assert.containsOnce(form, '.o_form_editable');

            form.destroy();
        });

        QUnit.test('check if required field is set', async function (assert) {
            assert.expect(3);

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
                    assert.strictEqual(ev.data.args[0].title, 'Invalid fields:');
                    assert.strictEqual(ev.data.args[0].message.toString(), '<ul><li>Header</li></ul>');
                    assert.strictEqual(ev.data.args[0].type, 'danger');
                }
            }, true);

            const promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;
            await testUtils.dom.click(form.$('.o_form_button_save'));

            form.destroy();
        });

        QUnit.test('colorpicker', async function (assert) {
            assert.expect(7);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 1,
            });

            await testUtils.form.clickEdit(form);
            await new Promise(resolve => setTimeout(resolve, 50));
            var $field = form.$('.oe_form_field[name="body"]');

            // select the text
            var pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 1, pText, 10);
            // text is selected

            var range = Wysiwyg.getRange();

            assert.strictEqual(range.sc, pText,
                "should select the text");

            async function openColorpicker(selector) {
                const $colorpicker = $(selector);
                const openingProm = new Promise(resolve => {
                    $colorpicker.one('shown.bs.dropdown', () => resolve());
                });
                await testUtils.dom.click($colorpicker.find('button:first'));
                return openingProm;
            }

            await openColorpicker('#toolbar .note-back-color-preview');
            assert.ok($('.note-back-color-preview .dropdown-menu').hasClass('show'),
                "should display the color picker");

            await testUtils.dom.click($('#toolbar .note-back-color-preview .o_we_color_btn[style="background-color:#00FFFF;"]'));

            assert.ok(!$field.find('.note-back-color-preview').hasClass('show'),
                "should close the color picker");

            assert.strictEqual($field.find('.note-editable').html(),
                '<p>t<font style="background-color: rgb(0, 255, 255);">oto toto </font>toto</p><p>tata</p>',
                "should have rendered the field correctly in edit");

            var fontElement = $field.find('.note-editable font')[0];
            var rangeControl = {
                sc: fontElement,
                so: 0,
                ec: fontElement,
                eo: 1,
            };
            range = Wysiwyg.getRange();
            assert.deepEqual(_.pick(range, 'sc', 'so', 'ec', 'eo'), rangeControl,
                "should select the text after color change");

            // select the text
            pText = $field.find('.note-editable p').first().contents()[2];
            Wysiwyg.setRange(fontElement.firstChild, 5, pText, 2);
            // text is selected

            await openColorpicker('#toolbar .note-back-color-preview');
            await testUtils.dom.click($('#toolbar .note-back-color-preview [style="background-color: var(--we-cp-o-color-3);"]'));

            assert.strictEqual($field.find('.note-editable').html(),
                '<p>t<font style="background-color: rgb(0, 255, 255);">oto t</font><font class="bg-o-color-3">oto to</font>to</p><p>tata</p>',
                "should have rendered the field correctly in edit");

            // Make sure the reset button works too
            await openColorpicker('#toolbar .note-back-color-preview');
            await testUtils.dom.click($('#toolbar .note-back-color-preview .o_colorpicker_reset'));

            // TODO right now the behavior is to force "inherit" as background
            // but it should remove the useless font element when possible.
            assert.strictEqual($field.find('.note-editable').html(),
                '<p>t<font style="background-color: rgb(0, 255, 255);">oto t</font>oto toto</p><p>tata</p>',
                "should have properly reset the background color");

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

            var pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 1, pText, 2);

            await new Promise((resolve) => setTimeout(resolve));

            const wysiwyg = $field.find('.note-editable').data('wysiwyg');

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

            var $editable = form.$('.oe_form_field[name="body"] .note-editable');
            assert.ok($editable.find('img')[0].dataset.src.includes('/web/image/123/transparent.png'),
                "should have the image in the dom");

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


            var pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 1, pText, 2);

            const wysiwyg = $field.find('.note-editable').data('wysiwyg');

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

            var $editable = form.$('.oe_form_field[name="body"] .note-editable');

            assert.strictEqual($editable.data('wysiwyg').getValue(),
                '<p>t<span class="fa fa-glass"></span>to toto toto</p><p>tata</p>',
                "should have the image in the dom");

            form.destroy();
        });

        QUnit.test('link dialog - external link - no edit', async function (assert) {
            assert.expect(2);

            const form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 2,
            });
            let $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(),
                '<p><a href="https://www.external.com" target="_blank" rel="noreferrer">External website</a></p>',
                "should have rendered a div with correct content in readonly");

            const promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;
            $field = form.$('.oe_form_field[name="body"]');
            // the dialog load some xml assets
            const defLinkDialog = testUtils.makeTestPromise();
            testUtils.mock.patch(LinkDialog, {
                init: function () {
                    this._super.apply(this, arguments);
                    this.opened(defLinkDialog.resolve.bind(defLinkDialog));
                }
            });

            let pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText.firstChild, 0, pText.firstChild, pText.firstChild.length);
            await testUtils.dom.triggerEvent($('#toolbar #create-link'), 'click');
            // load static xml file (dialog, link dialog)
            await defLinkDialog;
            $('.modal .tab-content .tab-pane').removeClass('fade'); // to be sync in test
            await testUtils.dom.click($('.modal .modal-footer button:contains(Save)'));

            await testUtils.form.clickSave(form);

            $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(),
                '<p><a href="https://www.external.com" target="_blank" rel="noreferrer">External website</a></p>',
                "the link shouldn't change");

            testUtils.mock.unpatch(LinkDialog);
            form.destroy();
        });

        QUnit.test('link dialog - internal link - no edit', async function (assert) {
            assert.expect(2);

            const form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 3,
            });
            let $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(),
                '<p><a href="' + window.location.href.replace(/&/g, "&amp;") + '/test">This website</a></p>',
                "should have rendered a div with correct content in readonly");

            const promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;
            $field = form.$('.oe_form_field[name="body"]');
            // the dialog load some xml assets
            const defLinkDialog = testUtils.makeTestPromise();
            testUtils.mock.patch(LinkDialog, {
                init: function () {
                    this._super.apply(this, arguments);
                    this.opened(defLinkDialog.resolve.bind(defLinkDialog));
                }
            });

            let pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText.firstChild, 0, pText.firstChild, pText.firstChild.length);
            await testUtils.dom.triggerEvent($('#toolbar #create-link'), 'click');
            // load static xml file (dialog, link dialog)
            await defLinkDialog;
            $('.modal .tab-content .tab-pane').removeClass('fade'); // to be sync in test
            await testUtils.dom.click($('.modal input#o_link_dialog_url_strip_domain'));
            await testUtils.dom.click($('.modal .modal-footer button:contains(Save)'));

            await testUtils.form.clickSave(form);

            $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(),
                '<p><a href="' + window.location.href.replace(/&/g, "&amp;") + '/test">This website</a></p>',
                "the link shouldn't change");

            testUtils.mock.unpatch(LinkDialog);
            form.destroy();
        });

        QUnit.test('link dialog - test preview', async function (assert) {
            assert.expect(4);

            const form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 3,
            });
            let $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(),
                '<p><a href="' + window.location.href.replace(/&/g, "&amp;") + '/test">This website</a></p>',
                "should have rendered a div with correct content in readonly");

            const promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;
            $field = form.$('.oe_form_field[name="body"]');
            // the dialog load some xml assets
            const defLinkDialog = testUtils.makeTestPromise();
            testUtils.mock.patch(LinkDialog, {
                init: function () {
                    this._super.apply(this, arguments);
                    this.opened(defLinkDialog.resolve.bind(defLinkDialog));
                }
            });

            let pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText.firstChild, 0, pText.firstChild, pText.firstChild.length);
            await testUtils.dom.triggerEvent($('#toolbar #create-link'), 'click');
            // load static xml file (dialog, link dialog)
            await defLinkDialog;
            $('.modal .tab-content .tab-pane').removeClass('fade'); // to be sync in test
            const $labelInputField = $('input#o_link_dialog_label_input');
            const $linkPreview = $('a#link-preview');
            assert.strictEqual($labelInputField.val().replace(/\u200B/g, ''), 'This website',
                "The label input field should match the link's content");
            assert.strictEqual($linkPreview.text().replace(/\u200B/g, ''), 'This website',
                "Link label in preview should match label input field");
            await testUtils.fields.editAndTrigger($labelInputField, "New label", ['input']);
            await testUtils.nextTick();
            assert.strictEqual($linkPreview.text(), "New label",
                "Preview should be updated on label input field change");
            await testUtils.dom.click($('.modal .modal-footer button:contains(Save)'));

            await testUtils.form.clickSave(form);

            testUtils.mock.unpatch(LinkDialog);
            form.destroy();
        });

        QUnit.test('link dialog - external link - new', async function (assert) {
            assert.expect(2);

            const form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 4,
            });
            let $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(), '<p>New external link</p>',
                "should have rendered a div with correct content in readonly");

            const promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;
            $field = form.$('.oe_form_field[name="body"]');
            // the dialog load some xml assets
            const defLinkDialog = testUtils.makeTestPromise();
            testUtils.mock.patch(LinkDialog, {
                init: function () {
                    this._super.apply(this, arguments);
                    this.opened(defLinkDialog.resolve.bind(defLinkDialog));
                }
            });

            let pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 0, pText, pText.length);
            await testUtils.dom.triggerEvent($('#toolbar #create-link'), 'click');
            // load static xml file (dialog, link dialog)
            await defLinkDialog;
            $('.modal .tab-content .tab-pane').removeClass('fade'); // to be sync in test
            $('input#o_link_dialog_url_input').val('www.test.com');
            await testUtils.dom.click($('.modal .modal-footer button:contains(Save)'));

            await testUtils.form.clickSave(form);

            $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(),
                '<p><a href="http://www.test.com" target="_blank" rel="noreferrer">New external link</a></p>',
                "the link should be created with the right format");

            testUtils.mock.unpatch(LinkDialog);
            form.destroy();
        });


        QUnit.test('link dialog - internal link - new', async function (assert) {
            assert.expect(3);

            const form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 5,
            });
            let $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(), '<p>New internal link</p>',
                "should have rendered a div with correct content in readonly");

            let promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;
            $field = form.$('.oe_form_field[name="body"]');
            // the dialog load some xml assets
            const defLinkDialog = testUtils.makeTestPromise();
            testUtils.mock.patch(LinkDialog, {
                init: function () {
                    this._super.apply(this, arguments);
                    this.opened(defLinkDialog.resolve.bind(defLinkDialog));
                }
            });

            let pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 0, pText, pText.length);
            await testUtils.dom.triggerEvent($('#toolbar #create-link'), 'click');
            // load static xml file (dialog, link dialog)
            await defLinkDialog;
            $('.modal .tab-content .tab-pane').removeClass('fade'); // to be sync in test
            const $input = $('input#o_link_dialog_url_input');
            await testUtils.fields.editAndTrigger($input, window.location.href + '/test', ["change"]);
            $('.modal input#o_link_dialog_url_strip_domain').click();
            await testUtils.dom.click($('.modal .modal-footer button:contains(Save)'));

            await testUtils.form.clickSave(form);

            $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(),
                '<p><a href="' + window.location.href.replace(/&/g, "&amp;") + '/test">New internal link</a></p>',
                "the link should be created with the right format");

            promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;

            $field = form.$('.oe_form_field[name="body"]');
            pText = $field.find('.note-editable a').eq(0).contents()[0];
            Wysiwyg.setRange(pText, 0, pText, pText.length);
            await testUtils.dom.triggerEvent($('#toolbar #create-link'), 'click');
            // load static xml file (dialog, link dialog)
            await defLinkDialog;
            $('.modal .tab-content .tab-pane').removeClass('fade'); // to be sync in test
            await testUtils.dom.click($('.modal .modal-footer button:contains(Save)'));
            await testUtils.form.clickSave(form);

            $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(),
                '<p><a href="' + window.location.href.slice(window.location.origin.length).replace(/&/g, "&amp;") + '/test">New internal link</a></p>',
                "the link should be created with the right format");

            testUtils.mock.unpatch(LinkDialog);
            form.destroy();
        });

        QUnit.test('save', async function (assert) {
            assert.expect(0);

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
            await testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('Quick Edition: click on link inside html field', async function (assert) {
            assert.expect(6);

            this.data['note.note'].records[0]['body'] = '<p><a href="#">hello</a> world</p>';

            const MULTI_CLICK_DELAY = 6498651354; // arbitrary large number to identify setTimeout calls
            let quickEditCB;
            let quickEditTimeoutId;
            let nextId = 1;
            const originalSetTimeout = window.setTimeout;
            const originalClearTimeout = window.clearTimeout;
            patchWithCleanup(window, {
                setTimeout(fn, delay) {
                    if (delay === MULTI_CLICK_DELAY) {
                        quickEditCB = fn;
                        quickEditTimeoutId = `quick_edit_${nextId++}`;
                        return quickEditTimeoutId;
                    } else {
                        return originalSetTimeout(...arguments);
                    }
                },
                clearTimeout(id) {
                    if (id === quickEditTimeoutId) {
                        quickEditCB = undefined;
                    } else {
                        return originalClearTimeout(...arguments);
                    }
                },
            });

            const form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                formMultiClickTime: MULTI_CLICK_DELAY,
                res_id: 1,
            });

            assert.containsOnce(form, '.o_legacy_form_view.o_form_readonly');

            await testUtils.dom.click(form.$('.oe_form_field[name="body"] a'));
            await testUtils.nextTick();
            assert.strictEqual(quickEditCB, undefined, "no quickEdit callback should have been set");
            assert.containsOnce(form, '.o_legacy_form_view.o_form_readonly');

            await testUtils.dom.click(form.$('.oe_form_field[name="body"] p'));
            await testUtils.nextTick();
            assert.containsOnce(form, '.o_legacy_form_view.o_form_readonly');
            assert.ok(quickEditCB, "quickEdit callback should have been set");
            quickEditCB();
            await testUtils.nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(form, '.o_legacy_form_view.o_form_editable');

            form.destroy();
        });

        QUnit.test('.o_not_editable should be contenteditable=false', async function (assert) {
            assert.expect(8);

            const form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    '</form>',
                res_id: 7,
            });

            const waitForMutation = (element) => {
                let currentResolve;
                const promise = new Promise((resolve)=>{
                    currentResolve = resolve;
                });
                const observer = new MutationObserver((records) => {
                    currentResolve();
                    observer.disconnect();
                });
                observer.observe(element, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                });
                return promise;
            }

            assert.equal(form.$('.b').attr('contenteditable'), undefined);

            let promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;
            assert.equal(form.$('.b').attr('contenteditable'), 'false');
            await testUtils.form.clickSave(form);
            assert.equal(form.$('.b').attr('contenteditable'), undefined);

            // edit a second time
            promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;
            await testUtils.nextTick();

            // adding an element with o_not_editable
            form.$('.b').after($(`<div class="c o_not_editable">c</div>`));
            await waitForMutation(form.$('.c')[0]);
            assert.equal(form.$('.c').attr('contenteditable'), 'false');

            // changing the class o_not_editable back and forth
            form.$('.a').addClass('o_not_editable');
            await waitForMutation(form.$('.a')[0]);
            assert.equal(form.$('.a').attr('contenteditable'), 'false');
            form.$('.a').removeClass('o_not_editable');
            await waitForMutation(form.$('.a')[0]);
            assert.equal(form.$('.a').attr('contenteditable'), undefined);

            // changing the class o_not_editable back and forth again
            form.$('.a').addClass('o_not_editable');
            await waitForMutation(form.$('.a')[0]);
            assert.equal(form.$('.a').attr('contenteditable'), 'false');
            form.$('.a').removeClass('o_not_editable');
            await waitForMutation(form.$('.a')[0]);
            assert.equal(form.$('.a').attr('contenteditable'), undefined);

            form.destroy();
        });

        QUnit.test('Paste video URL', async function (assert) {
            assert.expect(4);
            const form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" options="{\'allowCommandVideo\': true}" style="height: 100px"/>' +
                    '</form>',
                res_id: 8,
                mockRPC: function (route, args) {
                    if (route === '/web_editor/video_url/data') {
                        return Promise.resolve({
                            platform: "youtube",
                            embed_url: "//www.youtube.com/embed/qxb74CMR748?rel=0&autoplay=0",
                        });
                    }
                    return this._super.apply(this, arguments);
                },
            });

            let promise = new Promise((resolve) => _formResolveTestPromise = resolve);
            await testUtils.form.clickEdit(form);
            await promise;

            const editable = document.querySelector('.note-editable');
            const p = editable.querySelector('p');
            Wysiwyg.setRange(p, 0);

            // Paste a video URL.
            const clipboardData = new DataTransfer();
            clipboardData.setData('text/plain', 'https://www.youtube.com/watch?v=qxb74CMR748');
            p.dispatchEvent(new ClipboardEvent('paste', { clipboardData, bubbles: true }));
            assert.strictEqual(p.outerHTML, '<p>https://www.youtube.com/watch?v=qxb74CMR748<br></p>',
                "The URL should be inserted as text");
            assert.isVisible($('.oe-powerbox-wrapper:contains("Embed Youtube Video")'),
                "The powerbox should be opened");

            // Press Enter to select first option in the powerbox ("Embed Youtube Video").
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
            await testUtils.nextTick();
            assert.strictEqual(p.outerHTML, '<p></p>', "URL insertion should be reverted");
            assert.containsOnce(
                editable,
                'div.media_iframe_video iframe[data-src="//www.youtube.com/embed/qxb74CMR748?rel=0&autoplay=0"]',
                "The video should be embedded as an iframe"
            );

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
                debug: 1,
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
            assert.strictEqual($field.find('#iframe_target').length, 0);

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
                    if (route === "/web/dataset/call_kw/note.note/get_field_translations") {
                        assert.deepEqual(args.args, [[1],"body"], "should translate the body field of the record");
                        return Promise.resolve([
                            [{lang: "en_US", source: "first paragraph", value: "first paragraph"},
                                {lang: "en_US", source: "second paragraph", value: "second paragraph"},
                                {lang: "fr_BE", source: "first paragraph", value: "premier paragraphe"},
                                {lang: "fr_BE", source: "second paragraph", value: "deuxième paragraphe"}],
                            {translation_type: "text", translation_show_source: true},
                        ]);
                    }
                    if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                        return Promise.resolve([["en_US", "English"], ["fr_BE", "French (Belgium)"]]);
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
