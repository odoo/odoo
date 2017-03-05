odoo.define('web_editor.web_editor_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

QUnit.module('web_editor', {
    beforeEach: function() {
        this.data = {
            'mass.mailing': {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    body: {string: "Message Body", type: "html"},
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    body: "<div>yep</div>"
                }],
                onchanges: {},
            },
        };
    }
});

QUnit.test('field html widget', function(assert) {
    assert.expect(2);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<field name="body" widget="html_frame"/>' +
            '</form>',
        res_id: 1,
        session: {user_context: {lang: "en_us"}},
        manualDestroy: true,
    });

    assert.strictEqual(form.$('iframe').length, 1, "should have rendered an iframe without crashing");

    form.$buttons.find('.o_form_button_edit').click();

    assert.strictEqual(form.$('iframe').length, 1, "should have rendered an iframe without crashing");

    form.destroy();
});

});
