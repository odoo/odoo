import { test } from "@odoo/hoot";
import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    patchUiSize,
    startClient,
    startServer,
} from "../mail_test_helpers";

defineMailModels();

test("auto-select 'Inbox' when discuss had channel as active thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ height: 360, width: 640 });
    await startClient();
    await openDiscuss(channelId);
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder", { text: "Channel" });
    await click("button", { text: "Mailboxes" });
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder", { text: "Mailboxes" });
    await contains("button.active", { text: "Inbox" });
});
