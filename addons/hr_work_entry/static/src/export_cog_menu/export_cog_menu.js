import { Component, t, useProps } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useEnv } from "@web/owl2/utils";

const cogMenuRegistry = registry.category("cogMenu");

export class ExportWorkEntriesCogMenu extends Component {

    static template = "hr_work_entry.ExportWorkEntriesCogMenu"
    static components = { DropdownItem };

    props = useProps({
        isActionMenu: t.boolean().optional(),
    });

    setup() {
        this.actionService = useService("action");
    }

    async exportWorkEntries() {
        let activeIds = (this.env.model.root.selection && this.env.model.root.selection.length)
            ? this.env.model.root.selection.map(r => r.resId)
            : this.env.model.root.resId;
        return this.actionService.doAction("hr_work_entry.action_open_export_wizard", {
            additionalContext: {
                active_ids: activeIds,
            },
        });
    }
}

cogMenuRegistry.add(
    "export-work-entries-cog-menu",
    {
        Component: ExportWorkEntriesCogMenu,
        groupNumber: 40,
<<<<<<< c84fbd6b53c64b9b2aaa6168c47a1ca4378ab63c
        isDisplayed() {
            const env = useEnv();
            return env.searchModel.resModel === "hr.employee";
        },
||||||| ce3e0e984ba6b3b82dcafd8b2702e602c35b0f17
        isDisplayed: ({ searchModel }) => { return searchModel.resModel === "hr.employee" },
=======
        isDisplayed: ({ config, searchModel }) =>
            searchModel.resModel === "hr.employee" &&
            ["form", "kanban", "list"].includes(config.viewType),
>>>>>>> 080fe1df86828cd98ec810479da0d60e7b995aa6
    },
    { sequence: 1 }
);
