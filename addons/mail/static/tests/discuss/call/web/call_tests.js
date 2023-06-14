/* @odoo-module */

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";

import { editInput, triggerEvent } from "@web/../tests/helpers/utils";

QUnit.module("call");

QUnit.test("no default rtc after joining a chat conversation", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem");

    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await afterNextRender(() =>
        editInput(document.body, ".o-discuss-ChannelSelector input", "mario")
    );
    await click(".o-discuss-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-discuss-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.containsNone($, ".o-mail-Discuss-content .o-mail-Message");
    assert.containsNone($, ".o-discuss-Call");
});

QUnit.test("no default rtc after joining a group conversation", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem");
    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await afterNextRender(() =>
        editInput(document.body, ".o-discuss-ChannelSelector input", "mario")
    );
    await click(".o-discuss-ChannelSelector-suggestion");
    await afterNextRender(() =>
        editInput(document.body, ".o-discuss-ChannelSelector input", "luigi")
    );
    await click(".o-discuss-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-discuss-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.containsNone($, ".o-mail-Discuss-content .o-mail-Message");
    assert.containsNone($, ".o-discuss-Call");
});
