import "@portal/views/fields/portal_wizard_user_one2many";

import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Wizard extends models.Model {
    users = fields.One2many({ relation: "portal.user", relation_field: "wizard_id" });
    _records = [{ id: 1, users: [1] }];
}
class PortalUser extends models.Model {
    _name = "portal.user";
    wizard_id = fields.Many2one({ relation: "wizard" });
    email = fields.Char({ required: true });
    _records = [{ id: 1, wizard_id: 1, email: "alice@example.com" }];
}
defineModels([Wizard, PortalUser]);

const arch = `<form><field name="users" widget="portal_wizard_user_one2many">
    <list editable="bottom"><field name="email"/>
        <button name="action_refresh_modal" type="object" icon="fa-check"/>
        <button name="action_grant_access" type="object" string="Grant"/>
    </list></field></form>`;

test("email status icons do not call the server, access buttons do", async () => {
    onRpc("action_refresh_modal", () => expect.step("unexpected refresh"));
    onRpc("action_grant_access", () => {
        expect.step("grant");
        return false;
    });
    await mountView({ type: "form", resModel: "wizard", resId: 1, arch });
    await contains('button[name="action_refresh_modal"]').click();
    expect.verifySteps([]);
    await contains('button[name="action_grant_access"]').click();
    expect.verifySteps(["grant"]);
});

test("editing a row still saves before granting access", async () => {
    onRpc("web_save", () => expect.step("save"));
    onRpc("action_grant_access", () => {
        expect.step("grant");
        return false;
    });
    await mountView({ type: "form", resModel: "wizard", resId: 1, arch });
    await contains('.o_data_cell[name="email"]').click();
    await contains('.o_field_widget[name="email"] input').edit("changed@example.com");
    await contains('button[name="action_grant_access"]').click();
    expect.verifySteps(["save", "grant"]);
});

test("invalid edited rows do not leave the access action locked", async () => {
    onRpc("action_grant_access", () => {
        expect.step("grant");
        return false;
    });
    await mountView({ type: "form", resModel: "wizard", resId: 1, arch });
    await contains('.o_data_cell[name="email"]').click();
    await contains('.o_field_widget[name="email"] input').edit("");
    await contains('button[name="action_grant_access"]').click();
    expect.verifySteps([]);
    await contains('.o_field_widget[name="email"] input').edit("valid@example.com");
    await contains('button[name="action_grant_access"]').click();
    expect.verifySteps(["grant"]);
});
