/** @odoo-module */

import { click, editInput, getFixture, patchDate, nextTick } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

import { hoverGridCell } from "../helpers";

let serverData, target;

async function mockRPC(route, args) {
    if (args.method === "grid_unavailability") {
        return {};
    }
}

QUnit.module("Grid Cells", (hook) => {
    hook.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                grid: {
                    fields: {
                        foo_id: { string: "Foo", type: "many2one", relation: "foo" },
                        date: { string: "Date", type: "date" },
                        time: {
                            string: "Float time field",
                            type: "float",
                            digits: [2, 1],
                            group_operator: "sum",
                        },
                    },
                    records: [{ id: 1, date: "2023-03-20", foo_id: 1, time: 9.1 }],
                },
                foo: {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [{ name: "Foo" }],
                },
            },
            views: {
                "grid,false,grid": `<grid editable="1">
                    <field name="foo_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                    </field>
                    <field name="time" type="measure" widget="float_time"/>
                </grid>`,
            },
        };
        setupViewRegistries();
        patchDate(2023, 2, 20, 0, 0, 0);
    });

    QUnit.module("FloatTimeGridCell");

    QUnit.test("FloatTimeGridCell in grid view", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "grid",
            serverData,
            mockRPC,
            viewId: false,
        });

        const cells = target.querySelectorAll(".o_grid_row .o_grid_cell_readonly");
        const cell = cells[0];
        await hoverGridCell(cell);
        await nextTick();
        assert.containsOnce(target, ".o_grid_cell", "The component should be mounted");
        if (!target.querySelectorAll(".o_grid_cell span").length) {
            await nextTick();
        }
        assert.containsOnce(
            target,
            ".o_grid_cell span",
            "The component should be readonly once it is mounted"
        );
        assert.containsNone(
            target,
            ".o_grid_cell input",
            "No input should be displayed in the component since it is readonly."
        );
        assert.strictEqual(
            target.querySelector(".o_grid_cell").textContent,
            "9:06",
            "The component should have the value correctly formatted"
        );
        await click(target, ".o_grid_cell");
        await nextTick();
        assert.containsOnce(target, ".o_grid_cell input", "The component should be in edit mode.");
        assert.containsNone(
            target,
            ".o_grid_cell span",
            "The component should no longer be in readonly mode."
        );
        await editInput(target, ".o_grid_cell input", "09:30");
        assert.strictEqual(
            target.querySelector(".o_grid_cell_readonly").textContent,
            "9:30",
            "The edition should be taken into account."
        );
    });
});
