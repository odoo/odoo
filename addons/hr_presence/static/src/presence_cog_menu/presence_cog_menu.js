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
        // Get active_id from record prop or resId prop (both available in form view)
        const activeId = this.props.record?.id || this.props.resId;
        if (activeId) {
            options.additionalContext = { active_id: activeId };
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
