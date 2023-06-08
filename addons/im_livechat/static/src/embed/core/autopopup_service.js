/* @odoo-module */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export class AutopopupService {
    static COOKIE = "im_livechat_auto_popup";

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * "im_livechat.chatbot": import("@im_livechat/embed/chatbot/chatbot_service").ChatBotService,
     * "im_livechat.livechat": import("@im_livechat/embed/core/livechat_service").LivechatService,
     * "mail.thread": import("@mail/core/common/thread_service").ThreadService,
     * "mail.store": import("@mail/core/common/store_service").Store,
     * cookie: typeof import("@web/core/browser/cookie_service").cookieService.start,
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
            cookie,
        }
    ) {
        this.threadService = threadService;
        this.storeService = storeService;
        this.livechatService = livechatService;
        this.chatbotService = chatbotService;
        this.cookie = cookie;
        this.ui = ui;

        livechatService.initializedDeferred.then(() => {
            if (livechatService.shouldRestoreSession) {
                threadService.openChat();
            } else if (this.allowAutoPopup) {
                browser.setTimeout(async () => {
                    if (await this.shouldOpenChatWindow()) {
                        this.cookie.setCookie(AutopopupService.COOKIE, JSON.stringify(false));
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
        const thread = await this.threadService.getLivechatThread();
        return this.storeService.chatWindows.every(
            (chatWindow) => chatWindow.thread.localId !== thread?.localId
        );
    }

    get allowAutoPopup() {
        return Boolean(
            JSON.parse(this.cookie.current[AutopopupService.COOKIE] ?? "true") !== false &&
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
        "cookie",
        "ui",
    ],

    start(env, services) {
        return new AutopopupService(env, services);
    },
};
registry.category("services").add("im_livechat.autopopup", autoPopupService);
