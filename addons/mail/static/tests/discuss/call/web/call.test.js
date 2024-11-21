import {
    click,
    contains,
    defineMailModels,
    insertText,
    mockGetMedia,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockUserAgent } from "@odoo/hoot-mock";
import { mockService } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("no default rtc after joining a chat conversation", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebar [title='Start a conversation']");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await insertText(".o-discuss-ChannelSelector input", "mario");
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-discuss-ChannelSelector-suggestion", { count: 0 });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-Discuss-content .o-mail-Message", { count: 0 });
    await contains(".o-discuss-Call", { count: 0 });
});

test("no default rtc after joining a group conversation", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebar [title='Start a conversation']");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await insertText(".o-discuss-ChannelSelector input", "mario");
    await click(".o-discuss-ChannelSelector-suggestion", { text: "Mario" });
    await insertText(".o-discuss-ChannelSelector input", "luigi", { replace: true });
    await click(".o-discuss-ChannelSelector-suggestion", { text: "Luigi" });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-Discuss-content .o-mail-Message", { count: 0 });
    await contains(".o-discuss-Call", { count: 0 });
});

test.tags("mobile")("show Push-to-Talk button on mobile", async () => {
    mockGetMedia();
    mockUserAgent("android");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockService("discuss.ptt_extension", {
        get isEnabled() {
            return false;
        },
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start a Call']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await click("button", { text: "Push to Talk" });
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await contains("button", { text: "Push to talk" });
});
