import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import {
    assertSteps,
    click,
    contains,
    insertText,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { getService, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Handle livechat history command", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    onRpc("/im_livechat/history", () => {
        step("/im_livechat/history");
        return true;
    });
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { count: 2 });
    const thread = getService("im_livechat.livechat").thread;
    const guestId = pyEnv.cookie.get("dgid");
    const [guest] = pyEnv["mail.guest"].read(guestId);
    pyEnv["bus.bus"]._sendone(guest, "im_livechat.history_command", {
        id: thread.id,
    });
    await tick();
    await assertSteps(["/im_livechat/history"]);
});
