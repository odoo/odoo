import { expirableStorage } from "@im_livechat/core/common/expirable_storage";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export class AutopopupService {
    static STORAGE_KEY = "im_livechat_auto_popup";

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * "im_livechat.livechat": import("@im_livechat/embed/common/livechat_service").LivechatService,
     * "mail.store": import("@mail/core/common/store_service").Store,
     * ui: typeof import("@web/core/ui/ui_service").uiService.start,
     * }} services
     */
    constructor(env, { "im_livechat.livechat": livechatService, "mail.store": store, ui }) {
        this.store = store;
        this.livechatService = livechatService;
        this.ui = ui;

        store.isReady.then(() => {
            browser.setTimeout(async () => {
                await store.chatHub.initPromise;
                if (this.allowAutoPopup) {
                    expirableStorage.setItem(AutopopupService.STORAGE_KEY, true);
                    livechatService.open();
                }
            }, store.livechat_rule?.auto_popup_timer * 1000);
        });
    }

    get allowAutoPopup() {
        return Boolean(
            !expirableStorage.getItem(AutopopupService.STORAGE_KEY) &&
                !this.ui.isSmall &&
                this.store.livechat_rule?.action === "auto_popup" &&
                this.store.livechat_available &&
                this.store.activeLivechats.length === 0
        );
    }
}

export const autoPopupService = {
    dependencies: ["im_livechat.livechat", "mail.store", "ui"],

    start(env, services) {
        return new AutopopupService(env, services);
    },
};
registry.category("services").add("im_livechat.autopopup", autoPopupService);
