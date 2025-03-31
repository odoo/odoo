/** @odoo-module alias=@web/../tests/mobile/views/kanban_view_tests default=false */

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { AnimatedNumber } from "@web/views/view_components/animated_number";

let serverData;
let target;

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(AnimatedNumber, { enableAnimations: false });
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        product_id: {
                            string: "something_id",
                            type: "many2one",
                            relation: "product",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            foo: "yop",
                            product_id: 3,
                        },
                        {
                            id: 2,
                            foo: "blip",
                            product_id: 5,
                        },
                        {
                            id: 3,
                            foo: "gnap",
                            product_id: 3,
                        },
                        {
                            id: 4,
                            foo: "blip",
                            product_id: 5,
                        },
                    ],
                },
                product: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Display Name", type: "char" },
                    },
                    records: [
                        { id: 3, name: "hello" },
                        { id: 5, name: "xmo" },
                    ],
                },
            },
            views: {},
        };
        target = getFixture();

        setupViewRegistries();
    });

    QUnit.module("KanbanView");

    QUnit.test("Should load grouped kanban with folded column", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <progressbar field="foo" colors='{"yop": "success", "blip": "danger"}'/>
                    <templates>
                        <t t-name="card">
                            <field name="foo"/>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
            async mockRPC(route, args, performRPC) {
                if (args.method === "web_read_group") {
                    const result = await performRPC(route, args);
                    result.groups[1].__fold = true;
                    return result;
                }
            },
        });
        assert.containsN(target, ".o_column_progress", 2, "Should have 2 progress bar");
        assert.containsN(target, ".o_kanban_group", 2, "Should have 2 grouped column");
        assert.containsN(target, ".o_kanban_record", 2, "Should have 2 loaded record");
        assert.containsOnce(
            target,
            ".o_kanban_load_more",
            "Should have a folded column with a load more button"
        );
        await click(target, ".o_kanban_load_more button");
        assert.containsNone(target, ".o_kanban_load_more", "Shouldn't have a load more button");
        assert.containsN(target, ".o_kanban_record", 4, "Should have 4 loaded record");
    });
});
