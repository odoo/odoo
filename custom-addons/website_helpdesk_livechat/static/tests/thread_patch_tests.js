/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";

addModelNamesToFetch(["helpdesk.ticket"]);

import { registry } from "@web/core/registry";

const viewArchsRegistry = registry.category("bus.view.archs");
const formArchsRegistry = viewArchsRegistry.category("form");
formArchsRegistry.add(
    "helpdesk.ticket",
    `<form>
        <sheet>
            <field name="name"/>
        </sheet>
        <div class="oe_chatter">
            <field name="activity_ids"/>
            <field name="message_follower_ids"/>
            <field name="message_ids"/>
        </div>
    </form>`
);

QUnit.module("thread (patch)");

QUnit.test("[technical] /ticket command gets a body as kwarg", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const messageId = pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
    });
    const [channelMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["discuss.channel.member"].write([channelMemberId], {
        seen_message_id: messageId,
    });
    const { openDiscuss } = await start({
        mockRPC(route, { model, method, kwargs }) {
            if (model === "discuss.channel" && method === "execute_command_helpdesk") {
                assert.step(`execute command helpdesk. body: ${kwargs.body}`);
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
        },
    });
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/ticket something");
    await click(".o-mail-Composer-send:not(:disabled)");
    assert.verifySteps(["execute command helpdesk. body: /ticket something"]);
});

QUnit.test("canned response should work in helpdesk ticket", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.shortcode"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    const ticketId = pyEnv["helpdesk.ticket"].create({ name: "My helpdesk ticket" });
    const { openFormView } = await start();
    openFormView("helpdesk.ticket", ticketId);
    await click(".o-mail-Chatter button", { text: "Send message" });
    await contains(".o-mail-Composer-suggestion strong", { count: 0, text: "hello" });

    await insertText(".o-mail-Composer-input", ":");
    await contains(".o-mail-Composer-suggestion strong", { text: "hello" });
});
