import { fields } from "@mail/model/export";
import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const discussAppPatch = {
    setup() {
        super.setup(...arguments);
        this.allCategories = fields.Many("DiscussAppCategory", {
            inverse: "app",
            sort: (c1, c2) => {
                // Favorites category always first
                if (c1.id === "favorites" || c2.id === "favorites") {
                    return c1.id === "favorites" ? -1 : 1;
                }
                // Categories linked to discuss.category come before others
                const c1HasDiscussCategory = !!c1.discussCategoryAsAppCategory;
                const c2HasDiscussCategory = !!c2.discussCategoryAsAppCategory;
                if (c1HasDiscussCategory !== c2HasDiscussCategory) {
                    return c1HasDiscussCategory ? -1 : 1;
                }
                // Finally sort by sequence then name if they are both linked or both not linked to discuss.category
                const c1Sequence = c1.discussCategoryAsAppCategory?.sequence ?? c1.sequence;
                const c2Sequence = c2.discussCategoryAsAppCategory?.sequence ?? c2.sequence;
                return c1Sequence !== c2Sequence
                    ? c1Sequence - c2Sequence
                    : c1.name.localeCompare(c2.name);
            },
        });
        this.channelCategory = fields.One("DiscussAppCategory", {
            compute() {
                return {
                    addTitle: _t("Add or join a channel"),
                    canView: true,
                    extraClass: "o-mail-DiscussSidebarCategory-channel",
                    icon: "fa fa-hashtag",
                    id: "channels",
                    name: _t("Channels"),
                    sequence: 10,
                };
            },
            eager: true,
        });
        this.chatCategory = fields.One("DiscussAppCategory", {
            compute() {
                return this.computeChatCategory();
            },
            eager: true,
        });
        this.favoriteCategory = fields.One("DiscussAppCategory", {
            compute() {
                return {
                    extraClass: "o-mail-DiscussSidebarCategory-favorite",
                    hideWhenEmpty: true,
                    icon: "fa fa-star",
                    id: "favorites",
                    name: _t("Favorites"),
                    sequence: 5,
                };
            },
        });
        this.unreadChannels = fields.Many("discuss.channel", { inverse: "appAsUnreadChannels" });
    },
    computeChatCategory() {
        return {
            addTitle: _t("Start a conversation"),
            canView: false,
            extraClass: "o-mail-DiscussSidebarCategory-chat",
            icon: "oi oi-users",
            id: "chats",
            name: _t("Direct messages"),
            sequence: 30,
        };
    },
};
patch(DiscussApp.prototype, discussAppPatch);
