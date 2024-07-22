import { ChannelSelector } from "@mail/discuss/core/web/channel_selector";
import { onExternalClick } from "@mail/utils/common/hooks";

import { patch } from "@web/core/utils/patch";
import { DiscussSidebarCategories } from "../public_web/discuss_sidebar_categories";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

DiscussSidebarCategories.components = { ...DiscussSidebarCategories.components, ChannelSelector };

/**
 * @type {import("@mail/discuss/core/public_web/discuss_sidebar_categories").DiscussSidebarCategories}
 */
const DiscussCategoriesPatch = {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.state.editing = true;
        onExternalClick("selector", () => {
            this.state.editing = false;
        });
    },
    addToCategory(category) {
        this.state.editing = category.id;
    },
    openCategory(category) {
        if (category.id === "channels") {
            this.actionService.doAction({
                name: _t("Public Channels"),
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                views: [
                    [false, "kanban"],
                    [false, "form"],
                ],
                domain: [["channel_type", "=", "channel"]],
            });
        }
    },
    /** @param {import("models").Thread} thread */
    openSettings(thread) {
        if (thread.channel_type === "channel") {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                res_id: thread.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    },
    stopEditing() {
        this.state.editing = false;
    },
};
patch(DiscussSidebarCategories.prototype, DiscussCategoriesPatch);
