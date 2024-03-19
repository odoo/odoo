import { describe, test } from "@odoo/hoot";
import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "../../mail_test_helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Pin message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Pinned Messages']");
    await contains(
        ".o-discuss-PinnedMessagesPanel:contains(This channel doesn't have any pinned messages.)"
    );
    await click(".o-mail-Message [title='Expand']");
    await click(".dropdown-item:contains(Pin)");
    await click(".modal-footer button:contains(Yeah, pin it!)");
    await contains(".o-discuss-PinnedMessagesPanel .o-mail-Message:contains(Hello world!)");
});

test("Unpin message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-03-30 11:27:11",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Pinned Messages']");
    await contains(".o-discuss-PinnedMessagesPanel .o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".dropdown-item:contains(Unpin)");
    await click(".modal-footer button:contains(Yes, remove it please)");
    await contains(".o-discuss-PinnedMessagesPanel .o-mail-Message", { count: 0 });
});

test("Deleted messages are not pinned", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-03-30 11:27:11",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Pinned Messages']");
    await contains(".o-discuss-PinnedMessagesPanel .o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".dropdown-item:contains(Delete)");
    await click("button:contains(Confirm)");
    await contains(".o-discuss-PinnedMessagesPanel .o-mail-Message", { count: 0 });
});

test("Open pinned panel from notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message:eq(0) [title='Expand']");
    await click(".dropdown-item:contains(Pin)");
    await click(".modal-footer button:contains(Yeah, pin it!)");
    await contains(".o-discuss-PinnedMessagesPanel", { count: 0 });
    await click(".o_mail_notification a:contains(See all pinned messages)");
    await contains(".o-discuss-PinnedMessagesPanel");
});

test("Jump to message", async () => {
    // make scroll behavior instantaneous.
    patchWithCleanup(Element.prototype, {
        scrollIntoView() {
            return super.scrollIntoView(true);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-04-03 08:15:04",
    });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(25),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Pinned Messages']");
    await click(".o-discuss-PinnedMessagesPanel button:contains(Jump)");
    await contains(".o-mail-Thread .o-mail-Message-body:contains(Hello world!)", { visible: true });
});

test("Jump to message from notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(25),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 21 });
    await click(".o-mail-Message:eq(0) [title='Expand']");
    await click(".dropdown-item:contains(Pin)");
    await click(".modal-footer button:contains(Yeah, pin it!)");
    await contains(".o_mail_notification");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await click(".o_mail_notification a:eq(0):contains(message)");
    await contains(".o-mail-Thread", { count: 0, scroll: "bottom" });
});
