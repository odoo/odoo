import {
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Settings } from "@mail/core/common/settings_model";
import { CallSettings } from "@mail/discuss/call/common/call_settings";
import { PTT_RELEASE_DURATION } from "@mail/discuss/call/common/rtc_service";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { toRawValue } from "@mail/utils/common/local_storage";
import { advanceTime, describe, expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineMailModels();

const TALKING = ".o-discuss-CallParticipantCard .o-isTalking:count(1)";
const NOT_TALKING = ".o-discuss-CallParticipantCard:not(:has(.o-isTalking)):count(1)";

/**
 * Stand in for the extension on the page side: answer its version, and log as steps the
 * messages the page sends to it. Must be called before `start`, as the plugin asks the version
 * when it starts.
 */
function mockPttExtension() {
    patch(window, {
        chrome: {
            runtime: {
                async sendMessage(extId, { type, value }) {
                    if (type === "ask-version") {
                        return "1.0.0.2";
                    }
                    expect.step(value === undefined ? type : `${type}: ${value}`);
                },
            },
        },
    });
}

/** @param {"answer-is-enabled" | "push-to-talk-pressed" | "toggle-voice"} type */
function sendFromPttExtension(type) {
    window.dispatchEvent(
        new MessageEvent("message", {
            data: { from: "discuss-push-to-talk", type },
            origin: location.origin,
            source: window,
        })
    );
}

function enablePushToTalk() {
    localStorage.setItem(
        makeRecordFieldLocalId(Settings.localId(), "usePushToTalk"),
        toRawValue(true)
    );
}

async function openChannel() {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await expect.waitForSteps(["ask-is-enabled"]);
}

async function startCall() {
    await contains("[title='Start Call']").click();
    await waitFor(NOT_TALKING);
}

test("only asks whether the extension is enabled until it answers", async () => {
    mockPttExtension();
    enablePushToTalk();
    await openChannel();
    await startCall();
    sendFromPttExtension("push-to-talk-pressed");
    await waitFor(TALKING);
    expect.verifySteps([]);
});

test("hides the extension ad once the extension answers", async () => {
    mockPttExtension();
    enablePushToTalk();
    const env = await start();
    await mountWithCleanup(CallSettings, { env, props: { withActionPanel: false } });
    await expect.waitForSteps(["ask-is-enabled"]);
    await waitFor(".alert-warning:contains('Push-to-Talk works only while this tab is in focus')");
    sendFromPttExtension("answer-is-enabled");
    await waitForNone(".alert-warning");
});

test("push-to-talk from the extension", async () => {
    mockPttExtension();
    enablePushToTalk();
    await openChannel();
    sendFromPttExtension("answer-is-enabled");
    await startCall();
    await expect.waitForSteps(["subscribe"]);
    sendFromPttExtension("push-to-talk-pressed");
    await waitFor(TALKING);
    await expect.waitForSteps(["is-talking: true"]);
    // the first press waits longer for the key repeat (750ms) than the following ones (200ms)
    await advanceTime(700);
    await waitFor(TALKING);
    sendFromPttExtension("push-to-talk-pressed");
    await advanceTime(150);
    await waitFor(TALKING);
    expect.verifySteps([]);
    await advanceTime(100);
    await waitFor(NOT_TALKING);
    await expect.waitForSteps(["is-talking: false"]);
    await contains(".o-discuss-CallActionList button[aria-label='Disconnect']").click();
    await expect.waitForSteps(["unsubscribe"]);
});

test("toggle voice from the extension", async () => {
    mockPttExtension();
    enablePushToTalk();
    await openChannel();
    sendFromPttExtension("answer-is-enabled");
    await startCall();
    await expect.waitForSteps(["subscribe"]);
    sendFromPttExtension("toggle-voice");
    await waitFor(TALKING);
    await expect.waitForSteps(["is-talking: true"]);
    // the release of a push-to-talk key is ignored while voice is toggled on
    window.dispatchEvent(new Event("blur"));
    await advanceTime(PTT_RELEASE_DURATION + 1000);
    await waitFor(TALKING);
    sendFromPttExtension("toggle-voice");
    await advanceTime(0);
    await waitFor(NOT_TALKING);
    await expect.waitForSteps(["is-talking: false"]);
});
