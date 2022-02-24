odoo.define('mass_mailing.field_html_tests', function (require) {
"use strict";

var ajax = require('web.ajax');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var weTestUtils = require('web_editor.test_utils');

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
    assert.expect(4);

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
            if (route.indexOf('/web/dataset/call_kw/mailing.mailing/action_fetch_favorites') >= 0) {
                return Promise.resolve([]);
            }
            return this._super(...arguments);
        }
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

    form.destroy();
});

});
});
});
