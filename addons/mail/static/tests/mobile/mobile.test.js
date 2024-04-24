import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    patchUiSize,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("auto-select 'Inbox' when discuss had channel as active thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ height: 360, width: 640 });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder", { text: "Channel" });
    await click("button", { text: "Mailboxes" });
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder", { text: "Mailboxes" });
    await contains("button.active", { text: "Inbox" });
});
