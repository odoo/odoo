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

test("navigate to sub channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    // Should access sub-thread after its creation.
    await contains(".o-mail-Discuss-threadName", { value: "General" });
    await click("button[title='Show threads']");
    await click("button", { text: "Create Thread" });
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
    // Should access sub-thread after clicking on the menu.
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await contains(".o-mail-Discuss-threadName", { value: "General" });
    await click("button[title='Show threads']");
    await click(".o-mail-NotificationItem", { text: "New Thread" });
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
    // Should access sub-thread after clicking on the notification.
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
    await contains(".o-mail-NotificationMessage", {
        text: `${serverState.partnerName} started a thread: New Thread.See all threads.`,
    });
    await click(".o-mail-NotificationMessage a", { text: "New Thread" });
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
});

test("open sub channel menu from notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss-threadName", { value: "General" });
    await click("button[title='Show threads']");
    await click("button", { text: "Create Thread" });
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await contains(".o-mail-NotificationMessage", {
        text: `${serverState.partnerName} started a thread: New Thread.See all threads.`,
    });
    await click(".o-mail-NotificationMessage a", { text: "See all threads" });
    await contains(".o-mail-SubChannelList");
});

test("create sub thread from existing message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
        body: "Selling a training session and selling the products after the training session is more efficient.",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message-actions [title='Expand']");
    await click("[title='Create Thread']");
    await contains(".o-mail-Discuss-threadName", { value: "Selling a training session and" });
    await contains(".o-mail-Message", {
        text: "Selling a training session and selling the products after the training session is more efficient.",
    });
});
