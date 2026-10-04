import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { click, contains, insertText, start, startServer } from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";

import { serverState } from "@web/../tests/web_test_helpers";
import { location } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineLivechatModels();

test("portal user can open a live chat conversation in Discuss", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const portalUserId = pyEnv["res.users"].create({
        name: "Joel",
        share: true,
        login: "joel",
        password: "joel",
    });
    const portalPartnerId = pyEnv["res.partner"].create({
        name: "Joel",
        user_ids: [portalUserId],
    });
    pyEnv["res.partner"].write(serverState.partnerId, {
        user_livechat_username: "MitchellOp",
    });

    await start({
        authenticateAs: { login: "joel", password: "joel" },
        waitUntilSubscribe: false,
    });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input:enabled", "Hello!");
    await click(".o-mail-Composer button[aria-label='Send']:enabled");
    await contains(
        ".o-mail-Thread:not([data-transient]) .o-mail-Message[data-persistent]:contains('Hello!')"
    );
    const [channelId] = pyEnv["discuss.channel"].search([
        ["channel_type", "=", "livechat"],
        [
            "channel_member_ids",
            "in",
            pyEnv["discuss.channel.member"].search([
                ["partner_id", "=", portalPartnerId],
            ]),
        ],
    ]);
    patch(location, {
        assign(targetUrl) {
            expect(new URL(targetUrl).pathname).toBe(`/discuss/channel/${channelId}`);
            expect.step("redirect to public Discuss");
        },
    });
    await click(".o-mail-ChatWindow-header button[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Open in Discuss')");
    expect.verifySteps(["redirect to public Discuss"]);
});
