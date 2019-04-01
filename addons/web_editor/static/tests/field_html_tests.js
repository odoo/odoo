odoo.define('web_editor.field_html_tests', function (require) {
"use strict";

var ajax = require('web.ajax');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var weTestUtils = require('web_editor.test_utils');
var core = require('web.core');
var Wysiwyg = require('web_editor.wysiwyg');
var MediaDialog = require('wysiwyg.widgets.MediaDialog');

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
                        body: {
                            string: "Message",
                            type: "html"
                        },
                    },
                    records: [{
                        id: 1,
                        display_name: "first record",
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
            await testUtils.form.clickEdit(form);
            var $field = form.$('.oe_form_field[name="body"]');

            // select the text
            var pText = $field.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 1, pText, 10);
            // text is selected

            var range = Wysiwyg.getRange($field[0]);
            assert.strictEqual(range.sc, pText,
                "should select the text");

            $field.find('.note-toolbar .note-bg-color button:first').mousedown().click();

            assert.ok($field.find('.note-bg-color').hasClass('show') && $field.find('.note-bg-color .dropdown-menu').hasClass('show'),
                "should display the color picker");

            $field.find('.note-toolbar .note-bg-color button[data-value="#00FFFF"]').mousedown().click();

            assert.ok(!$field.find('.note-bg-color').hasClass('show') && !$field.find('.note-bg-color .dropdown-menu').hasClass('show'),
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

            $field.find('.note-toolbar .note-bg-color button:first').mousedown().click();
            $field.find('.note-toolbar .note-bg-color button[data-value="bg-gamma"]').mousedown().click();

            assert.strictEqual($field.find('.note-editable').html(),
                '<p>t<font style="background-color: rgb(0, 255, 255);">oto t</font><font class="bg-gamma">oto&nbsp;to</font>to</p><p>tata</p>',
                "should have rendered the field correctly in edit");

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
                        if (args.kwargs.domain[7][2].join(',') === "image/gif,image/jpe,image/jpeg,image/jpg,image/gif,image/png") {
                            return Promise.resolve([{
                                "id": 1,
                                "public": true,
                                "name": "image",
                                "datas_fname": "image.png",
                                "mimetype": "image/png",
                                "checksum": false,
                                "url": "/web_editor/static/src/img/transparent.png",
                                "type": "url",
                                "res_id": 0,
                                "res_model": false,
                                "access_token": false
                            }]);
                        }
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

            $field.find('.note-toolbar .note-insert button:has(.fa-file-image-o)').mousedown().click();

            // load static xml file (dialog, media dialog, unsplash image widget)
            await defMediaDialog;
            await testUtils.dom.click($('.modal #editor-media-image .o_image:first'));
            await testUtils.dom.click($('.modal .modal-footer button.btn-primary'));

            var $editable = form.$('.oe_form_field[name="body"] .note-editable');

            assert.strictEqual($editable.data('wysiwyg').getValue(),
                '<p>t<img class="img-fluid o_we_custom_image" data-src="/web_editor/static/src/img/transparent.png">oto toto toto</p><p>tata</p>',
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

            $field.find('.note-toolbar .note-insert button:has(.fa-file-image-o)').mousedown().click();

            // load static xml file (dialog, media dialog, unsplash image widget)
            await defMediaDialog;
            $('.modal .tab-content .tab-pane').removeClass('fade'); // to be sync in test
            await testUtils.dom.click($('.modal a[aria-controls="editor-media-icon"]'));
            await testUtils.dom.click($('.modal #editor-media-icon .font-icons-icon.fa-glass'));
            await testUtils.dom.click($('.modal .modal-footer button.btn-primary'));

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
                            '<p>t<font class="bg-gamma">oto toto&nbsp;</font>toto</p><p>tata</p>',
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

            await testUtils.dom.click($field.find('.note-toolbar .note-bg-color button:first').mousedown());
            await testUtils.dom.click($field.find('.note-toolbar .note-bg-color button[data-value="bg-gamma"]').mousedown());

            await testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.module('inline-style');

        QUnit.test('convert style to class on edit', async function (assert) {
            assert.expect(5);

            this.data['note.note'].records[0].body = '<p class="pull-right" style="float: right;">toto ' +
                '<img data-class="fa fa-star" data-style="color: red;" src="/web_editor/font_to_img/61445/rgb(255,0,0)/13" style="border-style:none;vertical-align:middle;height: auto; width: auto;">' +
                'toto toto</p><p>tata</p>';

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px" options="{\'style-inline\': true}"/>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.strictEqual(args.args[1].body,
                            '<p class="pull-right" style="margin:0px;font-size:13px;font-family:&quot;Lucida Grande&quot;, Helvetica, Verdana, Arial, sans-serif;float:right;">' +
                            'toto ' +
                            '<img ' +
                            'data-class="fa fa-star" ' +
                            'data-style="color: red;" ' +
                            'style="border-style:none;vertical-align:middle;color: red; height: auto; width: auto;" ' +
                            'data-src="/web_editor/font_to_img/61445/rgb(255,0,0)/13"' +
                            '>' +
                            'toto toto' +
                            '</p>' +
                            '<p style="margin:0px;font-size:13px;font-family:&quot;Lucida Grande&quot;, Helvetica, Verdana, Arial, sans-serif;">' +
                            'tata' +
                            '</p>',
                            "should save the content");
                    }
                    if (route.indexOf("/web_editor/font_to_img/61445/rgb(") !== -1) {
                        assert.strictEqual(route,
                            '/web_editor/font_to_img/61445/rgb(255,0,0)/13',
                            "should use the image in function of the font and the color");
                        return Promise.resolve('#');
                    }
                    return this._super.apply(this, arguments);
                },
            });
            var $field = form.$('.oe_form_field[name="body"]');

            assert.strictEqual($field.children('.o_readonly').html(),
                '<p class="pull-right" style="float: right;">' +
                'toto ' +
                '<img data-class="fa fa-star" data-style="color: red;" ' +
                'style="border-style:none;vertical-align:middle;height: auto; width: auto;" ' +
                'data-src="/web_editor/font_to_img/61445/rgb(255,0,0)/13">' +
                'toto toto' +
                '</p>' +
                '<p>tata</p>',
                "should have rendered a div with correct content in readonly");

            await testUtils.form.clickEdit(form);

            $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.find('.note-editable').html(),
                '<p class="pull-right">' +
                'toto ' +
                '<span class="fa fa-star o_fake_not_editable" style="color: red;" contenteditable="false"></span>' +
                'toto toto' +
                '</p>' +
                '<p>tata</p>',
                "should have rendered the field correctly in edit (remove inline style that used class)");

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

        QUnit.module('cssEdit');

        QUnit.test('rendering with iframe for edit mode', async function (assert) {
            assert.expect(4);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px" options="{\'cssEdit\': \'template.assets\'}"/>' +
                    '</form>',
                res_id: 1,
            });
            var $field = form.$('.oe_form_field[name="body"]');
            assert.strictEqual($field.children('.o_readonly').html(),
                '<p>toto toto toto</p><p>tata</p>',
                "should have rendered a div with correct content in readonly");

            await testUtils.form.clickEdit(form);

            $field = form.$('.oe_form_field[name="body"]');
            var $iframe = $field.find('iframe');
            await $iframe.data('loadDef');
            var doc = $iframe.contents()[0];
            var $content = $('#iframe_target', doc);

            await testUtils.nextTick();

            assert.strictEqual($content.find('.note-editable').html(),
                '<p>toto toto toto</p><p>tata</p>',
                "should have rendered a div with correct content in edit mode");

            assert.strictEqual(doc.defaultView.getComputedStyle(doc.body).backgroundColor,
                'rgb(255, 0, 0)',
                "should load the asset css");

            $content.find('.note-toolbar .note-bg-color button:first').mousedown().click();
            await testUtils.nextTick();

            assert.ok($content.find('.note-bg-color').hasClass('show') && $content.find('.note-bg-color .dropdown-menu').hasClass('show'),
                "should display toolbar dropdown menu in iframe");

            form.destroy();
        });

