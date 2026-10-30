import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { click, contains, start } from "@mail/../tests/mail_test_helpers";
import {
    insertTextInComposer,
    waitForComposerEditor,
} from "@mail/../tests/mail_test_helpers_composer";
import { describe, expect, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineLivechatModels();

test("Visitor cannot use @ mentions in livechat", async () => {
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    const editor = await waitForComposerEditor(".o-mail-Composer");
    expect(
        editor.shared.suggestion
            .getSources()
            .map(({ delimiter }) => delimiter)
            .sort()
    ).toEqual(["/", "::"]);
    await insertTextInComposer(".o-mail-Composer", "@");
    await contains(".o-mail-Composer-suggestion", { count: 0 });
});
