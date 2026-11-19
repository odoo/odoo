import {
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { containsTextInComposer } from "@mail/../tests/mail_test_helpers_composer";
import { LONG_PRESS_DELAY } from "@mail/utils/common/hooks";

import { advanceTime, describe, test } from "@odoo/hoot";
import { pointerDown, pointerUp, waitFor } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

class MockSpeechRecognition {
    /** @type {MockSpeechRecognition} */
    static current;

    /** @param {[transcript: string, isFinal: boolean][]} results */
    emit(results) {
        this.onresult({
            results: results.map(([transcript, isFinal]) =>
                Object.assign([{ transcript }], { isFinal })
            ),
        });
    }

    start() {
        MockSpeechRecognition.current = this;
    }

    stop() {
        this.onend();
    }
}

test("holding the voice button writes the speech in the composer as it is said", async () => {
    patchWithCleanup(window, { SpeechRecognition: MockSpeechRecognition });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-html:focus");
    await pointerDown(".o-mail-Composer button[title='Voice Message']");
    await advanceTime(LONG_PRESS_DELAY);
    await waitFor(".o-mail-Composer-inputContainer.o-dictating:count(1)");
    MockSpeechRecognition.current.emit([["Hello", false]]);
    await containsTextInComposer(".o-mail-Composer", "Hello");
    MockSpeechRecognition.current.emit([["Hello world", true]]);
    await containsTextInComposer(".o-mail-Composer", "Hello world");
    await pointerUp(".o-mail-Composer button[title='Voice Message']");
    await waitFor(".o-mail-Composer-inputContainer:not(.o-dictating):count(1)");
    await containsTextInComposer(".o-mail-Composer", "Hello world");
    // the release is not a click that records a voice message
    await waitFor(".o-mail-Composer button[title='Send']:enabled:count(1)");
});
