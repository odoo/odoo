import { describe, test } from "@odoo/hoot";
import {
    click,
    contains,
    insertText,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { defineLivechatModels, loadDefaultEmbedConfig } from "../livechat_test_helpers";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Only two quick actions are shown", async () => {
    // This is desired because 2 actions share a same icon
    // "Add a reaction" and "View reactions".
    await startServer();
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false, env: { odooEmbedLivechat: true } });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await contains(".o-mail-Message-actions i", { count: 3 });
    await contains("[title='Add a Reaction']");
    await contains("[title='Reply']");
    await contains("[title='Expand']");
    await click("[title='Expand']");
    await contains(".o-mail-Message-actions i, .o-mail-Message-moreMenu i", { count: 6 });
    await contains("[title='Edit']");
    await contains("[title='Delete']");
    await contains("[title='View Reactions']");
});
