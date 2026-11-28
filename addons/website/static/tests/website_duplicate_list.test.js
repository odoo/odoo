import { describe, expect, test } from "@odoo/hoot";
import {
    contains,
    defineActions,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    toggleActionMenu,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";
import { WebClient } from "@web/webclient/webclient";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

class Website extends models.Model {
    _name = "website";

    name = fields.Char();

    _records = [
        { id: 1, name: "Website 1" },
        { id: 2, name: "Website 2" },
    ];
    _views = {
        list: `<list js_class="website_duplicate_list"><field name="name"/></list>`,
    };
}

class WebsiteDuplicate extends models.Model {
    _name = "website.duplicate";

    name = fields.Char();

    _views = {
        form: `
            <form>
                <field name="name"/>
                <footer>
                    <button name="action_duplicate" type="object" string="Create"/>
                </footer>
            </form>`,
    };
}

defineModels([Website, WebsiteDuplicate]);
defineMailModels();
defineActions([
    {
        id: 1,
        res_model: "website",
        views: [[false, "list"]],
    },
    {
        id: 2,
        xml_id: "website.website_duplicate_action",
        res_model: "website.duplicate",
        target: "new",
        views: [[false, "form"]],
    },
]);

describe.current.tags("desktop");

test("duplicate the selected websites with the name given in the dialog", async () => {
    onRpc("website.duplicate", "action_duplicate", function ({ args, kwargs }) {
        const [wizard] = this.env["website.duplicate"].browse(args[0]);
        expect.step(["action_duplicate", wizard.name, kwargs.context.active_ids]);
        return false;
    });
    onRpc("website", "web_search_read", () => expect.step("load websites"));
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await contains(".o_data_row:eq(1) .o_list_record_selector input").click();
    await toggleActionMenu();
    await contains(".o_menu_item:contains(Duplicate)").click();
    expect(".modal .o_form_view").toHaveCount(1);

    await contains(".modal .o_field_widget[name=name] input").edit("Copy");
    await contains(".modal button[name=action_duplicate]").click();
    expect(".modal").toHaveCount(0);
    expect.verifySteps(["load websites", ["action_duplicate", "Copy", [2]], "load websites"]);
});

test("duplicate is not available to non-administrators", async () => {
    patchWithCleanup(user, { isSystem: false });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await contains(".o_data_row:eq(1) .o_list_record_selector input").click();
    await toggleActionMenu();
    expect(".o_menu_item:contains(Delete)").toHaveCount(1);
    expect(".o_menu_item:contains(Duplicate)").toHaveCount(0);
});
