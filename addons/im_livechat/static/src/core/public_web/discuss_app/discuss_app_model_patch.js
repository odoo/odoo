import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";
import { fields } from "@mail/model/export";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { effectWithCleanup } from "@mail/utils/common/misc";

// Looking for help subscription is triggered when the sidebar category is
// opened, and when the discuss app is active. To avoid unsubscribing right away
// when the user closes the sidebar or switches to another app, wait for 5
// minutes before unsubscribing.
export const LFH_UNSUBSCRIBE_DELAY = 5 * 60 * 1000;

const DISPOSE_EFFECT_TIMEOUT_SYM = Symbol("DISPOSE_EFFECT_TIMEOUT");
const DISPOSE_EFFECT_SYM = Symbol("DISPOSE_EFFECT");

const discussAppStaticPatch = {
    new() {
        /** @type {import("models").DiscussApp} */
        const app = super.new(...arguments);
        app[DISPOSE_EFFECT_SYM] = effectWithCleanup(() => {
            const busService = app.store.env.services.bus_service;
            const category = app.livechatLookingForHelpCategory;
            const store = app.store;
            if (
                !app.exists() ||
                !app.livechatLookingForHelpCategory?.is_open ||
                app.livechatLookingForHelpCategory.hidden ||
                !app.isActive
            ) {
                return;
            }
            clearTimeout(app[DISPOSE_EFFECT_TIMEOUT_SYM]);
            if (!app.isSubscribedToLookingForHelp) {
                busService.addChannel("im_livechat.looking_for_help");
                store.fetchStoreData("/im_livechat/looking_for_help");
                app.isSubscribedToLookingForHelp = true;
            }
            return () => {
                app[DISPOSE_EFFECT_TIMEOUT_SYM] = setTimeout(() => {
                    app.isSubscribedToLookingForHelp = false;
                    busService.deleteChannel("im_livechat.looking_for_help");
                    if (!category.exists()) {
                        return;
                    }
                    category.channels
                        .filter((channel) => !channel.self_member_id && !channel.isLocallyPinned)
                        .forEach((channel) => channel.delete());
                }, LFH_UNSUBSCRIBE_DELAY);
            };
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
                    name: _t("Live Chat"),
                    sequence: 17,
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
        this.lastThread = fields.One("mail.thread");
        this.livechats = fields.Many("discuss.channel", { inverse: "appAsLivechats" });
        this.isLivechatInfoPanelOpenByDefault = fields.Attr(true, { localStorage: true });
    },
    delete(...args) {
        this[DISPOSE_EFFECT_SYM]();
        super.delete(...args);
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
            (this.lastThread.channel?.livechat_status === "need_help" ||
                this.lastThread.channel?.unpinOnThreadSwitch)
        ) {
            this.lastThread.channel.isLocallyPinned = false;
        }
        if (
            this.thread?.channel?.livechat_status === "need_help" &&
            !this.thread.channel?.self_member_id
        ) {
            this.thread.channel.isLocallyPinned = true;
        }
        this.lastThread = this.thread;
        super._threadOnUpdate();
    },
});
