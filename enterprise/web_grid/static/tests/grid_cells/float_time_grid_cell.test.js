import { expect, test } from "@odoo/hoot";
import { hover, queryFirst } from "@odoo/hoot-dom";
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

    _records = [{ id: 1, date: "2023-03-20", foo_id: 1, time: 9.1 }];

    _views = {
        grid: `<grid editable="1">
                    <field name="foo_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                    </field>
                    <field name="time" type="measure" widget="float_time"/>
                </grid>`,
    };
}

class Foo extends models.Model {
    name = fields.Char();

    _records = [{ name: "Foo" }];
}

defineModels([Grid, Foo]);

test.tags("desktop");
test("FloatTimeGridCell in grid view", async () => {
    mockDate("2023-03-20 00:00:00");
    onRpc("grid_unavailability", () => {
        return {};
    });
    await mountView({
        type: "grid",
        resModel: "grid",
    });
    await hover(queryFirst(".o_grid_row .o_grid_cell_readonly"));
    await runAllTimers();
    expect(".o_grid_cell").toHaveCount(1, { message: "The component should be mounted" });
    await animationFrame();
    expect(".o_grid_cell span").toHaveCount(1, {
        message: "The component should be readonly once it is mounted",
    });
    expect(".o_grid_cell input").toHaveCount(0, {
        message: "No input should be displayed in the component since it is readonly.",
    });
    expect(".o_grid_cell").toHaveText("9:06", {
        message: "The component should have the value correctly formatted",
    });
    await contains(".o_grid_cell").click();
    await animationFrame();
    expect(".o_grid_cell input").toHaveCount(1, {
        message: "The component should be in edit mode.",
    });
    expect(".o_grid_cell input").toHaveAttribute("inputmode", "text");
    expect(".o_grid_cell span").toHaveCount(0, {
        message: "The component should no longer be in readonly mode.",
    });
    await contains(".o_grid_cell input").edit("09:30");
    expect(".o_grid_cell_readonly").toHaveText("9:30", {
        message: "The edition should be taken into account.",
    });
    expect(".o_grid_component[name='foo_id'] .o_form_uri").toHaveAttribute("href", "/odoo/m-foo/1");
});
