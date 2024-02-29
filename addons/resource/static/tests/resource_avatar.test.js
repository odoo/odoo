import { expect, test } from "@odoo/hoot";
import { defineModels, mountView } from "@web/../tests/web_test_helpers";
import { resouce, user} from "@resource/../tests/mock_server/mock_models/resouce_model";

defineModels([resouce, user]);

test("Check the resource avatar icon", async () => {
     await mountView({
        resModel: "resouce.resouce",
        type: "list",
        arch: `<tree><field name="name" widget="resource_avatar"/></tree>`,
    });

    expect(".o_avatar").toHaveCount(1);
    expect(".fa-wrench").toHaveCount(1);

});
