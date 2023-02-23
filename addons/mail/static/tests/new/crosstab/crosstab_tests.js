/** @odoo-module **/

import { afterNextRender, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("crosstab");

QUnit.test("Messages are received cross-tab", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss(channelId);
    await tab1.insertText(".o-mail-composer-textarea", "Hello World!");
    await tab1.click("button:contains(Send)");
    assert.containsOnce(tab1.target, ".o-mail-message:contains(Hello World!)");
    assert.containsOnce(tab2.target, ".o-mail-message:contains(Hello World!)");
});

QUnit.test("Delete starred message updates counter", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "Hello World!",
        model: "mail.channel",
        res_id: channelId,
        starred_partner_ids: [pyEnv.currentPartnerId],
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss(channelId);
    assert.containsOnce(tab2.target, "button:contains(Starred1)");
    await afterNextRender(() =>
        tab1.env.services.rpc("/mail/message/update_content", {
            message_id: messageId,
            body: "",
            attachment_ids: [],
        })
    );
    assert.containsNone(tab2.target, "button:contains(Starred1)");
});
