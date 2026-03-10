import { DiscussSidebarCategory } from "@mail/discuss/core/public_web/discuss_app/sidebar/category";
import { DiscussSidebarChannel } from "@mail/discuss/core/public_web/discuss_app/sidebar/channel";

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/** @type {DiscussSidebarCategory} */
const DiscussSidebarCategoryPatch = {
    setup() {
        super.setup();
        this.actionService = useService("action");
    },
    get actions() {
        const actions = super.actions;
        if (this.category.id === "im_livechat.category_default" && this.store.has_access_livechat) {
            actions.push({
                onSelect: () =>
                    this.actionService.doAction("im_livechat.im_livechat_channel_action"),
                label: _t("View or join live chat channels"),
                icon: "fa fa-cog",
            });
        }
        return actions;
    },
    get isToggleFoldDisabled() {
        return this.category.eq(this.store.discuss.livechatLookingForHelpCategory)
            ? false
            : super.isToggleFoldDisabled;
    },
};

/** @type {DiscussSidebarChannel} */
const DiscussSidebarChannelPatch = {
    get attClassContainer() {
        return {
            ...super.attClassContainer,
            "bg-100": this.channel.livechat_end_dt,
        };
    },
    get itemNameAttClass() {
        return {
            ...super.itemNameAttClass,
            "fst-italic text-muted fw-normal": this.channel.livechat_end_dt,
        };
    },
    get threadAvatarAttClass() {
        return {
            ...super.threadAvatarAttClass,
            "o-opacity-65": this.channel.livechat_end_dt,
        };
    },
};

patch(DiscussSidebarCategory.prototype, DiscussSidebarCategoryPatch);
patch(DiscussSidebarChannel.prototype, DiscussSidebarChannelPatch);
