/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("data_merge", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                "data_merge.record": {
                    fields: {
                        name: { string: "Foo", type: "char" },
                        group_id: { type: "many2one", relation: "data_merge.group" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "a1",
                            group_id: 1,
                        },
                        {
                            id: 2,
                            name: "a2",
                            group_id: 1,
                        },
                        {
                            id: 3,
                            name: "b1",
                            group_id: 2,
                        },
                        {
                            id: 4,
                            name: "b2",
                            group_id: 2,
                        },
                    ],
                },
                "data_merge.group": {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "1",
                        },
                        {
                            id: 2,
                            name: "2",
                        },
                    ],
                },
            },
        };
        setupViewRegistries();
        target = getFixture();
    });

    QUnit.test("merge multiple records uses the domain selection", async function (assert) {
        assert.expect(1);
        await makeView({
            type: "list",
            resModel: "data_merge.record",
            serverData,
            groupBy: ["group_id"],
            arch: '<list expand="true" js_class="data_merge_list"><field name="name"/></list>',
            mockRPC: async (_, { method, args }) => {
                if (method === "merge_multiple_records") {
                    assert.deepEqual(args[0], {
                        1: [1, 2],
                        2: [3, 4],
                    });
                    return true;
                }
            },
        });
        await click(target, ".o_group_header:first-child"); // fold the first group
        await click(target, "thead .o_list_record_selector");
        await click(target, ".o_list_selection_box .o_list_select_domain");
        await click(target, ".btn-primary.o_data_merge_merge_button");
        await click(target, ".modal-dialog button.btn-primary");
    });
});
