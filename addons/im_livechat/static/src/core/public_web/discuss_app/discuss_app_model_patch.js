import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";
import { fields } from "@mail/model/export";
import { effectWithDebouncedCleanup } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

// Looking for help subscription is triggered when the sidebar category is
// opened, and when the discuss app is active. To avoid unsubscribing right away
// when the user closes the sidebar or switches to another app, wait for 5
// minutes before unsubscribing.
export const LFH_UNSUBSCRIBE_DELAY = 5 * 60 * 1000;

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
                    category.channels
                        .filter((channel) => !channel.self_member_id && !channel.isLocallyPinned)
                        .forEach((channel) => channel.delete());
                };
            },
            predicate: (app) =>
                Boolean(
                    app.exists() &&
                        app.livechatLookingForHelpCategory?.is_open &&
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
        this.lastThread = fields.One("mail.thread");
        this.livechats = fields.Many("discuss.channel", { inverse: "appAsLivechats" });
    },

    _threadOnUpdate() {
        if (
            this.lastThread?.notEq(this.thread) &&
            (this.lastThread.channel?.livechat_status === "need_help" ||
                this.lastThread.channel?.unpinOnThreadSwitch)
        ) {
            this.lastThread.isLocallyPinned = false;
        }
        if (this.thread?.channel?.livechat_status === "need_help" && !this.thread.self_member_id) {
            this.thread.isLocallyPinned = true;
        }
        this.lastThread = this.thread;
        super._threadOnUpdate();
    },
});
