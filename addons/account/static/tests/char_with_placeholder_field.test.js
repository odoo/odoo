import { expect, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fieldInput,
    fields,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";
import { defineAccountModels } from "./account_test_helpers";

class Account extends models.Model {
    _name = "account.account";
    _inherit = [];

    code = fields.Char({
        string: "Code",
        trim: true,
    });
    placeholder_code = fields.Char();

    _records = [
        {
            id: 1,
            placeholder_code: "Placeholder Code",
        },
    ];

    _views = {
        list: /* xml */ `
            <list editable="top" create="1" delete="1">
                <field name="placeholder_code" column_invisible="1" />
                <field name="code" widget="char_with_placeholder_field" options="{'placeholder_field': 'placeholder_code'}" />
            </list>
        `,
    };
}

defineAccountModels();
defineModels([Account]);
test.tags("desktop");
test("List: placeholder_field shows as text/placeholder", async () => {
    await mountView({
        type: "list",
        resModel: "account.account",
    });

    const firstCellSelector = "tbody td:not(.o_list_record_selector):first";

    expect(`${firstCellSelector} span`).toHaveText("Placeholder Code", {
        message: "placeholder_field should be the text value",
    });

    expect(`${firstCellSelector} span`).toHaveClass("text-muted", {
        message: "placeholder_field should be greyed out",
    });

    await contains(firstCellSelector).click();
    expect(queryFirst(firstCellSelector).parentElement).toHaveClass("o_selected_row", {
        message: "should be set as edit mode",
    });
    expect(`${firstCellSelector} input`).toHaveValue("", {
        message: "once in edit mode, should have no value in input",
    });
    expect(`${firstCellSelector} input`).toHaveAttribute("placeholder", "Placeholder Code", {
        message: "once in edit mode, should have placeholder_field as placeholder",
    });
    await fieldInput("code").edit("100001", { confirm: false });

    await contains(".o_list_button_save").click();
    expect(firstCellSelector).toHaveText("100001", {
        message: "entered value should be saved",
    });
    expect(firstCellSelector).not.toHaveClass("text-muted", {
        message: "field should not be greyed out",
    });
});
