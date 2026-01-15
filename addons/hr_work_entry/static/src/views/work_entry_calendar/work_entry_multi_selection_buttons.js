import { WorkEntryMultiCreatePopover } from "@hr_work_entry/views/work_entry_calendar/work_entry_multi_create_popover";
import { useService } from "@web/core/utils/hooks";
import { addFieldDependencies } from "@web/model/relational_model/utils";
import { MultiSelectionButtons } from "@web/views/view_components/multi_selection_buttons";

export class WorkEntryCalendarMultiSelectionButtons extends MultiSelectionButtons {
    static template = "hr_work_entry.WorkEntryCalendarMultiSelectionButtons";
    static props = {
        reactive: {
            type: Object,
            shape: {
                ...MultiSelectionButtons.props.reactive.shape,
                userFavoritesWorkEntries: Array,
                onQuickReplace: Function,
                onQuickReset: Function,
            },
        }
    };
    static components = {
        ...MultiSelectionButtons.components,
        Popover: WorkEntryMultiCreatePopover,
    };

    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    get favoritesWorkEntries() {
        return this.props.reactive.userFavoritesWorkEntries;
    }

    /**
     * @override
     */
    getMultiCreatePopoverProps() {
        const props = super.getMultiCreatePopoverProps();
        props.onQuickReplace = (values) => {
            this.props.reactive.onQuickReplace(values);
        }
        return props;
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

    makeValues(workEntryTypeId) {
        return {
            employee_id: this.props.reactive.context.default_employee_id,
            duration: -1,
            work_entry_type_id: workEntryTypeId,
        };
    }

    async onQuickReplace(workEntryTypeId) {
        const values = this.makeValues(workEntryTypeId);
        this.props.reactive.onQuickReplace(values);
    }
}
