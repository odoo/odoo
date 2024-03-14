const test = QUnit.test; // QUnit.test()

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { openFormView, start } from "@mail/../tests/helpers/test_utils";

import { assertSteps, click, contains, step } from "@web/../tests/utils";

QUnit.module("properties field");

/**
 * Open a chat window when clicking on an avatar many2one / many2many properties.
 */
async function testPropertyFieldAvatarOpenChat(propertyType) {
    const pyEnv = await startServer();
    const view = `
        <form string="Form With Avatar Users">
            <sheet>
                <field name="name"/>
                <field name="parent_id"/>
                <field name="properties"/>
            </sheet>
            <chatter/>
        </form>`;

    await start({
        serverData: {
            views: {
                "mail.test.properties,false,form": view,
            },
        },
        async mockRPC(route) {
            if (route.includes("/mail.test.properties/check_access_rights")) {
                return true;
            } else if (route === "/web/dataset/call_kw/res.users/read") {
                step("read res.users");
                return [{ id: userId, partner_id: [partnerId, "Partner Test"] }];
            } else if (route === "/web/dataset/call_kw/res.users/search_read") {
                return [{ id: userId, name: "User Test" }];
            }
        },
    });

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

test("Properties fields: many2one avatar open chat on click", async () => {
    await testPropertyFieldAvatarOpenChat("many2one");
});

test("Properties fields: m2m avatar list open chat on click", async () => {
    await testPropertyFieldAvatarOpenChat("many2many");
});
