import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const cogMenuRegistry = registry.category("cogMenu");

export class ExportWorkEntriesCogMenu extends Component {

    static template = "hr_work_entry.ExportWorkEntriesCogMenu"
    static components = { DropdownItem };
    static props = {
        isActionMenu: { type: Boolean, optional: true },
    };

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
        isDisplayed: ({ searchModel }) => { return searchModel.resModel === "hr.employee" },
    },
    { sequence: 1 }
);
