import { describe, test, expect } from "@odoo/hoot";
import { mountView, defineModels, fields, models } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
class User extends models.Model {
    _name = "res.users";
    has_group() {
        return true;
    }
}
class Resource extends models.Model {
    id = fields.Integer();
    name = fields.Char();
    avatar_128 = fields.Image()
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
        arch: `<list>
                    <field name="avatar_128" widget="resource_avatar" options="{'size': [24, 24], 'img_class': 'rounded-3'}" nolabel="1"/>
                    <field name="name"/>
                </list>`,
    });

    expect(".img").toHaveCount(1);
    expect(".fa-wrench").toHaveCount(1);
});
