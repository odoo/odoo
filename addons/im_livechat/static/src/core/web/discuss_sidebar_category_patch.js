import { DiscussSidebarCategory } from "@mail/discuss/core/public_web/discuss_sidebar_categories";
import { CloseAllConfirmation } from "@mail/core/common/close_all_confirmation";

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

/** @type {import("@mail/discuss/core/public_web/discuss_sidebar_categories").DiscussSidebarCategory} */
const DiscussSidebarCategoryPatch = {
    get actions() {
        const actions = super.actions;
        if (this.store.has_access_livechat && this.category.livechatChannel && this.category.open) {
            actions.push(
                {
                    onSelect: () => {
                        this.store.env.services.dialog.add(CloseAllConfirmation, {
                            title: _t("Close live chat conversations"),
                            message: _t(
                                "This action will end all live chat conversations of %s. Proceed?",
                                this.category.livechatChannel.name
                            ),
                            onConfirm: () => {
                                const promises = [];
                                for (const thread of this.category.livechatChannel.threads) {
                                    promises.push(thread.leave());
                                }
                                Promise.all(promises);
                            },
                        });
                    },
                    label: _t("Leave all conversations"),
                    icon: "fa fa-close text-danger",
                    active: () =>
                        this.category.livechatChannel.threads.filter(
                            (thread) => thread.isLocallyPinned || thread.is_pinned
                        ).length,
                },
                {
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
                }
            );
        }
        return actions;
    },
};

patch(DiscussSidebarCategory.prototype, DiscussSidebarCategoryPatch);
