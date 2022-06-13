/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

let serverData;
let target;

QUnit.module("Sales Team Dashboard", {
    beforeEach() {
        target = getFixture();
        serverData = {
            models: {
                "crm.team": {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        invoiced: { string: "Invoiced", type: "integer" },
                        invoiced_target: { string: "Invoiced_target", type: "integer" },
                    },
                    records: [{ id: 1, foo: "yop", invoiced: 0, invoiced_target: 0 }],
                },
            },
        };

        setupViewRegistries();
    },
});

QUnit.test("edit target with several o_kanban_primary_bottom divs", async (assert) => {
    assert.expect(4);

    const fakeActionService = {
        start: () => ({
            async doAction(action) {
                assert.deepEqual(
                    action,
                    {
                        res_model: "crm.team",
                        target: "current",
                        type: "ir.actions.act_window",
                        method: "get_formview_action",
                    },
                    "should trigger do_action with the correct args"
                );
                return true;
            },
        }),
    };
    serviceRegistry.add("action", fakeActionService, { force: true });

    await makeView({
        serverData,
        type: "kanban",
        resModel: "crm.team",
        arch: /* xml */`
            <kanban>
                <field name="invoiced_target"/>
                <templates>
                    <div t-name="kanban-box" class="container o_kanban_card_content">
                        <field name="invoiced" widget="sales_team_progressbar" options="{'current_value': 'invoiced', 'max_value': 'invoiced_target', 'editable': true, 'edit_max_value': true}"/>
                        <div class="col-12 o_kanban_primary_bottom"/>
                        <div class="col-12 o_kanban_primary_bottom bottom_block"/>
                    </div>
                </templates>
            </kanban>`,
        resId: 1,
        async mockRPC(route, { method, model }) {
            if (route === "/web/dataset/call_kw/crm.team/get_formview_action") {
                return {
                    method,
                    res_model: model,
                    target: "current",
                    type: "ir.actions.act_window",
                };
            }
        },
    });

    assert.containsOnce(
        target,
        ".o_field_sales_team_progressbar:contains(Click to define an invoicing target)"
    );
    assert.containsN(target, ".o_kanban_primary_bottom", 2);
    assert.containsNone(target, ".o_progressbar input");

    await click(target, ".sale_progressbar_form_link"); // should trigger a do_action
});
