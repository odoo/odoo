import { DiscussSidebarCategory } from "@mail/discuss/core/public_web/discuss_sidebar_categories";
import { patch } from "@web/core/utils/patch";

/** @type {import("@mail/discuss/core/public_web/discuss_sidebar_categories").DiscussSidebarCategory} */
const DiscussSidebarCategoryPatch = {
    get actions() {
        const actions = super.actions;
        if (this.store.has_access_livechat && this.category.livechatChannel && this.category.open) {
            actions.push({
                onSelect: () => {
                    if (this.category.livechatChannel.are_you_inside) {
                        this.category.livechatChannel.leave({ notify: false });
                    } else {
                        this.category.livechatChannel.join({ notify: false });
                    }
                },
                label: this.category.livechatChannel.are_you_inside
                    ? this.category.livechatChannel.leaveTitle
                    : this.category.livechatChannel.joinTitle,
                icon: this.category.livechatChannel.are_you_inside
                    ? "fa fa-sign-out text-danger"
                    : "fa fa-sign-in text-success",
            });
        }
        return actions;
    },
};

patch(DiscussSidebarCategory.prototype, DiscussSidebarCategoryPatch);
