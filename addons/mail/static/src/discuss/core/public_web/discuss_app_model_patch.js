import { Record } from "@mail/core/common/record";
import { DiscussApp } from "@mail/core/public_web/discuss_app_model";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const discussAppPatch = {
    setup() {
        super.setup(...arguments);
        this.allCategories = Record.many("DiscussAppCategory", {
            inverse: "app",
            sort: (c1, c2) =>
                c1.sequence !== c2.sequence
                    ? c1.sequence - c2.sequence
                    : c1.name.localeCompare(c2.name),
        });
        this.channels = Record.one("DiscussAppCategory", {
            compute() {
                return {
                    addTitle: _t("Add or join a channel"),
                    canView: true,
                    extraClass: "o-mail-DiscussSidebarCategory-channel",
                    icon: "fa fa-hashtag",
                    id: "channels",
                    name: _t("Channels"),
                    sequence: 10,
                    serverStateKey: "is_discuss_sidebar_category_channel_open",
                };
            },
            eager: true,
        });
        this.chats = Record.one("DiscussAppCategory", {
            compute() {
                return this.computeChats();
            },
            eager: true,
        });
    },
    computeChats() {
        return {
            addTitle: _t("Start a conversation"),
            canView: false,
            extraClass: "o-mail-DiscussSidebarCategory-chat",
            icon: "fa fa-users",
            id: "chats",
            name: _t("Direct messages"),
            sequence: 30,
            serverStateKey: "is_discuss_sidebar_category_chat_open",
        };
    },
};
patch(DiscussApp.prototype, discussAppPatch);
