import { describe, test } from "@odoo/hoot";
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
import { tick } from "@odoo/hoot-mock";
import { defineLivechatModels, loadDefaultEmbedConfig } from "../livechat_test_helpers";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";

describe.current.tags("desktop");
defineLivechatModels();

test("Handle livechat history command", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    onRpc("/im_livechat/history", () => {
        step("/im_livechat/history");
        return true;
    });
    const env = await start({ authenticateAs: false, env: { odooEmbedLivechat: true } });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { count: 2 });
    const thread = env.services["im_livechat.livechat"].thread;
    const guestId = pyEnv.cookie.get("dgid");
    const [guest] = pyEnv["mail.guest"].read(guestId);
    pyEnv["bus.bus"]._sendone(guest, "im_livechat.history_command", {
        id: thread.id,
    });
    await tick();
    await assertSteps(["/im_livechat/history"]);
});
