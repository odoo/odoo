import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { SuggestionService } from "@mail/core/common/suggestion_service";
import { click, contains, insertText, start } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Visitor cannot use @ mentions in livechat", async () => {
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    patchWithCleanup(SuggestionService.prototype, {
        getSupportedDelimiters() {
            const delimiters = super.getSupportedDelimiters(...arguments);
            expect.step(delimiters.map((d) => d[0]).join(","));
            return delimiters;
        },
    });
    await insertText(".o-mail-Composer-input", "@");
    await expect.waitForSteps(["::,:,/"]);
    await contains(".o-mail-Composer-suggestion", { count: 0 });
});
