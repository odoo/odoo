import {
    defineActions,
    defineModels,
    fields,
    models,
    mountView,
} from "../web_test_helpers";
import { expect, test } from "@odoo/hoot";


class ResUsers extends models.Model {
    _name = "res.users";

    name = fields.Char();

    has_group() {
        return true;
    }

    _records = [
        { id: 1, name: "User 1" },
    ];
}

class Foo extends models.Model {
    _name = "foo";

    value = fields.Boolean();

    _records = [
        {
            id: 1,
            value: true,
        },
    ];
}

defineModels([Foo, ResUsers]);

defineActions([
    {
        id: 1,
        xml_id: "action_report_1",
        name: "Some Report always visible",
        report_name: "some_report",
        report_type: "qweb-pdf",
        type: "ir.actions.report",
        binding_model_id: "foo",
        binding_type: "report",
    },
    {
        id: 2,
        xml_id: "action_report_2",
        name: "Some Report with satisfied domain",
        report_name: "some_report",
        report_type: "qweb-pdf",
        type: "ir.actions.report",
        binding_model_id: "foo",
        binding_type: "report",
        domain: [["value", "=", "True"]],
    },
    {
        id: 3,
        xml_id: "action_report_3",
        name: "Some Report with no satisfied domain",
        report_name: "some_report",
        report_type: "qweb-pdf",
        type: "ir.actions.report",
        binding_model_id: "foo",
        binding_type: "report",
        domain: [["value", "=", "False"]],
    },
]);

test("simple rendering", async () => {
    await mountView({
        type: "list",
        resModel: "foo",
        resId: 1,
        actionMenus: {
            action: [
                {
                    id: 44,
                    name: "Custom Action",
                    type: "ir.actions.act_window",
                    target: "new",
                },
            ],
            print: [],
        },
        loadActionMenus: true,
        arch: /* xml */ `
              <list>
                  <field name="value"/>
              </list>
         `,
    });
    expect(".o_cp_action_menus").toBeVisible();
});
