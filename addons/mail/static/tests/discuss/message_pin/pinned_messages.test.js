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
    await contains(".o-discuss-PinnedMessagesPanel p", {
        text: "This channel doesn't have any pinned messages.",
    });
    await click(".o-mail-Message [title='Expand']");
    await click(".dropdown-item", { text: "Pin" });
    await click(".modal-footer button", { text: "Yeah, pin it!" });
    await contains(".o-discuss-PinnedMessagesPanel .o-mail-Message", { text: "Hello world!" });
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
    await click(".dropdown-item", { text: "Unpin" });
    await click(".modal-footer button", { text: "Yes, remove it please" });
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
    await click(".dropdown-item", { text: "Delete" });
    await click("button", { text: "Confirm" });
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
    await click(":nth-child(1 of .o-mail-Message) [title='Expand']");
    await click(".dropdown-item", { text: "Pin" });
    await click(".modal-footer button", { text: "Yeah, pin it!" });
    await contains(".o-discuss-PinnedMessagesPanel", { count: 0 });
    await click(".o_mail_notification a", { text: "See all pinned messages" });
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
    await click(".o-discuss-PinnedMessagesPanel button", { text: "Jump" });
    await contains(".o-mail-Thread .o-mail-Message-body", { text: "Hello world!", visible: true });
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
    await click(":nth-child(1 of .o-mail-Message) [title='Expand']");
    await click(".dropdown-item", { text: "Pin" });
    await click(".modal-footer button", { text: "Yeah, pin it!" });
    await contains(".o_mail_notification");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await click(".o_mail_notification a", { text: "message" });
    await contains(".o-mail-Thread", { count: 0, scroll: "bottom" });
});
