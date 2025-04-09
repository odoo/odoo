import { DiscussSidebarCategory } from "@mail/discuss/core/public_web/discuss_sidebar_categories";
import { patch } from "@web/core/utils/patch";

/** @type {import("@mail/discuss/core/public_web/discuss_sidebar_categories").DiscussSidebarCategory} */
const DiscussSidebarCategoryPatch = {
    get actions() {
        const actions = super.actions;
        if (
            this.store.has_access_livechat &&
            this.category.livechat_channel_id &&
            this.category.open
        ) {
            actions.push({
                onSelect: () => {
                    if (this.category.livechat_channel_id.are_you_inside) {
                        this.category.livechat_channel_id.leave({ notify: false });
                    } else {
                        this.category.livechat_channel_id.join({ notify: false });
                    }
                },
                label: this.category.livechat_channel_id.are_you_inside
                    ? this.category.livechat_channel_id.leaveTitle
                    : this.category.livechat_channel_id.joinTitle,
                icon: this.category.livechat_channel_id.are_you_inside
                    ? "fa fa-sign-out text-danger"
                    : "fa fa-sign-in text-success",
            });
        }
        return actions;
    },
};

patch(DiscussSidebarCategory.prototype, DiscussSidebarCategoryPatch);
