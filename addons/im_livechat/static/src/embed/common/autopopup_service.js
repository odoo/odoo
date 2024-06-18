/* @odoo-module */

import { expirableStorage } from "@im_livechat/embed/common/expirable_storage";
import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export class AutopopupService {
    static STORAGE_KEY = "im_livechat_auto_popup";

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * "im_livechat.chatbot": import("@im_livechat/embed/common/chatbot/chatbot_service").ChatBotService,
     * "im_livechat.livechat": import("@im_livechat/embed/common/livechat_service").LivechatService,
     * "mail.thread": import("@mail/core/common/thread_service").ThreadService,
     * "mail.store": import("@mail/core/common/store_service").Store,
     * ui: typeof import("@web/core/ui/ui_service").uiService.start,
     * }} services
     */
    constructor(
        env,
        {
            "im_livechat.chatbot": chatbotService,
            "im_livechat.livechat": livechatService,
            "mail.thread": threadService,
            "mail.store": storeService,
            ui,
        }
    ) {
        this.threadService = threadService;
        this.storeService = storeService;
        this.livechatService = livechatService;
        this.chatbotService = chatbotService;
        this.ui = ui;

        livechatService.initializedDeferred.then(() => {
            if (this.allowAutoPopup && livechatService.state === SESSION_STATE.NONE) {
                browser.setTimeout(async () => {
                    if (!this.storeService.ChatWindow.get({ thread: livechatService.thread })) {
                        expirableStorage.setItem(AutopopupService.STORAGE_KEY, false);
                        livechatService.open();
                    }
                }, livechatService.rule.auto_popup_timer * 1000);
            }
        });
    }

    get allowAutoPopup() {
        return Boolean(
            !expirableStorage.getItem(AutopopupService.STORAGE_KEY) &&
                !this.ui.isSmall &&
                this.livechatService.rule?.action === "auto_popup" &&
                (this.livechatService.available || this.chatbotService.available)
        );
    }
}

export const autoPopupService = {
    dependencies: [
        "im_livechat.livechat",
        "im_livechat.chatbot",
        "mail.thread",
        "mail.store",
        "ui",
    ],

    start(env, services) {
        return new AutopopupService(env, services);
    },
};
registry.category("services").add("im_livechat.autopopup", autoPopupService);
