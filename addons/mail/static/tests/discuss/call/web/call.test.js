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
} from "@mail/../tests/mail_test_helpers";
import { test } from "@odoo/hoot";
import { mockService } from "@web/../tests/web_test_helpers";

defineMailModels();

test.tags("desktop");
test("no auto-call on joining chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openDiscuss();
    await click("input[placeholder='Search conversations']");
    await insertText("input[placeholder='Search a conversation']", "mario");
    await click("a", { text: "mario" });
    await contains(".o-mail-DiscussSidebar-item", { text: "Mario" });
    await contains(".o-mail-Message", { count: 0 });
    await contains(".o-discuss-Call", { count: 0 });
});

test.tags("desktop");
test("no auto-call on joining group chat", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    await start();
    await openDiscuss();
    await click("input[placeholder='Search conversations']");
    await click("a", { text: "Create Chat" });
    await click("li", { text: "Mario" });
    await click("li", { text: "Luigi" });
    await click("button", { text: "Create Group Chat" });
    await contains(".o-mail-DiscussSidebar-item:contains('Mario, and Luigi')");
    await contains(".o-mail-Message", { count: 0 });
    await contains(".o-discuss-Call", { count: 0 });
});

test.tags("mobile");
test.skip("show Push-to-Talk button on mobile", async () => {
    mockGetMedia();
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
    await click("[title='Start Call']");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await click("button", { text: "Push to Talk" });
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await contains("button", { text: "Push to talk" });
});
