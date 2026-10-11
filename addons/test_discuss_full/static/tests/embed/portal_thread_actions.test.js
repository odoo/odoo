import { loadDefaultEmbedConfig } from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    patchUiSize,
    setupChatHub,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { defineTestDiscussFullModels } from "@test_discuss_full/../tests/test_discuss_full_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";

import { Command, serverState } from "@web/../tests/web_test_helpers";
import { location } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineTestDiscussFullModels();

async function checkOpenLivechatInDiscuss({ mobile = false } = {}) {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    if (mobile) {
        await patchUiSize({ size: SIZES.SM });
    }
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
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ partner_id: portalPartnerId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
    });
    patch(location, {
        assign(targetUrl) {
            expect(new URL(targetUrl).pathname).toBe(`/discuss/channel/${channelId}`);
            expect.step("redirect to public Discuss");
        },
    });
    setupChatHub({ opened: [channelId] });

    await start({
        authenticateAs: { login: "joel", password: "joel" },
        waitUntilSubscribe: false,
    });
    await waitFor(".o-mail-ChatWindow .o-mail-Thread:not([data-transient])");
    await click(".o-mail-ChatWindow-header button[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Open in Discuss')");
    expect.verifySteps(["redirect to public Discuss"]);
}

test("portal user can open a live chat conversation in Discuss", async () => {
    await checkOpenLivechatInDiscuss();
});

test("portal user can open a live chat conversation in Discuss on mobile", async () => {
    await checkOpenLivechatInDiscuss({ mobile: true });
});
