import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { hover, press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockDate, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Grid extends models.Model {
    foo_id = fields.Many2one({ string: "Foo", relation: "foo" });
    date = fields.Date({ string: "Date" });
    time = fields.Float({
        string: "Float time field",
        digits: [2, 1],
        aggregator: "sum",
    });

    _records = [
        { date: "2023-03-20", foo_id: 1, time: 0.0 },
        { date: "2023-03-21", foo_id: 2, time: 0.0 },
    ];

    _views = {
        "grid,false": `<grid editable="1">
            <field name="foo_id" type="row"/>
            <field name="date" type="col">
                <range name="day" string="Day" span="day" step="day"/>
            </field>
            <field name="time" type="measure" widget="float_toggle"/>
        </grid>`,
        "grid,1": `<grid editable="1">
            <field name="foo_id" type="row"/>
            <field name="date" type="col">
                <range name="day" string="Day" span="day" step="day"/>
                <range name="week" string="Week" span="week" step="day" default="1"/>
            </field>
            <field name="time" type="measure" widget="float_toggle"/>
        </grid>`,
    };
}

class Foo extends models.Model {
    name = fields.Char();

    _records = [{ name: "Foo" }, { name: "Bar" }];
}

defineModels([Grid, Foo]);

onRpc("grid_unavailability", () => {
    return {};
});

beforeEach(() => {
    mockDate("2023-03-20 00:00:00");
});

describe.current.tags("desktop");

test("FloatToggleGridCell: click to focus", async () => {
    await mountView({
        type: "grid",
        resModel: "grid",
    });

    const cell = queryOne(
        ".o_grid_row:not(.o_grid_row_total,.o_grid_row_title,.o_grid_column_total)"
    );
    expect(cell).toHaveText("0.00", { message: "Initial cell content should be 0.00" });
    await hover(cell);
    await runAllTimers();
    await contains(".o_grid_cell").click();
    await animationFrame();
    expect(".o_grid_cell").toHaveText("0.50", {
        message: "Clicking on the cell alters the content of the cell and focuses it",
    });
});

test("FloatToggleGridCell: keyboard navigation", async () => {
    await mountView({
        type: "grid",
        resModel: "grid",
        viewId: 1,
    });

    function checkGridCellInRightPlace(expectedGridRow, expectedGridColumn) {
        const gridCell = queryOne(".o_grid_cell");
        expect(gridCell.dataset.gridRow).toBe(expectedGridRow);
        expect(gridCell.dataset.gridColumn).toBe(expectedGridColumn);
    }

    const firstCell = queryOne(".o_grid_row[data-row='1'][data-column='0']");
    expect(firstCell.dataset.gridRow).toBe("2");
    expect(firstCell.dataset.gridColumn).toBe("2");
    await hover(firstCell);
    await runAllTimers();
    expect(".o_grid_cell").toHaveCount(1, {
        message: "The GridCell component should be mounted on the grid cell hovered",
    });
    checkGridCellInRightPlace(firstCell.dataset.gridRow, firstCell.dataset.gridColumn);
    await contains(".o_grid_cell").click();
    await animationFrame();
    expect(".o_grid_cell").toHaveText("0.50", {
        message: "Clicking on the cell alters the content of the cell and focuses it",
    });
    expect(".o_grid_cell button.o_field_float_toggle").toBeFocused({
        message: "The element focused should be the button of the grid cell",
    });

    // Go to the next cell
    await press("tab");
    await animationFrame();
    checkGridCellInRightPlace("2", "3");

    // Go to the previous cell
    await press("shift+tab");
    await animationFrame();
    checkGridCellInRightPlace("2", "2");

    // Go the cell below
    await press("enter");
    await animationFrame();
    checkGridCellInRightPlace("3", "2");

    // Go up since it is the cell in the row
    await press("enter");
    await animationFrame();
    checkGridCellInRightPlace("2", "3");

    await press("shift+tab");
    await animationFrame();
    checkGridCellInRightPlace("2", "2");

    // Go to the last editable cell in the grid view since it is the first cell.
    await press("shift+tab");
    await animationFrame();
    checkGridCellInRightPlace("3", "8");

    // Go back to the first cell since it is the last cell in grid view.
    await press("tab");
    await animationFrame();
    checkGridCellInRightPlace("2", "2");

    // Go to the last editable cell in the grid view since it is the first cell.
    await press("shift+tab");
    await animationFrame();
    checkGridCellInRightPlace("3", "8");

    // Go back to the first cell since it is the last cell in grid view.
    await press("enter");
    await animationFrame();
    checkGridCellInRightPlace("2", "2");
});

test("FloatToggleGridCell: click on magnifying glass", async () => {
    await mountView({
        type: "grid",
        resModel: "grid",
    });

    const cell = queryOne(
        ".o_grid_row:not(.o_grid_row_total,.o_grid_row_title,.o_grid_column_total)"
    );
    expect(cell).toHaveText("0.00", { message: "Initial cell content should be 0.00" });
    await hover(cell);
    await runAllTimers();
    await contains(".o_grid_search_btn").click();
    expect(".o_grid_cell").toHaveText("0.00", {
        message: "Clicking on the magnifying glass shouldn't alter the content of the cell",
    });
});
