import { describe, test, expect } from "@odoo/hoot";
import { defineResourceModels } from "./resource_test_helpers";
import { mountView, defineModels, fields, models } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineResourceModels();

class User extends models.Model {
    _name = "res.users";

    name = fields.Char();

    has_group() {
        return true;
    }
}
 class Resource extends models.Model {
    id = fields.Integer();
    name = fields.Char();
    resource_type = fields.Selection({
        selection: [
            ["user", "Human"],
            ["material", "material"],
        ],
        default: "user",
    });

    _records = [
        {
            id: 1,
            name: "admin",
            resource_type: "user"
        },
        {
            id: 2,
            name: "crane",
            resource_type: "material"
        },
    ];
}
defineModels([Resource, User]);

test("Check the resource avatar icon", async () => {
    await mountView({
        resModel: 'resource',
        type: "list",
        arch: `<list><field name="name" widget="resource_avatar"/> </list>`,
    });

    expect(".o_avatar").toHaveCount(1);
    expect(".fa-wrench").toHaveCount(1);
});
