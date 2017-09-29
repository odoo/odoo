odoo.define('im_livechat.copy_clipboard_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('copy_clipboard', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    script_external: {string: "Script External", type: "text"},
                    web_page: {string: "Web page link", type: "char"}
                },
                records: [{
                    id: 1,
                    script_external:'Random Text',
                    web_page: 'web page links'
                },],
            },
        };
    }
});

QUnit.test('im_livechat: Copy to clipboard button', function (assert) {
    assert.expect(2);

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                        '<div>' +
                            '<field name="script_external" widget="CopyClipboardText"/>' +
                            '<field name="web_page" widget="CopyClipboardChar"/>' +
                        '</div>' +
                '</sheet>' +
            '</form>',
    });
    assert.strictEqual(form.$('.o_clipboard_button.o_btn_text_copy').length, 1,"Should have copy button on text type field");
    assert.strictEqual(form.$('.o_clipboard_button.o_btn_char_copy').length, 1,"Should have copy button on char type field");
    form.destroy();
});

});
