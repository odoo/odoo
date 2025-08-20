import { MultiSelectionButtons } from "@web/views/view_components/multi_selection_buttons";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { WorkEntryMultiCreatePopover } from "@hr_work_entry/views/work_entry_calendar/work_entry_multi_create_popover";
import { addFieldDependencies } from "@web/model/relational_model/utils";

export class WorkEntryCalendarMultiSelectionButtons extends MultiSelectionButtons {
    static template = "hr_work_entry.WorkEntryCalendarMultiSelectionButtons";
    static components = {
        ...MultiSelectionButtons.components,
        Popover: WorkEntryMultiCreatePopover,
    };

    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({ favoritesWorkEntries: null });
    }

    /**
     * @override
     */
    getMultiCreatePopoverProps() {
        return {
            ...super.getMultiCreatePopoverProps(),
            onReplace: (multiCreateData) => {
                this.props.reactive.onQuickReplace(multiCreateData);
            },
        };
    }

    /**
     * @override
     */
    async loadMultiCreateView() {
        await super.loadMultiCreateView();
        addFieldDependencies(
            this.multiCreateRecordProps.activeFields,
            this.multiCreateRecordProps.fields,
            [
                { name: "display_code", type: "char" },
                { name: "color", type: "integer" },
                { name: "employee_id", type: "many2one" },
            ]
        );
    }

    get favoritesWorkEntries() {
        return this.props.reactive.userFavoritesWorkEntries;
    }

    createFakeMultiCreateData(workEntryType) {
        const multiCreateData = {
            timeRange: this.props.timeRange && { ...this.props.timeRange },
            record: {
                data: {
                    employee_id: this.actionService.currentController.currentState.active_id,
                    duration: 8,
                    work_entry_type_id: workEntryType.id,
                },
                fields: {
                    employee_id: { type: "many2one" },
                    duration: { type: "float" },
                    work_entry_type_id: { type: "many2one" },
                },
            },
        };
        multiCreateData.record.getChanges = () => multiCreateData.record.data;
        return multiCreateData;
    }

    async onQuickReplace(workEntryType) {
        const multiCreateData = this.createFakeMultiCreateData(workEntryType);
        this.props.reactive.onQuickReplace(multiCreateData);
    }
}
