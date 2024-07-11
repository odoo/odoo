/* @odoo-module */

import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { registry } from "@web/core/registry";

export class AutopopupService {
    static COOKIE = "im_livechat_auto_popup";

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
            if (livechatService.shouldRestoreSession) {
                threadService.openChat();
            } else if (this.allowAutoPopup) {
                browser.setTimeout(async () => {
                    if (await this.shouldOpenChatWindow()) {
                        cookie.set(AutopopupService.COOKIE, JSON.stringify(false));
                        threadService.openChat();
                    }
                }, livechatService.rule.auto_popup_timer * 1000);
            }
        });
    }

    /**
     * Determines if a chat window should be opened. This is the case if
     * there is an available operator and if no chat window linked to
     * the session exists.
     *
     * @returns {Promise<boolean>}
     */
    async shouldOpenChatWindow() {
        const thread = await this.livechatService.thread;
        return this.storeService.discuss.chatWindows.every((cw) => !cw.thread?.eq(thread));
    }

    get allowAutoPopup() {
        return Boolean(
            JSON.parse(cookie.get(AutopopupService.COOKIE) ?? "true") !== false &&
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
