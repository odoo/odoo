import { waitNotifications } from "@bus/../tests/bus_test_helpers";

import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { describe, test } from "@odoo/hoot";
import {
    click,
    contains,
    insertText,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Only two quick actions are shown", async () => {
    // This is desired because 2 actions share a same icon
    // "Add a reaction" and "View reactions".
    await startServer();
    await loadDefaultEmbedConfig();
    const env = await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    // message data from post contains no reaction, wait now to avoid overriding newer value later
    await waitNotifications([env, "discuss.channel/new_message"]);
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await contains(".o-mail-MessageReaction", { text: "😅" });
    await contains(".o-mail-Message-actions i", { count: 3 });
    await contains("[title='Add a Reaction']");
    await contains("[title='Reply']");
    await contains("[title='Expand']");
    await click("[title='Expand']");
    await contains(".o-mail-Message-actions i, .o-mail-Message-moreMenu i", { count: 7 });
    await contains("[title='Copy Message Link']");
    await contains("[title='Edit']");
    await contains("[title='Delete']");
    await contains("[title='View Reactions']");
});
