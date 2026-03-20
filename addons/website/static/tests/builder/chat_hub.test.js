import {
    contains,
    defineMailModels,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { ChatHub } from "@mail/core/common/chat_hub";
import { CHAT_HUB_DEFAULT_BUBBLE_START } from "@mail/core/common/chat_hub_model";
import { animationFrame, describe, expect, queryFirst, test } from "@odoo/hoot";
import { onRendered } from "@odoo/owl";
import { getService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CHAT_HUB_WE_SIDEBAR_WIDTH } from "@website/mail/core/common/chat_hub_model_patch";

describe.current.tags("desktop");
defineMailModels();

test("chat hub offsets when website in edition mode", async () => {
    // As to not overlap the website editor panel
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Orange",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    setupChatHub({ opened: [channelId] });
    patchWithCleanup(ChatHub.prototype, {
        setup() {
            super.setup();
            onRendered(() => {
                const rootEl = this.root.el;
                if (!rootEl) {
                    return;
                }
                if (this.isWebsiteEdition) {
                    rootEl.dataset.isWebsiteEdition = this.isWebsiteEdition;
                } else {
                    delete rootEl.dataset.isWebsiteEdition;
                }
            });
        },
    });
    await start();
    await contains(".o-mail-ChatWindow");
    const xOffset_1 = queryFirst(".o-mail-ChatWindow").getBoundingClientRect().x;
    // simulate website edition mode on
    getService("website").context.edition = true;
    await contains(".o-mail-ChatHub[data-is-website-edition]");
    await animationFrame();
    const xOffset_2 = queryFirst(".o-mail-ChatWindow").getBoundingClientRect().x;
    expect(xOffset_2).toBe(xOffset_1 - CHAT_HUB_WE_SIDEBAR_WIDTH + CHAT_HUB_DEFAULT_BUBBLE_START);
});
