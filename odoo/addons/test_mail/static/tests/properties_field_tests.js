/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("properties field");

/**
 * Open a chat window when clicking on an avatar many2one / many2many properties.
 */
async function testPropertyFieldAvatarOpenChat(assert, propertyType) {
    const pyEnv = await startServer();
    const view = `
        <form string="Form With Avatar Users">
            <sheet>
                <field name="name"/>
                <field name="parent_id"/>
                <field name="properties"/>
            </sheet>
            <div class="oe_chatter">
                <field name="message_ids"/>
            </div>
        </form>`;

    const { openView } = await start({
        serverData: {
            views: {
                "mail.test.properties,false,form": view,
            },
        },
        async mockRPC(route) {
            if (route.includes("/mail.test.properties/check_access_rights")) {
                return true;
            } else if (route === "/web/dataset/call_kw/res.users/read") {
                assert.step("read res.users");
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

    await openView({
        res_id: childId,
        res_model: "mail.test.properties",
        views: [[false, "form"]],
    });

    assert.verifySteps([]);
    await click(
        propertyType === "many2one" ? ".o_field_property_many2one_value img" : ".o_m2m_avatar"
    );
    assert.verifySteps(["read res.users"]);
    await contains(".o-mail-ChatWindow", { text: "Partner Test" });
}

QUnit.test("Properties fields: many2one avatar open chat on click", async function (assert) {
    await testPropertyFieldAvatarOpenChat(assert, "many2one");
});

QUnit.test("Properties fields: m2m avatar list open chat on click", async function (assert) {
    await testPropertyFieldAvatarOpenChat(assert, "many2many");
});
