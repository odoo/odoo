odoo.define('mass_mailing.field_html_tests', function (require) {
"use strict";

var ajax = require('web.ajax');
var FormView = require('web.FormView');
var FieldHtml = require('web_editor.field.html');
var MassMailingFieldHtml = require('mass_mailing.FieldHtml');
var testUtils = require('web.test_utils');
var weTestUtils = require('web_editor.test_utils');
var Wysiwyg = require('web_editor.wysiwyg');


QUnit.module('mass_mailing', {}, function () {
QUnit.module('field html', {
    beforeEach: function () {
        this.data = weTestUtils.wysiwygData({
            'mailing.mailing': {
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
                    body_html: "<div class='field_body' style='background-color: red;'><p>code to edit</p></div>",
                    body_arch: "<div class='field_body'><p>code to edit</p></div>",
                }],
            },
        });

        testUtils.mock.patch(ajax, {
            loadAsset: function (xmlId) {
                if (xmlId === 'template.assets') {
                    return Promise.resolve({
                        cssLibs: [],
                        cssContents: ['.field_body {background-color: red;}']
                    });
                }
                if (xmlId === 'template.assets_all_style') {
                    return Promise.resolve({
                        cssLibs: $('link[href]:not([type="image/x-icon"])').map(function () {
                            return $(this).attr('href');
                        }).get(),
                        cssContents: ['.field_body {background-color: red;}']
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

QUnit.test('save arch and html', async function (assert) {
    assert.expect(6);

    var form = await testUtils.createView({
        View: FormView,
        model: 'mailing.mailing',
        data: this.data,
        arch: '<form>' +
            '   <field name="body_html" class="oe_read_only" widget="html"'+
            '       options="{'+
            '                \'cssReadonly\': \'template.assets\','+
            '       }"'+
            '   />'+
            '   <field name="body_arch" class="oe_edit_only" widget="mass_mailing_html"'+
            '       options="{'+
            '                \'snippets\': \'web_editor.snippets\','+
            '                \'cssEdit\': \'template.assets\','+
            '                \'inline-field\': \'body_html\''+
            '       }"'+
            '   />'+
            '</form>',
        res_id: 1,
        mockRPC: function (route, args) {
            if (args.method === "write") {
                var values = args.args[1];
                assert.strictEqual(values.body_html,
                    '<div class="field_body" style="background-color:red;"><p>c<b>od</b>e to edit</p></div>',
                    "should save the content");
                assert.strictEqual(values.body_arch,
                    '<div class="field_body"><p>c<b>od</b>e to edit</p></div>',
                    "should save the content");

            }
            return this._super.apply(this, arguments);
        },
    });
    var $fieldReadonly = form.$('.oe_form_field[name="body_html"]');
    var $fieldEdit = form.$('.oe_form_field[name="body_arch"]');

    assert.strictEqual($fieldReadonly.css('display'), 'block', "should display the readonly mode");
    assert.strictEqual($fieldEdit.css('display'), 'none', "should hide the edit mode");

    await testUtils.form.clickEdit(form);

    $fieldReadonly = form.$('.oe_form_field[name="body_html"]');
    $fieldEdit = form.$('.oe_form_field[name="body_arch"]');

    assert.strictEqual($fieldReadonly.css('display'), 'none', "should hide the readonly mode");
    assert.strictEqual($fieldEdit.css('display'), 'block', "should display the edit mode");

    var $iframe = $fieldEdit.find('iframe');
    await testUtils.nextTick();
    await $iframe.data('loadDef');
    await testUtils.nextTick();
    var doc = $iframe.contents()[0];
    var $content = $('#iframe_target', doc);

    // select the text
    var pText = $content.find('.note-editable p').first().contents()[0];
    Wysiwyg.setRange(pText, 1, pText, 3);
    // text is selected
    await testUtils.nextTick();

    await testUtils.dom.triggerEvents($content.find('.note-toolbar .note-font .note-btn-bold'),['mousedown','click']);

    await testUtils.dom.click(form.$buttons.find('.o_form_button_save'));

    form.destroy();
});

QUnit.test('save and edit arch wysiwyg', async function (assert) {
    assert.expect(4);

    testUtils.mock.patch(FieldHtml, {
        commitChanges: function () {
            assert.step("FieldHtml");
            return this._super.apply(this, arguments);
        },
    });

    testUtils.mock.patch(MassMailingFieldHtml, {
        commitChanges: function () {
            assert.step("MassMailingFieldHtml");
            return this._super.apply(this, arguments);
        },
    });

    var form = await testUtils.createView({
        View: FormView,
        model: 'mailing.mailing',
        data: this.data,
        arch: '<form>' +
            '   <header style="min-height:31px;">' +
            '       <button name="put_in_queue" type="object" class="oe_highlight" string="Send Now"/>' +
            '   </header>' +
            '   <field name="body_arch" class="oe_edit_only" widget="mass_mailing_html"' +
            '       options="{' +
            '                \'snippets\': \'template.assets\',' +
            '                \'cssEdit\': \'template.assets\',' +
            '                \'inline-field\': \'body_html\'' +
            '       }"' +
            '   />' +
            '</form>',
        res_id: 1,
        intercepts: {
            execute_action: function (event) {
                event.data.on_success();
            },
        },
    });

    await testUtils.dom.click($('[name=put_in_queue]'));
    await testUtils.form.clickEdit(form);
    var $fieldEdit = form.$('.oe_form_field[name="body_arch"]');
    var $iframe = $fieldEdit.find('iframe');

    await $iframe.data('loadDef');
    await testUtils.nextTick();
    await testUtils.dom.click($('[name=put_in_queue]'));
    assert.verifySteps(["MassMailingFieldHtml", "FieldHtml", "MassMailingFieldHtml"]);

    testUtils.mock.unpatch(FieldHtml);
    testUtils.mock.unpatch(MassMailingFieldHtml);
    form.destroy();
});

});
});
});
