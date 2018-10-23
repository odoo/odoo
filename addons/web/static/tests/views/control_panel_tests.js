odoo.define('web.control_panel_tests', function (require) {
"use strict";

var ControlPanelView = require('web.ControlPanelView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: 'char' },
                    foo: { string: "Foo", type: 'char', default: "My little Foo Value" },
                },
                records: [],
                onchanges: {},
            },
        };
    }
}, function () {
    QUnit.module('ControlPanelView');

    QUnit.test('basic rendering of controls', function (assert) {
        assert.expect(4);

        var controlPanel = createView({
            View: ControlPanelView,
            model: 'partner',
            data: this.data,
            arch: '<controlpanel>' +
                    '<controls>' +
                        '<button name="some_action_ref" type="action" string="Do it" class="b"/>' +
                    '</controls>' +
                '</controlpanel>',
            intercepts: {
                execute_action: function (ev) {
                    assert.deepEqual(ev.data, {
                        action_data: {
                            class: 'b',
                            name: 'some_action_ref',
                            string: 'Do it',
                            type: 'action',
                        },
                        env: {
                            context: {},
                            model: 'partner',
                        },
                    }, "should trigger execute_action with correct params");
                },
            },
        });

        assert.strictEqual(controlPanel.$('.o_cp_custom_buttons').length, 1,
            "should have rendered a custom button area");
        assert.strictEqual(controlPanel.$('.o_cp_custom_buttons button').length, 1,
            "should have rendered one custom button");
        assert.strictEqual(controlPanel.$('.o_cp_custom_buttons button.b').text(), 'Do it',
            "should have correctly rendered the custom button");

        controlPanel.$('.o_cp_custom_buttons button').click();

        controlPanel.destroy();
    });
});

});
