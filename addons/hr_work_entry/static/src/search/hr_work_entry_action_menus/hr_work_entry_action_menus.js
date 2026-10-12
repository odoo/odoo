import { patch } from "@web/core/utils/patch";
import { HrActionMenus } from "@hr/search/hr_action_menus/hr_action_menus";

patch(HrActionMenus.prototype, {
    async exportWorkEntries() {
        const activeIds = (this.env.model.root.selection && this.env.model.root.selection.length)
            ? this.env.model.root.selection.map((r) => r.resId)
            : this.env.model.root.resId;
        return this.actionService.doAction("hr_work_entry.action_open_export_wizard", {
            additionalContext: {
                active_ids: activeIds,
            },
        });
    },
});
