import {
    assertSteps,
    click,
    contains,
    openFormView,
    registerArchs,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { defineTestMailModels } from "@test_mail/../tests/test_mail_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

/**
 * Open a chat window when clicking on an avatar many2one / many2many properties.
 */
async function testPropertyFieldAvatarOpenChat(propertyType) {
    const pyEnv = await startServer();
    registerArchs({
        "mail.test.properties,false,form": `
            <form string="Form With Avatar Users">
                <sheet>
                    <field name="name"/>
                    <field name="parent_id"/>
                    <field name="properties"/>
                </sheet>
                <chatter/>
            </form>
        `,
    });
    onRpc("mail.test.properties", "has_access", () => true);
    onRpc("res.users", "read", () => {
        step("read res.users");
        return [{ id: userId, partner_id: [partnerId, "Partner Test"] }];
    });
    onRpc("res.users", "search_read", () => [{ id: userId, name: "User Test" }]);
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner Test" });
    const userId = pyEnv["res.users"].create({ name: "User Test", partner_id: partnerId });
    const parentId = pyEnv["mail.test.properties"].create({ name: "Parent" });
    const value = propertyType === "many2one" ? [userId, "User Test"] : [[userId, "User Test"]];
    const childId = pyEnv["mail.test.properties"].create({
        name: "Test",
        parent_id: parentId,
        properties: [
            { type: propertyType, comodel: "res.users", name: "user", string: "user", value },
        ],
    });
    await openFormView("mail.test.properties", childId);
    await assertSteps([]);
    await click(
        propertyType === "many2one" ? ".o_field_property_many2one_value img" : ".o_m2m_avatar"
    );
    await assertSteps(["read res.users"]);
    await contains(".o-mail-ChatWindow", { text: "Partner Test" });
}

describe.current.tags("desktop");
defineTestMailModels();

test("Properties fields: many2one avatar open chat on click", async () => {
    await testPropertyFieldAvatarOpenChat("many2one");
});

test("Properties fields: m2m avatar list open chat on click", async () => {
    await testPropertyFieldAvatarOpenChat("many2many");
});
