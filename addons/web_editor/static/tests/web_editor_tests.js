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

QUnit.test('field html widget', function (assert) {
    assert.expect(6);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<field name="body" widget="html_frame" options="{\'editor_url\': \'/test\'}"/>' +
            '</form>',
        res_id: 1,
        session: {user_context: {lang: "en_us"}},
        mockRPC: function (route) {
            if (_.str.startsWith(route, '/test')) {
                // those tests will be executed twice, once in readonly and once in edit
                assert.ok(route.search('model=mass.mailing') > 0,
                    "the route should specify the correct model");
                assert.ok(route.search('res_id=1') > 0,
                    "the route should specify the correct id");
                return $.when();
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.strictEqual(form.$('iframe').length, 1, "should have rendered an iframe without crashing");

    form.$buttons.find('.o_form_button_edit').click();

    assert.strictEqual(form.$('iframe').length, 1, "should have rendered an iframe without crashing");

    form.destroy();
});

});
