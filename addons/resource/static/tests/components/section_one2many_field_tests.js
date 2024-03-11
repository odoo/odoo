/** @odoo-module */

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("SectionOneToManyField", (hooks) => {
    let serverData;
    let target;

    hooks.beforeEach(() => {
        target = getFixture();

        serverData = {
            models: {
                partner: {
                    fields: { lines: { type: "one2many", relation: "lines_sections" } },
                    records: [
                        {
                            id: 1,
                            lines: [1, 2],
                        },
                    ],
                },
                lines_sections: {
                    fields: {
                        display_type: { type: "char" },
                        title: { type: "char", string: "Title" },
                        int: { type: "number", string: "integer" },
                    },
                    records: [
                        {
                            id: 1,
                            display_type: "line_section",
                            title: "firstSectionTitle",
                            int: 4,
                        },
                        {
                            id: 2,
                            display_type: false,
                            title: "recordTitle",
                            int: 5,
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.test("basic rendering", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="lines" widget="section_one2many">
                        <tree>
                            <field name="display_type" invisible="1" />
                            <field name="title" />
                            <field name="int" />
                        </tree>
                    </field>
                </form>
            `,
        });
        assert.containsOnce(target, ".o_field_x2many .o_list_renderer table.o_section_list_view");
        assert.containsN(target, ".o_data_row", 2);
        const rows = target.querySelectorAll(".o_data_row");
        assert.hasClass(rows[0], "o_is_line_section fw-bold");
        assert.doesNotHaveClass(rows[1], "o_is_line_section fw-bold");
        assert.strictEqual(rows[0].textContent, "firstSectionTitle");
        assert.strictEqual(rows[1].textContent, "recordTitle5");
        assert.strictEqual(rows[0].querySelector("td[name=title]").getAttribute("colspan"), "3");
        assert.strictEqual(rows[1].querySelector("td[name=title]").getAttribute("colspan"), null);
        assert.containsOnce(target, ".o_list_record_remove");
        assert.containsNone(target, ".o_is_line_section .o_list_record_remove");
    });
});
