import { WorkEntryMultiCreatePopover } from "@hr_work_entry/views/work_entry_calendar/work_entry_multi_create_popover";
import { useService } from "@web/core/utils/hooks";
import { addFieldDependencies } from "@web/model/relational_model/utils";
import { MultiSelectionButtons } from "@web/views/view_components/multi_selection_buttons";
import { usePopover } from "@web/core/popover/popover_hook";

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
        this.quickMultiCreatePopover = usePopover(this.constructor.components.Popover);
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
        props.multiCreateRecordProps.context = {
            ...props.multiCreateRecordProps.context,
            default_is_manual: true,
        }
        return props;
    }

    get multiCreateAdditionalFieldDependencies() {
        return [
            { name: "display_code", type: "char" },
            { name: "color", type: "integer" },
            { name: "shortcut_behavior", type: "selection" },
            { name: "employee_id", type: "many2one", relation: "hr.employee", readonly: false },
        ];
    }

    /**
     * @override
     */
    async loadMultiCreateView() {
        await super.loadMultiCreateView();
        addFieldDependencies(
            this.multiCreateRecordProps.activeFields,
            this.multiCreateRecordProps.fields,
            this.multiCreateAdditionalFieldDependencies
        );
    }

    makeValues(workEntryType, duration) {
        return {
            employee_id: this.props.reactive.context.default_employee_id,
            duration: duration ?? -1,
            work_entry_type_id: workEntryType?.id,
            is_manual: true,
        };
    }

    async onQuickReplace(workEntryType) {
        const values = this.makeValues(workEntryType);
        this.props.reactive.onQuickReplace(values);
    }

    async onQuickAdd(currentTarget, workEntryType) {
        if (this.quickMultiCreatePopover.isOpen) {
            return;
        }
        const values = {
            ...this.makeValues(workEntryType, 1),
            shortcut_behavior: "add",
            display_code: workEntryType?.display_code,
            color: workEntryType?.color,
        };
        const props = this.getMultiCreatePopoverProps();
        this.quickMultiCreatePopover.open(currentTarget, {
            ...props,
            multiCreateRecordProps: {
                ...props.multiCreateRecordProps,
                context: {
                    ...props.multiCreateRecordProps.context,
                    quick_add: true,
                },
                values: values,
            },
            onAdd: (multiCreateData) => {
                this.props.reactive.onAdd(multiCreateData);
            },
        });
    }
}
