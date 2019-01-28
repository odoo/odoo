odoo.define('mass_mailing.field_html_tests', function (require) {
"use strict";

var ajax = require('web.ajax');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var weTestUtils = require('web_editor.test_utils');
var Wysiwyg = require('web_editor.wysiwyg');


QUnit.module('mass_mailing', {}, function () {
QUnit.module('field html', {
    beforeEach: function () {
        this.data = weTestUtils.wysiwygData({
            'mail.mass_mailing': {
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
                    return $.when({
                        cssLibs: [],
                        cssContents: ['.field_body {background-color: red;}']
                    });
                }
                if (xmlId === 'template.assets_all_style') {
                    return $.when({
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

QUnit.test('save arch and html', function (assert) {
    var done = assert.async();
    assert.expect(6);

    testUtils.createAsyncView({
        View: FormView,
        model: 'mail.mass_mailing',
        data: this.data,
        arch: '<form>' +
            '   <field name="body_html" class="oe_read_only" widget="html"'+
            '       options="{'+
            '                \'cssReadonly\': \'template.assets\','+
            '       }"'+
            '   />'+
            '   <field name="body_arch" class="oe_edit_only" widget="mass_mailing_html"'+
            '       options="{'+
            '                \'snippets\': \'template.assets\','+
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
    }).then(function (form) {
        var $fieldReadonly = form.$('.oe_form_field[name="body_html"]');
        var $fieldEdit = form.$('.oe_form_field[name="body_arch"]');

        assert.strictEqual($fieldReadonly.css('display'), 'block', "should display the readonly mode");
        assert.strictEqual($fieldEdit.css('display'), 'none', "should hide the edit mode");

        form.$buttons.find('.o_form_button_edit').click();

        $fieldReadonly = form.$('.oe_form_field[name="body_html"]');
        $fieldEdit = form.$('.oe_form_field[name="body_arch"]');

        assert.strictEqual($fieldReadonly.css('display'), 'none', "should hide the readonly mode");
        assert.strictEqual($fieldEdit.css('display'), 'block', "should display the edit mode");

        var $iframe = $fieldEdit.find('iframe');

        $iframe.data('load-def').then(function () {
            var doc = $iframe.contents()[0];
            var $content = $('#iframe_target', doc);

            // select the text
            var pText = $content.find('.note-editable p').first().contents()[0];
            Wysiwyg.setRange(pText, 1, pText, 3);
            // text is selected

            $content.find('.note-toolbar .note-font .note-btn-bold').mousedown().click();

            form.$buttons.find('.o_form_button_save').click();

            form.destroy();
            done();
        });
    });
});

});
});
});
