import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { click, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { press, waitFor } from "@odoo/hoot-dom";
import { contains, getService, onRpc, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Handle livechat history command", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    onRpc("/im_livechat/history", ({ url }) => {
        expect.step(new URL(url).pathname);
        return true;
    });
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Composer-input").edit("Hello World!", { confirm: false });
    await press("Enter");
    await waitFor(".o-mail-Message:contains(Hello World!)");
    const thread = Object.values(getService("mail.store")["mail.thread"].records).at(-1);
    const guestId = pyEnv.cookie.get("dgid");
    const [guest] = pyEnv["mail.guest"].read(guestId);
    pyEnv["bus.bus"]._sendone(guest, "im_livechat.history_command", {
        id: thread.id,
        partner_id: serverState.partnerId,
    });
    await expect.waitForSteps(["/im_livechat/history"]);
});
