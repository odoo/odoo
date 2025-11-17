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
import { pttExtensionServiceInternal } from "@mail/discuss/call/common/ptt_extension_service";
import { PTT_RELEASE_DURATION } from "@mail/discuss/call/common/rtc_service";
import { advanceTime, freezeTime, keyDown, mockTouch, mockUserAgent, test } from "@odoo/hoot";
import { patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

defineMailModels();

test.tags("desktop");
test("no auto-call on joining chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openDiscuss();
    await click("input[placeholder='Search conversations']");
    await contains(".o_command_name", { count: 5 });
    await insertText("input[placeholder='Search a conversation']", "mario");
    await contains(".o_command_name", { count: 3 });
    await click(".o_command_name", { text: "Mario" });
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
test("show Push-to-Talk button on mobile", async () => {
    mockGetMedia();
    mockTouch(true);
    mockUserAgent("android");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    patchWithCleanup(pttExtensionServiceInternal, {
        onAnswerIsEnabled(pttService) {
            pttService.isEnabled = false;
        },
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-ChatWindow-moreActions", { text: "General" });
    await click(".o-dropdown-item:text('Start Call')");
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

test.tags("desktop");
test("Can push-to-talk", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["res.users.settings"].create({
        use_push_to_talk: true,
        user_id: serverState.userId,
        push_to_talk_key: "...f",
    });
    patchWithCleanup(pttExtensionServiceInternal, {
        onAnswerIsEnabled(pttService) {
            pttService.isEnabled = false;
        },
    });
    freezeTime();
    await start();
    await openDiscuss(channelId);
    await advanceTime(1000);
    await click("[title='Start Call']");
    await advanceTime(1000);
    await contains(".o-discuss-Call");
    await click(".o-discuss-Call");
    await advanceTime(1000);
    await keyDown("f");
    await advanceTime(PTT_RELEASE_DURATION);
    await contains(".o-discuss-CallParticipantCard .o-isTalking");
    // switching tab while PTT key still pressed then released on other tab should eventually release PTT
    browser.dispatchEvent(new Event("blur"));
    await advanceTime(PTT_RELEASE_DURATION + 1000);
    await contains(".o-discuss-CallParticipantCard:not(:has(.o-isTalking))");
    await click(".o-discuss-Call");
    await advanceTime(1000);
    await keyDown("f");
    await advanceTime(PTT_RELEASE_DURATION);
    await contains(".o-discuss-CallParticipantCard .o-isTalking");
});
