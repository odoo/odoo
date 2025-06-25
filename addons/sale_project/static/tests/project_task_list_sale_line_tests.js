/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("Sale Project Task List View", (hooks) => {
    QUnit.test("cannot edit sale_line_id when partners are diffrent", async function (assert) {
        const target = getFixture();
        setupViewRegistries();
        await makeView({
            type: "list",
            resModel: "project.task",
            arch: `
                <list multi_edit="1" js_class="project_task_list">
                    <field name="partner_id"/>
                    <field name="sale_line_id"/>
                </list>
            `,
            serverData: {
                models: {
                    "project.task": {
                        fields: {
                            partner_id: {
                                string: "Customer",
                                type: "many2one",
                                relation: "res.partner",
                            },
                            sale_line_id: {
                                string: "Sale Order",
                                type: "many2one",
                                relation: "sale.order.line",
                            }
                        },
                        records: [
                            {
                                id: 1,
                                partner_id: 1,
                                sale_line_id: 1,
                            }, {
                                id: 2,
                                partner_id: 2,
                                sale_line_id: 1,
                            }
                        ],
                    },
                    "res.partner": {
                        records: [
                            {
                                id: 1,
                                name: "Deco Addict",
                            }, {
                                id: 2,
                                name: "Azure Interior",
                            },
                        ],
                    },
                    "sale.order.line": {
                        records: [
                            {
                                id: 1,
                                name: "order1",
                            }, {
                                id: 2,
                                name: "order2",
                            },
                        ],
                    },
                },
            }
        });
        const [firstRow, secondRow] = target.querySelectorAll(".o_data_row");
        await click(firstRow.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsNone(firstRow, ".o_readonly_modifier", "None of the fields should be readonly");
        assert.containsNone(secondRow, ".o_readonly_modifier", "None of the fields should be readonly");

        await click(secondRow.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(firstRow, ".o_readonly_modifier");
        assert.hasClass(firstRow.querySelectorAll(".o_data_cell")[1], "o_readonly_modifier", "The sale_ine_id should be readonly");
        assert.containsOnce(secondRow, ".o_readonly_modifier");
        assert.hasClass(secondRow.querySelectorAll(".o_data_cell")[1], "o_readonly_modifier", "The sale_ine_id should be readonly");
    });
});
