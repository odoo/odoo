import { patch } from "@web/core/utils/patch";
import { DiscussSidebarCategory } from "../public_web/discuss_sidebar_categories";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/** @type {import("@mail/discuss/core/public_web/discuss_sidebar_categories").DiscussSidebarCategory} */
const DiscussSidebarCategoryPatch = {
    setup() {
        super.setup();
        this.actionService = useService("action");
    },
    open() {
        if (this.category.id === "channels") {
            this.actionService.doAction({
                name: _t("Public Channels"),
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                views: [
                    [false, "kanban"],
                    [false, "list"],
                    [false, "form"],
                ],
                domain: [
                    ["channel_type", "=", "channel"],
                    ["parent_channel_id", "=", false],
                ],
            });
        } else if (this.category.id === "announcements") {
            this.actionService.doAction({
                name: _t("Announcement Channels"),
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                views: [
                    [false, "kanban"],
                    [false, "form"],
                ],
                context: { default_channel_type: "announcement" },
                domain: [
                    ["channel_type", "=", "announcement"],
                    ["parent_channel_id", "=", false],
                ],
            });
        }
    },
    get actions() {
        const actions = super.actions;
        if (this.category.canView) {
            actions.push({
                onSelect: () => this.open(),
                label: _t("View or join %s", this.category.id),
                icon: "fa fa-cog",
            });
        }
        return actions;
    },
};

patch(DiscussSidebarCategory.prototype, DiscussSidebarCategoryPatch);
