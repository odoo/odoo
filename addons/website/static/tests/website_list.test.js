import { describe, expect, test } from "@odoo/hoot";
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
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

class Website extends models.Model {
    _name = "website";

    name = fields.Char();

    _records = [
        { id: 1, name: "My Website" },
        { id: 2, name: "Other Website" },
    ];
}

defineModels([Website]);
defineMailModels();

describe.current.tags("desktop");

test("duplicate websites from the list view", async () => {
    onRpc("website", "copy", ({ args, kwargs }) => {
        expect.step(`copy ${args[0]} as ${kwargs.default.name}`);
        return [];
    });
    onRpc("website", "web_search_read", () => {
        expect.step("reload");
    });
    await mountView({
        type: "list",
        resModel: "website",
        arch: `<list js_class="website_list"><field name="name"/></list>`,
        actionMenus: {},
    });
    expect.verifySteps(["reload"]);

    await contains(".o_data_row:eq(0) .o_list_record_selector input").click();
    await contains(".o_data_row:eq(1) .o_list_record_selector input").click();
    await toggleActionMenu();
    await toggleMenuItem("Duplicate");
    expect(".modal .modal-footer .btn-primary").not.toBeEnabled({
        message: "the name of the new website is required",
    });

    await contains(".modal input[type=text]").edit("New Website");
    await contains(".modal .modal-footer .btn-primary").click();
    expect(".modal").toHaveCount(0);
    expect.verifySteps(["copy 1 as New Website", "copy 2 as New Website 2", "reload"]);
});
