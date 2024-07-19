import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    toggleActionMenu,
    toggleMenuItem,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    _name = "res.partner";
    _inherit = [];

    name = fields.Char({
        string: "Name",
        default: "My little Name Value",
        trim: true,
    });

    _records = [
        {
            id: 1,
            display_name: "first record",
            name: "yop",
        },
        {
            id: 2,
            display_name: "second record",
            name: "blip",
        },
        {
            id: 3,
            display_name: "aaa",
            name: "abc",
        },
    ];
}
class User extends models.Model {
    _name = "res.users";

    name = fields.Char();

    has_group() {
        return true;
    }
}

defineModels([Partner, User]);

test("Pass context when duplicating data in list view", async () => {

    onRpc("copy", ({ kwargs }) => {
        const { context } = kwargs;
        expect(context.ctx_key).toBe('ctx_val');
        expect.step('copy');
    });
    await mountView({
        type: "list",
        resModel: "res.partner",
        loadActionMenus: true,
        arch: `
            <tree>
                <field name="name" />
            </tree>`,
        context: {
            ctx_key: "ctx_val",
        }
    });

    const inputSelector = "tbody tr:first-child td.o_list_record_selector input";
    await contains(inputSelector).click();
    await toggleActionMenu();
    await toggleMenuItem("Duplicate");
    expect.verifySteps(["copy"]);
});
