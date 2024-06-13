import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("show unread messages banner when there are unread messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", {
        text: "message 0",
    });
    await contains("span", { text: "30 new messagesMark as Read" });
});

test("mark thread as read from unread messages banner", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (let i = 0; i < 30; ++i) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: `message ${i}`,
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", {
        text: "message 0",
    });
    await click("span", {
        text: "Mark as Read",
        parent: ["span", { text: "30 new messagesMark as Read" }],
    });
    await contains(".o-mail-Thread-jumpToUnread", { count: 0 });
});
