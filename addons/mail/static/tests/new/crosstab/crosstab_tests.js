/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";

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
