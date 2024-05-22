odoo.define("stock.orderpoint_tests", function (require) {
    "use strict";

    const { createView, dom, nextTick } = require("web.test_utils");
    const StockOrderpointListView = require("stock.StockOrderpointListView");

    QUnit.module(
        "Views",
        {
            beforeEach: function () {
                this.data = {
                    person: {
                        fields: {
                            name: { string: "Name", type: "char" },
                            age: { string: "Age", type: "integer" },
                            job: { string: "Profession", type: "char" },
                        },
                        records: [
                            { id: 1, name: "Daniel Fortesque", age: 32, job: "Soldier" },
                            { id: 2, name: "Samuel Oak", age: 64, job: "Professor" },
                            { id: 3, name: "Leto II Atreides", age: 128, job: "Emperor" },
                        ],
                    },
                };
            },
        },
        () => {
            QUnit.module("StockOrderpointListView");

            QUnit.test(
                "domain selection: order should be called on all records",
                async function (assert) {
                    assert.expect(1);

                    const view = await createView({
                        View: StockOrderpointListView,
                        model: "person",
                        data: this.data,
                        arch: `
                            <tree js_class="stock_orderpoint_list" limit="1">
                                <field name="name"/>
                            </tree>`,
                        mockRPC: function (route, { args, method, model }) {
                            if (method === "action_replenish") {
                                assert.deepEqual(
                                    { args, model },
                                    { args: [[1, 2, 3]], model: "person" }
                                );
                                return Promise.resolve({});
                            }
                            return this._super.apply(this, arguments);
                        },
                    });

                    await dom.click(view.$("thead .o_list_record_selector input"));
                    await dom.click(view.$(".o_list_selection_box .o_list_select_domain"));
                    await dom.click(view.$(".o_button_order"));
                    await nextTick();
                    view.destroy();
                }
            );

            QUnit.test(
                "domain selection: snooze should be called on all records",
                async function (assert) {
                    assert.expect(1);

                    const view = await createView({
                        View: StockOrderpointListView,
                        model: "person",
                        data: this.data,
                        arch: `
                            <tree js_class="stock_orderpoint_list" limit="1">
                                <field name="name"/>
                            </tree>`,
                        intercepts: {
                            do_action: function (event) {
                                if (event.data.action === "stock.action_orderpoint_snooze") {
                                    assert.deepEqual(event.data.options.additional_context, {
                                        default_orderpoint_ids: [1, 2, 3],
                                    });
                                }
                            },
                        },
                    });

                    await dom.click(view.$("thead .o_list_record_selector input"));
                    await dom.click(view.$(".o_list_selection_box .o_list_select_domain"));
                    await dom.click(view.$(".o_button_snooze"));
                    await nextTick();
                    view.destroy();
                }
            );
        }
    );
});