QUnit.test('save immediately before iframe is rendered in edit mode', async function (assert) {
    assert.expect(1);

    var form = await testUtils.createAsyncView({
        View: FormView,
        model: 'note.note',
        data: this.data,
        arch: '<form>' +
            '<field name="body" widget="html" style="height: 100px" options="{\'cssEdit\': \'template.assets\'}"/>' +
            '</form>',
        res_id: 1,
    });
    testUtils.form.clickEdit(form);
    await testUtils.nextTick();
    testUtils.form.clickSave(form);
    await testUtils.nextTick();
    assert.ok(true, "No traceback encountered. The wysiwyg was cut while not loaded.");
    form.destroy();
});

        QUnit.test('save immediately before iframe is rendered in edit mode with style-inline', async function (assert) {
            assert.expect(1);

            var form = await testUtils.createAsyncView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px" options="{\'cssEdit\': \'template.assets\', \'style-inline\': true}"/>' +
                    '</form>',
                res_id: 1,
            });
            testUtils.form.clickEdit(form);
            await testUtils.nextTick();
            testUtils.form.clickSave(form);
            await testUtils.nextTick();
            assert.ok(true, "No traceback encountered. The wysiwyg was cut while not loaded.");
            form.destroy();
        });

        QUnit.test('use colorpicker and save', async function (assert) {
            assert.expect(1);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px" options="{\'cssEdit\': \'template.assets\'}"/>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.strictEqual(args.args[1].body,
                            '<p>t<font class="bg-gamma">oto toto&nbsp;</font>toto</p><p>tata</p>',
                            "should save the content");
                    }
                    return this._super.apply(this, arguments);
                },
            });
            await testUtils.form.clickEdit(form);
            var $field = form.$('.oe_form_field[name="body"]');
            var $iframe = $field.find('iframe');

            await $iframe.data('loadDef');
            await testUtils.nextTick();

            var doc = $iframe.contents()[0];
            var $content = $('#iframe_target', doc);
            var $editable = $content.find('.note-editable');

            // select the text
            var pText = $editable.find('p').first().contents()[0];
            Wysiwyg.setRange(pText, 1, pText, 10);
            // text is selected

            await testUtils.dom.click($content.find('.note-toolbar .note-bg-color button:first').mousedown());
            await testUtils.dom.click($content.find('.note-toolbar .note-bg-color button[data-value="bg-gamma"]').mousedown());

            await testUtils.form.clickSave(form);
            form.destroy();
        });

        QUnit.module('wrapper');

        // todo add test wrapper

        QUnit.module('snippet (without iframe)');

        QUnit.test('rendering with snippet panel', async function (assert) {
            var done = assert.async();
            assert.expect(1);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px" options="{\'snippets\': \'web_editor.snippets\'}"/>' +
                    '</form>',
                res_id: 1,
            });
            testUtils.mock.intercept(form, "snippets_loaded", function () {
                assert.strictEqual(form.$('.oe_form_field #oe_snippets').length, 1,
                    "should display the snippet panel");
                form.destroy();
                done();
            });
            await testUtils.form.clickEdit(form);
        });

        QUnit.test('drag&drop snippet', async function (assert) {
            assert.expect(1);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px" options="{\'snippets\': \'web_editor.snippets\'}"/>' +
                    '</form>',
                res_id: 1,
            });
            var defSnippets = testUtils.makeTestPromise();
            testUtils.mock.intercept(form, "snippets_loaded", function () {
                defSnippets.resolve();
            });

            await testUtils.form.clickEdit(form);
            var $field = form.$('.oe_form_field[name="body"]');
            var $editable = $field.find('.note-editable');

            await defSnippets;
            var $hr = $field.find('.oe_snippet_thumbnail:first');
            testUtils.dom.dragAndDrop($hr, $editable.find('p'));

            assert.strictEqual($editable.data('wysiwyg').getValue().replace(/\s+/g, ' '),
                '<div class=\"s_hr pt32 pb32\"> <hr class=\"s_hr_1px s_hr_solid w-100 mx-auto\"> </div><p>toto toto toto</p><p>tata</p>',
                "should drop the snippet");

            form.destroy();
        });

        // todo add test snippet + customize snippet

        QUnit.module('snippet & cssEdit');

        QUnit.test('rendering with snippet panel', async function (assert) {
            var done = assert.async();
            assert.expect(1);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px" options="{\'snippets\': \'web_editor.snippets\', \'cssEdit\': \'template.assets\'}"/>' +
                    '</form>',
                res_id: 1,
            });
            testUtils.mock.intercept(form, "snippets_loaded", function () {
                var doc = form.$('iframe').contents()[0];
                var $content = $('#iframe_target', doc);
                assert.strictEqual($content.find('#oe_snippets').length, 1,
                    "should display the snippet panel");
                form.destroy();
                done();
            });
            await testUtils.form.clickEdit(form);
        });

        QUnit.test('drag&drop snippet', async function (assert) {
            assert.expect(1);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px" options="{\'snippets\': \'web_editor.snippets\', \'cssEdit\': \'template.assets_all_style\'}"/>' +
                    '</form>',
                res_id: 1,
            });
            var defSnippets = testUtils.makeTestPromise();
            testUtils.mock.intercept(form, "snippets_loaded", function () {
                defSnippets.resolve();
            });
            await testUtils.form.clickEdit(form);

            await defSnippets;
            var doc = form.$('iframe').contents()[0];
            var $content = $('#iframe_target', doc);
            var $editable = $content.find('.note-editable');

            var $hr = $content.find('.oe_snippet_thumbnail:first');
            var from = $hr.offset();
            var to = $editable.find('p').offset();

            $hr.trigger($.Event("mousedown", {
                which: 1,
                pageX: from.left + 1,
                pageY: from.top + 1
            }));
            $hr.trigger($.Event("mousemove", {
                which: 1,
                pageX: to.left,
                pageY: to.top
            }));
            $hr.trigger($.Event("mouseup", {
                which: 1,
                pageX: to.left,
                pageY: to.top
            }));

            assert.strictEqual($editable.data('wysiwyg').getValue().replace(/\s+/g, ' '),
                '<div class=\"s_hr pt32 pb32\"> <hr class=\"s_hr_1px s_hr_solid w-100 mx-auto\"> </div><p>toto toto toto</p><p>tata</p>',
                "should drop the snippet");

            form.destroy();
        });

        QUnit.test('drag&drop snippet options', async function (assert) {
            var done = assert.async();
            assert.expect(6);

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px" options="{\'snippets\': \'web_editor.snippets\', \'cssEdit\': \'template.assets_all_style\'}"/>' +
                    '</form>',
                res_id: 1,
            });
            var defSnippets = testUtils.makeTestPromise();
            testUtils.mock.intercept(form, "snippets_loaded", function () {
                defSnippets.resolve();
            });

            var defActivateSnippet;
            testUtils.mock.intercept(form, "snippet_focused", function (e) {
                defActivateSnippet.resolve(e.target);
            });

            await testUtils.form.clickEdit(form);

            defSnippets.then(function () {
                var doc = form.$('iframe').contents()[0];
                var $content = $('#iframe_target', doc);
                var $editable = $content.find('.note-editable');

                function dropSnippet() {
                    defActivateSnippet = testUtils.makeTestPromise();

                    var $hr = $content.find('.oe_snippet_thumbnail:first');
                    var from = $hr.offset();
                    var to = $editable.find('p').offset();

                    $hr.trigger($.Event("mousedown", {
                        which: 1,
                        pageX: from.left + 1,
                        pageY: from.top + 1
                    }));
                    $hr.trigger($.Event("mousemove", {
                        which: 1,
                        pageX: to.left,
                        pageY: to.top
                    }));
                    $hr.trigger($.Event("mouseup", {
                        which: 1,
                        pageX: to.left,
                        pageY: to.top
                    }));
                }

                dropSnippet();
                defActivateSnippet.then(function (snippet) {
                    assert.strictEqual($editable.data('wysiwyg').getValue().replace(/\s+/g, ' '),
                        '<div class=\"s_hr pt32 pb32 built focus\"> <hr class=\"s_hr_1px s_hr_solid w-100 mx-auto\"> </div><p>toto toto toto</p><p>tata</p>',
                        "should drop the snippet");

                    assert.strictEqual(snippet.$target.index(), 0,
                        'should show the snippet editor for the first dropped block');

                    dropSnippet();
                    defActivateSnippet.then(function (snippet) {
                        assert.strictEqual($editable.data('wysiwyg').getValue().replace(/\s+/g, ' '),
                            '<div class=\"s_hr pt32 pb32 built\"> <hr class=\"s_hr_1px s_hr_solid w-100 mx-auto\"> ' +
                            '</div><div class=\"s_hr pt32 pb32 built focus\"> <hr class=\"s_hr_1px s_hr_solid w-100 mx-auto\"> ' +
                            '</div><p>toto toto toto</p><p>tata</p>',
                            "should drop the snippet");

                        assert.strictEqual(snippet.$target.index(), 1,
                            'should show the snippet editor for the second dropped block');

                        assert.strictEqual($('.oe_active .oe_overlay_options .btn:visible', doc).length, 4,
                            'should show the snippet editor buttons');

                        defActivateSnippet = testUtils.makeTestPromise();
                        $editable.find('hr:first').trigger('click');
                        defActivateSnippet.then(function (snippet) {

                            assert.strictEqual(snippet.$target.index(), 0,
                                'should show the snippet editor for the first dropped block');

                            form.destroy();
                            done();
                        });
                    });
                });
            });
        });

        QUnit.module('translation');

        QUnit.test('field html translatable', async function (assert) {
            assert.expect(3);

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
                        return Promise.resolve();
                    }
                    return this._super.apply(this, arguments);
                },
            });
            assert.strictEqual(form.$('.oe_form_field_html .o_field_translate').length, 0,
                "should not have a translate button in readonly mode");

            await testUtils.form.clickEdit(form);
            var $button = form.$('.oe_form_field_html .note-toolbar .o_field_translate');
            assert.strictEqual($button.length, 1, "should have a translate button");
            $button.click();

            form.destroy();
            _t.database.multi_lang = multiLang;
        });

        QUnit.test('field html translatable in iframe', async function (assert) {
            assert.expect(2);

            var multiLang = _t.database.multi_lang;
            _t.database.multi_lang = true;

            this.data['note.note'].fields.body.translate = true;

            var form = await testUtils.createView({
                View: FormView,
                model: 'note.note',
                data: this.data,
                arch: '<form>' +
                    '<field name="body" widget="html" style="height: 100px" options="{\'cssEdit\': \'template.assets\'}"/>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_button' && args.method === 'translate_fields') {
                        assert.deepEqual(args.args, ['note.note', 1, 'body'], "should call 'call_button' route");
                        return Promise.resolve();
                    }
                    return this._super.apply(this, arguments);
                },
            });
            var $field = form.$('.oe_form_field[name="body"]');
            await testUtils.form.clickEdit(form);
            $field = form.$('.oe_form_field[name="body"]');
            var $iframe = $field.find('iframe');

            await $iframe.data('loadDef');
            await testUtils.nextTick();
            var doc = $iframe.contents()[0];
            var $content = $('#iframe_target', doc);

            var $button = $content.find('.note-toolbar .o_field_translate');
            assert.strictEqual($button.length, 1, "should have a translate button");
            await testUtils.dom.click($button);

            form.destroy();
            _t.database.multi_lang = multiLang;
        });
    });
});
});
