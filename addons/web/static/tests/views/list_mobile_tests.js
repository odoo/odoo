odoo.define('web.list_tests', function (require) {
"use strict";

const ListView = require('web.ListView');
const testUtils = require('web.test_utils');

const createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: { string: "Foo", type: "char" },
                },
                records: [
                    {
                        id: 1,
                        foo: "yop",
                    },
                ]
            },
        };
    }
}, function () {

    QUnit.module('ListViewMobile');

    QUnit.test('server action with display_in_control_panel should not be shown as button in list view in mobile', async function (assert) {
        assert.expect(1);

        const list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: { hasActionMenus: true },
            arch: '<tree><field name="foo"/></tree>',
            toolbar: {
                action: [{
                    model_name: 'foo',
                    name: 'Server Action 1',
                    type: 'ir.actions.server',
                    usage: 'ir_actions_server',
                }, {
                    model_name: 'foo',
                    name: 'Server Action 2',
                    type: 'ir.actions.server',
                    usage: 'ir_actions_server',
                    display_in_control_panel: true
                }],
            }
        });

        assert.containsNone(list, '.o_list_action_button', 'List view contains one server action button');

        list.destroy();
    });
});

});
