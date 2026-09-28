import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { SuggestionService } from "@mail/core/common/suggestion_service";
import { click, contains, start } from "@mail/../tests/mail_test_helpers";
import { insertTextInComposer } from "@mail/../tests/mail_test_helpers_composer";
import { describe, expect, test } from "@odoo/hoot";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineLivechatModels();

test("Visitor cannot use @ mentions in livechat", async () => {
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    patch(SuggestionService.prototype, {
        getSupportedDelimiters() {
            const delimiters = super.getSupportedDelimiters(...arguments);
            expect.step(delimiters.map((d) => d[0]).join(","));
            return delimiters;
        },
    });
    await insertTextInComposer(".o-mail-Composer", "@");
    // detected on both selection change and content change
    await expect.waitForSteps(["::,/", "::,/"]);
    await contains(".o-mail-Composer-suggestion", { count: 0 });
});
