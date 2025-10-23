import { fields } from "@mail/core/common/record";
import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const discussAppPatch = {
    setup() {
        super.setup(...arguments);
        this.allCategories = fields.Many("DiscussAppCategory", {
            inverse: "app",
            sort: (c1, c2) =>
                c1.sequence !== c2.sequence
                    ? c1.sequence - c2.sequence
                    : c1.name.localeCompare(c2.name),
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
        this.unreadChannels = fields.Many("mail.thread", { inverse: "appAsUnreadChannels" });
    },
    computeChatCategory() {
        return {
            addTitle: _t("Start a conversation"),
            canView: false,
            extraClass: "o-mail-DiscussSidebarCategory-chat",
            icon: "fa fa-users",
            id: "chats",
            name: _t("Direct messages"),
            sequence: 30,
        };
    },
};
patch(DiscussApp.prototype, discussAppPatch);
