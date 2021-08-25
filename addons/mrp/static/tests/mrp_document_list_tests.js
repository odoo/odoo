odoo.define('mrp.workcenter_routing_list_tests', function (require) {
    "use strict";

    const viewRegistry = require('web.view_registry');
    const MrpRoutingWorkcenterNoOpenTreeView = viewRegistry.get('mrp_routing_workcenter_no_open_tree_view');
    const testUtils = require('web.test_utils');

    const createView = testUtils.createView;

    QUnit.module('MRP List View', {}, function () {

        QUnit.module('MrpRoutingListView', {
            beforeEach: function () {
                this.data = {
                    'foo': {
                        fields: {
                            foo: { string: "Name", type: 'char', default: ' ' },
                        },
                        records: [
                            { id: 1, foo: 'test1' },
                            { id: 2, foo: 'test2' },
                        ],
                    },
                };
            },
        }, function () {
            QUnit.test('list with no_open="1"', async function (assert) {
                assert.expect(1);

                const list = await createView({
                    View: MrpRoutingWorkcenterNoOpenTreeView,
                    model: 'foo',
                    data: this.data,
                    viewOptions: { hasActionMenus: true },
                    arch: `<tree js_class="mrp_routing_workcenter_no_open_tree_view">
                        <field name="foo"/>
                    </tree>`,
                    debug: true,
                });

                testUtils.mock.intercept(list, "open_record", function () {
                    assert.step("list view should trigger 'open_record' event");
                });

                await testUtils.dom.click(list.$('.o_data_cell:first'));
                assert.verifySteps([]);

                list.destroy();
            });

        });

    });

});
