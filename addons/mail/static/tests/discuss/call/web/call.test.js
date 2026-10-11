import { waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";

import {
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
import { advanceTime, freezeTime, keyDown, test, waitFor, waitForNone } from "@odoo/hoot";
import { patch } from "@web/core/utils/patch";
import { contains } from "@web/../tests/web_test_helpers";

defineMailModels();

test.tags("desktop");
test("no auto-call on joining chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openDiscuss();
    await triggerHotkey("control+k");
    await waitFor(".o_command_name:count(2)");
    await insertText(
        ".o_command_palette_search input[placeholder='Search conversations']",
        "mario"
    );
    await waitFor(".o_command_name:count(2)");
    await contains(".o_command_name:text('Mario'):count(1)").click();
    await waitFor(".o-mail-MessagingMenuItem:has(:text('Mario')):count(1)");
    await waitForNone(".o-mail-Message");
    await waitForNone(".o-discuss-Call");
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
    await contains(".o_command_name:text(Mario):count(1)").click();
    await waitFor(".o-mail-DiscussContent-threadName[title='Mario']:count(1)");
    await contains("[title='Invite People']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:has(:text(Luigi)):count(1)").click();
    await contains("button:text('Create Group Chat'):count(1)").click();
    await waitFor(
        ".o-mail-MessagingMenuItem:has(:text('Mitchell Admin, Mario, and Luigi')):count(1)"
    );
    await waitForNone(".o-mail-Message");
    await waitForNone(".o-discuss-Call");
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
    patch(pttExtensionServiceInternal, {
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
    await contains("[title='Start Call']:count(1)").click();
    await advanceTime(1000);
    await waitFor(".o-discuss-Call:count(1)");
    await contains(".o-discuss-Call:count(1)").click();
    await advanceTime(1000);
    await keyDown("f");
    await advanceTime(PTT_RELEASE_DURATION);
    await waitFor(".o-discuss-CallParticipantCard .o-isTalking:count(1)");
    // switching tab while PTT key still pressed then released on other tab should eventually release PTT
    window.dispatchEvent(new Event("blur"));
    await advanceTime(PTT_RELEASE_DURATION + 1000);
    await waitFor(".o-discuss-CallParticipantCard:not(:has(.o-isTalking)):count(1)");
    await contains(".o-discuss-Call:count(1)").click();
    await advanceTime(1000);
    await keyDown("f");
    await advanceTime(PTT_RELEASE_DURATION);
    await waitFor(".o-discuss-CallParticipantCard .o-isTalking:count(1)");
});
