// @ts-check

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    webModels,
} from "@web/../tests/web_test_helpers";

class Foo extends models.Model {
    name = fields.Char();
    note = fields.Char();
    _records = [{ id: 1, name: "a", note: "n" }];
}

const { ResCompany, ResPartner, ResUsers } = webModels;

defineModels([Foo, ResCompany, ResPartner, ResUsers]);

/**
 * An editable list whose `note` column is required but hidden behind the
 * optional-columns gear. Leaving it empty makes the record invalid with the
 * culprit off screen.
 */
const ARCH = `
    <list editable="top">
        <field name="name"/>
        <field name="note" optional="hide" required="1"/>
    </list>`;

test.tags("desktop");
test("an invalid hidden optional column marks the gear and its dropdown entry", async () => {
    await mountView({ resModel: "foo", type: "list", arch: ARCH });

    expect(".o_optional_columns_dropdown button").not.toHaveClass(
        "o_invalid_optional_columns_button",
    );

    await contains(".o_list_button_add").click();
    await contains("[name=name] input").edit("b");
    await contains(".o_list_view").click();

    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row");
    expect(".o_optional_columns_dropdown button").toHaveClass(
        "o_invalid_optional_columns_button",
    );

    await contains(".o_optional_columns_dropdown_toggle").click();
    expect(".o-dropdown--menu .o_invalid_dropdown_item").toHaveCount(1);
    expect(".o-dropdown--menu .o_invalid_dropdown_item").toHaveText("Note");
});

test.tags("desktop");
test("showing the invalid optional column clears the marks: the cell carries them now", async () => {
    await mountView({ resModel: "foo", type: "list", arch: ARCH });

    await contains(".o_list_button_add").click();
    await contains("[name=name] input").edit("b");
    await contains(".o_list_view").click();

    await contains(".o_optional_columns_dropdown_toggle").click();
    expect(".o_optional_columns_dropdown button").toHaveClass(
        "o_invalid_optional_columns_button",
    );
    expect(".o-dropdown--menu .o_invalid_dropdown_item").toHaveCount(1);

    await contains(".o-dropdown--menu input[type=checkbox]").click();
    await animationFrame();

    expect(".o_optional_columns_dropdown button").not.toHaveClass(
        "o_invalid_optional_columns_button",
    );
    expect(".o-dropdown--menu .o_invalid_dropdown_item").toHaveCount(0);
    expect(".o_data_row:eq(0) .o_field_widget[name=note]").toHaveClass(
        "o_field_invalid",
    );
});

test.tags("desktop");
test("a valid record leaves the gear alone even with a hidden required column", async () => {
    await mountView({ resModel: "foo", type: "list", arch: ARCH });

    await contains(".o_data_cell").click();
    await contains("[name=name] input").edit("b");
    await contains(".o_list_view").click();

    expect(".o_selected_row").toHaveCount(0);
    expect(".o_optional_columns_dropdown button").not.toHaveClass(
        "o_invalid_optional_columns_button",
    );
});
