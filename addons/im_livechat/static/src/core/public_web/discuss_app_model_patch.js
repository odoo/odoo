import { fields } from "@mail/core/common/record";
import { DiscussApp } from "@mail/core/public_web/discuss_app_model";
import { effectWithDebouncedCleanup } from "@mail/utils/common/misc";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

// Looking for help subscription is triggered when the sidebar category is
// opened, and when the discuss app is active. To avoid unsubscribing right away
// when the user closes the sidebar or switches to another app, wait for 5
// minutes before unsubscribing.
export const LFH_UNSUBSCRIBE_DELAY = 5 * 60 * 1000;
export const LIVECHAT_INFO_DEFAULT_OPEN_LS = "im_livechat.isInfoPanelOpenByDefault";

const discussAppStaticPatch = {
    new() {
        /** @type {import("models").DiscussApp} */
        const app = super.new(...arguments);
        effectWithDebouncedCleanup({
            delay: LFH_UNSUBSCRIBE_DELAY,
            dependencies: (app) => ({
                busService: app.store.env.services.bus_service,
                category: app.livechatLookingForHelpCategory,
                store: app.store,
            }),
            effect({ busService, category, store }) {
                busService.addChannel("im_livechat.looking_for_help");
                store.fetchStoreData("/im_livechat/looking_for_help");
                return () => {
                    busService.deleteChannel("im_livechat.looking_for_help");
                    if (!category.exists()) {
                        return;
                    }
                    category.threads
                        .filter((thread) => !thread.self_member_id && !thread.isLocallyPinned)
                        .forEach((thread) => thread.delete());
                };
            },
            predicate: (app) =>
                Boolean(
                    app.exists() &&
                        app.livechatLookingForHelpCategory?.open &&
                        !app.livechatLookingForHelpCategory.hidden &&
                        app.isActive
                ),
            reactiveTargets: [app],
        });
        return app;
    },
};
patch(DiscussApp, discussAppStaticPatch);

patch(DiscussApp.prototype, {
    setup(env) {
        super.setup(...arguments);
        this.defaultLivechatCategory = fields.One("DiscussAppCategory", {
            compute() {
                return {
                    extraClass: "o-mail-DiscussSidebarCategory-livechat",
                    hideWhenEmpty: true,
                    icon: "fa fa-commenting-o",
                    id: `im_livechat.category_default`,
                    name: _t("Livechat"),
                    sequence: 21,
                };
            },
            eager: true,
        });
        this.livechatLookingForHelpCategory = fields.One("DiscussAppCategory", {
            compute() {
                if (!this.store.has_access_livechat) {
                    return null;
                }
                return {
                    extraClass: "o-mail-DiscussSidebarCategory-livechatNeedHelp",
                    icon: "fa fa-exclamation-circle",
                    id: `im_livechat.category_need_help`,
                    name: _t("Looking for help"),
                    sequence: 15,
                };
            },
            eager: true,
        });
        this.lastThread = fields.One("Thread");
        this.livechats = fields.Many("Thread", { inverse: "appAsLivechats" });
        this._recomputeIsLivechatInfoPanelOpenedByDefault = 0;
        this.isLivechatInfoPanelOpenByDefault = fields.Attr(true, {
            compute() {
                void this._recomputeIsLivechatInfoPanelOpenedByDefault;
                return browser.localStorage.getItem(LIVECHAT_INFO_DEFAULT_OPEN_LS) !== "false";
            },
        });
    },

    shouldDisableMemberPanelAutoOpenFromClose(nextActiveAction) {
        if (nextActiveAction?.id === "livechat-info") {
            return false;
        }
        return super.shouldDisableMemberPanelAutoOpenFromClose(...arguments);
    },

    _threadOnUpdate() {
        if (
            this.lastThread?.notEq(this.thread) &&
            (this.lastThread.livechat_status === "need_help" || this.lastThread.unpinOnThreadSwitch)
        ) {
            this.lastThread.isLocallyPinned = false;
        }
        if (this.thread?.livechat_status === "need_help" && !this.thread.self_member_id) {
            this.thread.isLocallyPinned = true;
        }
        this.lastThread = this.thread;
        super._threadOnUpdate();
    },

    onStorage(ev) {
        super.onStorage(ev);
        if (ev.key === LIVECHAT_INFO_DEFAULT_OPEN_LS) {
            this._recomputeIsLivechatInfoPanelOpenedByDefault++;
        }
    },
});
