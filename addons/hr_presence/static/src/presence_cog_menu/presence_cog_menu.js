import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component, onWillStart } from "@odoo/owl";
import { getActionRecords, getPresenceActionItems } from "../views/hooks";
import { useService } from "@web/core/utils/hooks";

const cogMenuRegistry = registry.category("cogMenu");

export class PresenceCogMenu extends Component {
    static template = "hr_presence.PresenceCogMenu";
    static components = { Dropdown, DropdownItem };
    static props = { record: { type: Object, optional: true }, resId: { type: [Number, String], optional: true } };

    setup() {
        super.setup();

        this.presenceActionItems = [];
        this.orm = useService('orm');
        this.actionService = useService('action');

        onWillStart(async () => {
            this.records = await getActionRecords(this.orm);
        });
    }

    onItemSelected(item) {
        const options = {};
        let activeIds = [];

        // Fetch the selected record IDs if there is a selection, otherwise fetch the currently focused record's ID.
        if (this.env.model.root.selection && this.env.model.root.selection.length) {
            activeIds = this.env.model.root.selection.map(r => r.resId);
        } else if (this.env.model.root.resId) {
            activeIds = [this.env.model.root.resId];
        }

        // Inject the fetched ID(s) and model into the action's context so the backend knows which record(s) to process.
        if (activeIds.length > 0) {
            options.additionalContext = { 
                active_id: activeIds[0],
                active_ids: activeIds,
                active_model: "hr.employee",
            };
        }

        this.actionService.doAction(item.id, options);
    }

    get PresenceActionItems() {
        return getPresenceActionItems(null, this.records);
    }
}

cogMenuRegistry.add(
    "presence-cog-menu",
    {
        Component: PresenceCogMenu,
        groupNumber: 40,
        isDisplayed: ({ searchModel }) => { return searchModel.resModel === "hr.employee" },
    },
    { sequence: 1 }
);
