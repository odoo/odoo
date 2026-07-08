import { waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";

import {
    click,
    contains,
    defineMailModels,
    insertText,
    mockGetMedia,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { Settings } from "@mail/core/common/settings_model";
import { pttExtensionServiceInternal } from "@mail/discuss/call/common/ptt_extension_service";
import { PTT_RELEASE_DURATION } from "@mail/discuss/call/common/rtc_service";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { toRawValue } from "@mail/utils/common/local_storage";
import { advanceTime, freezeTime, keyDown, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

defineMailModels();

test.tags("desktop");
test("no auto-call on joining chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openDiscuss();
    await triggerHotkey("control+k");
    await contains(".o_command_name", { count: 2 });
    await insertText(
        ".o_command_palette_search input[placeholder='Search conversations']",
        "mario"
    );
    await contains(".o_command_name", { count: 2 });
    await click(".o_command_name:text('Mario')");
    await contains(".o-mail-MessagingMenuItem:has(:text('Mario'))");
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
    await triggerHotkey("control+k");
    await click(".o_command_name:text(Mario)");
    await contains(".o-mail-DiscussContent-threadName[title='Mario']");
    await click("[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text(Luigi))");
    await click("button:text('Create Group Chat')");
    await contains(".o-mail-MessagingMenuItem:has(:text('Mitchell Admin, Mario, and Luigi'))");
    await contains(".o-mail-Message", { count: 0 });
    await contains(".o-discuss-Call", { count: 0 });
});

test.tags("desktop");
test("Can push-to-talk", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    localStorage.setItem(
        makeRecordFieldLocalId(Settings.localId(), "usePushToTalk"),
        toRawValue(true)
    );
    localStorage.setItem(
        makeRecordFieldLocalId(Settings.localId(), "pushToTalkKey"),
        toRawValue("...f")
    );
    patchWithCleanup(pttExtensionServiceInternal, {
        onAnswerIsEnabled(pttService) {
            pttService.isEnabled = false;
        },
    });
    freezeTime();
    // Time is frozen, so the websocket subscription cannot complete on its own.
    // The worker connection handshake reschedules a timer on each step and the
    // subscribe is debounced, so advance in small steps to flush it, then await
    // it before driving the call so the rest of the test does not race it.
    let isSubscribed = false;
    const subscribed = waitUntilSubscribe().then(() => (isSubscribed = true));
    await start({ waitUntilSubscribe: false });
    await openDiscuss(channelId);
    while (!isSubscribed) {
        await advanceTime(100);
    }
    await subscribed;
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
