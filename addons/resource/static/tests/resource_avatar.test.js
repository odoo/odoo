import { describe, test, expect, beforeEach } from "@odoo/hoot";
import { mountView } from "@web/../tests/web_test_helpers";
import { defineResourceModels } from "./resource_test_helpers"
import { ResourceResource } from "./mock_server/mock_models/resource_resource";

defineResourceModels();
describe.current.tags("desktop");

beforeEach(() => {
    ResourceResource._records = [
        {
            id: 1,
            name: "admin",
            resource_type: "user",
        },
        {
            id: 2,
            name: "crane",
            resource_type: "material",
        },
    ];
});

test("Check the resource avatar icon", async () => {
    await mountView({
        type: "list",
        resModel: 'resource.resource',
        arch: `<list>
                    <field name="avatar_128" widget="resource_avatar" options="{'size': [24, 24], 'img_class': 'rounded-3'}" nolabel="1"/>
                    <field name="name"/>
                </list>`,
    });

    expect(".img").toHaveCount(1);
    expect(".fa-wrench").toHaveCount(1);
});
