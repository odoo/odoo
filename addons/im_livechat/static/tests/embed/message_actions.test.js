<<<<<<< master
import { waitNotifications } from "@bus/../tests/bus_test_helpers";

||||||| cfb34ada1ba9e69a58fbe82954bcfcd49cc81dd6
import { waitNotifications } from "@bus/../tests/bus_test_helpers";

import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
=======
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
>>>>>>> 473fcc00ff817237fab55f12beb2804778b08075
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    insertText,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
<<<<<<< master
import { describe, test } from "@odoo/hoot";
||||||| cfb34ada1ba9e69a58fbe82954bcfcd49cc81dd6
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
=======
import { asyncStep, mountWithCleanup, waitForSteps } from "@web/../tests/web_test_helpers";
>>>>>>> 473fcc00ff817237fab55f12beb2804778b08075

describe.current.tags("desktop");
defineLivechatModels();

test("Only two quick actions are shown", async () => {
    // This is desired because 2 actions share a same icon
    // "Add a reaction" and "View reactions".
    await startServer();
    await loadDefaultEmbedConfig();
    const env = await start({ authenticateAs: false });
<<<<<<< master
||||||| cfb34ada1ba9e69a58fbe82954bcfcd49cc81dd6
    await mountWithCleanup(LivechatButton);
=======
    env.services.bus_service.subscribe("discuss.channel/new_message", () =>
        asyncStep("discuss.channel/new_message")
    );
    await mountWithCleanup(LivechatButton);
>>>>>>> 473fcc00ff817237fab55f12beb2804778b08075
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    // message data from post contains no reaction, wait now to avoid overriding newer value later
    await waitForSteps(["discuss.channel/new_message"]);
    await click("[title='Add a Reaction']");
    await click(".o-mail-QuickReactionMenu button", { text: "😅" });
    await contains(".o-mail-MessageReaction", { text: "😅" });
    await contains(".o-mail-Message-actions i", { count: 3 });
    await contains("[title='Add a Reaction']");
    await contains("[title='Reply']");
    await contains("[title='Expand']");
    await click("[title='Expand']");
    await contains(".o-mail-Message-actions i, .o-mail-Message-moreMenu i", { count: 8 });
    await contains("[title='View Reactions']");
    await contains("[title='Mark as Unread']");
    await contains("[title='Edit']");
    await contains("[title='Delete']");
    await contains("[title='Copy Link']");
});
