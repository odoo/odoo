/** @odoo-module */

import { click, getFixture, patchDate, nextTick, triggerEvent } from "@web/../tests/helpers/utils";
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
                    records: [
                        { date: "2023-03-20", foo_id: 1, time: 0.0 },
                        { date: "2023-03-21", foo_id: 2, time: 0.0 },
                    ],
                },
                foo: {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { name: "Foo" },
                        {name: "Bar"},
                    ],
                },
            },
            views: {
                "grid,false,grid": `<grid editable="1">
                    <field name="foo_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                    </field>
                    <field name="time" type="measure" widget="float_toggle"/>
                </grid>`,
                "grid,1,grid": `<grid editable="1">
                    <field name="foo_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                        <range name="week" string="Week" span="week" step="day" default="1"/>
                    </field>
                    <field name="time" type="measure" widget="float_toggle"/>
                </grid>`,
            },
        };
        setupViewRegistries();
        patchDate(2023, 2, 20, 0, 0, 0);
    });

    QUnit.module("FloatToggleGridCell");

    QUnit.test("FloatToggleGridCell: click to focus", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "grid",
            serverData,
            mockRPC,
            viewId: false,
        });

        const cell = target.querySelector(
            ".o_grid_row:not(.o_grid_row_total,.o_grid_row_title,.o_grid_column_total)"
        );
        assert.strictEqual(cell.textContent, "0.00", "Initial cell content should be 0.00");
        await hoverGridCell(cell);
        await nextTick();
        await click(target, ".o_grid_cell");
        assert.strictEqual(
            cell.textContent,
            "0.50",
            "Clicking on the cell alters the content of the cell and focuses it"
        );
    });

    QUnit.test("FloatToggleGridCell: keyboard navigation", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "grid",
            serverData,
            mockRPC,
            viewId: 1,
        });

        function checkGridCellInRightPlace(expectedGridRow, expectedGridColumn) {
            const gridCell = target.querySelector(".o_grid_cell");
            assert.strictEqual(gridCell.dataset.gridRow, expectedGridRow);
            assert.strictEqual(gridCell.dataset.gridColumn, expectedGridColumn);
        }

        const firstCell = target.querySelector(".o_grid_row[data-row='1'][data-column='0']");
        assert.strictEqual(firstCell.dataset.gridRow, "2");
        assert.strictEqual(firstCell.dataset.gridColumn, "2");
        await hoverGridCell(firstCell);
        await nextTick();
        assert.containsOnce(
            target,
            ".o_grid_cell",
            "The GridCell component should be mounted on the grid cell hovered"
        );
        checkGridCellInRightPlace(firstCell.dataset.gridRow, firstCell.dataset.gridColumn);
        await click(target, ".o_grid_cell");
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o_grid_cell").textContent,
            "0.50",
            "Clicking on the cell alters the content of the cell and focuses it"
        );
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_grid_cell button.o_field_float_toggle"),
            "The element focused should be the button of the grid cell"
        )

        // Go to the next cell
        await triggerEvent(document.activeElement, "", "keydown", { key: "tab" });
        checkGridCellInRightPlace("2", "3");

        // Go to the previous cell
        await triggerEvent(document.activeElement, "", "keydown", { key: "shift+tab" });
        checkGridCellInRightPlace("2", "2");

        // Go the cell below
        await triggerEvent(document.activeElement, "", "keydown", { key: "enter" });
        checkGridCellInRightPlace("3", "2");

        // Go up since it is the cell in the row
        await triggerEvent(document.activeElement, "", "keydown", { key: "enter" });
        checkGridCellInRightPlace("2", "3");

        await triggerEvent(document.activeElement, "", "keydown", { key: "shift+tab" });
        checkGridCellInRightPlace("2", "2");

        // Go to the last editable cell in the grid view since it is the first cell.
        await triggerEvent(document.activeElement, "", "keydown", { key: "shift+tab" });
        checkGridCellInRightPlace("3", "8");

        // Go back to the first cell since it is the last cell in grid view.
        await triggerEvent(document.activeElement, "", "keydown", { key: "tab" });
        checkGridCellInRightPlace("2", "2");

        // Go to the last editable cell in the grid view since it is the first cell.
        await triggerEvent(document.activeElement, "", "keydown", { key: "shift+tab" });
        checkGridCellInRightPlace("3", "8");

        // Go back to the first cell since it is the last cell in grid view.
        await triggerEvent(document.activeElement, "", "keydown", { key: "enter" });
        checkGridCellInRightPlace("2", "2");
    });

    QUnit.test("FloatToggleGridCell: click on magnifying glass", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "grid",
            serverData,
            mockRPC,
            viewId: false,
        });

        const cell = target.querySelector(
            ".o_grid_row:not(.o_grid_row_total,.o_grid_row_title,.o_grid_column_total)"
        );
        assert.strictEqual(cell.textContent, "0.00", "Initial cell content should be 0.00");
        await hoverGridCell(cell);
        await nextTick();
        await click(target, ".o_grid_search_btn");
        assert.strictEqual(
            cell.textContent,
            "0.00",
            "Clicking on the magnifying glass shouldn't alter the content of the cell"
        );
    });
});
