import { describe, test } from "@odoo/hoot";
import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    patchUiSize,
    start,
    startServer,
} from "../mail_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("auto-select 'Inbox' when discuss had channel as active thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ height: 360, width: 640 });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder:contains(Channel)");
    await click("button:contains(Mailboxes)");
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder:contains(Mailboxes)");
    await contains("button:contains(Inbox).active");
});
