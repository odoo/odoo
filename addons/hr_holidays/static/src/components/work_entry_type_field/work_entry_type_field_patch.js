import { patch } from "@web/core/utils/patch";
import { Many2OneWorkEntryTypeField } from "@hr_work_entry/components/work_entry_type_field/work_entry_type_field";

patch(Many2OneWorkEntryTypeField.prototype, {
    get m2oProps() {
        const props = super.m2oProps;
        return {
            ...props,
            specification: { ...props.specification, remaining_leaves_label: 1 },
        };
    },
});
