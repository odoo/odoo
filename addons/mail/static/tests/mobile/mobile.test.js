import {
    SIZES,
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openDiscuss,
    patchUiSize,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";

describe.current.tags("mobile");
defineMailModels();

test("auto-select 'Inbox' when discuss had channel as active thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-ChatWindow [title*='Close Chat Window']");
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder", { text: "Channel" });
    await click("button", { text: "Mailboxes" });
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder", { text: "Mailboxes" });
    await contains("button.active", { text: "Inbox" });
});

test("show loading on initial opening", async () => {
    // This could load a lot of data (all pinned conversations)
    const def = new Deferred();
    onRpcBefore("/mail/action", async (args) => {
        if (args.channels_as_member) {
            await def;
        }
    });
    onRpcBefore("/mail/data", async (args) => {
        if (args.channels_as_member) {
            await def;
        }
    });
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu .fa.fa-circle-o-notch.fa-spin");
    await contains(".o-mail-NotificationItem", { text: "General", count: 0 });
    def.resolve();
    await contains(".o-mail-MessagingMenu .fa.fa-circle-o-notch.fa-spin", { count: 0 });
    await contains(".o-mail-NotificationItem", { text: "General" });
});

test("enter key should create a newline in composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Test\n");
    await press("Enter");
    await insertText(".o-mail-Composer-input", "Other");
    await click(".o-mail-Composer-send");
    await contains(".o-mail-Message-body:has(br)", { textContent: "TestOther" });
});
