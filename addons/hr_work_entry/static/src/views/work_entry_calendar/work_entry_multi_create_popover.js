import { MultiCreatePopover } from "@web/views/view_components/multi_create_popover";

export class WorkEntryMultiCreatePopover extends MultiCreatePopover {
    static template = "hr_work_entry.WorkEntryMultiCreatePopover";
    static props = {
        ...MultiCreatePopover.props,
        onQuickReplace: Function,
    };

    async onReplace() {
        const isValid = await this.isValidMultiCreateData();
        if (isValid) {
            const values = await this.multiCreateData.record.getChanges();
            this.props.onQuickReplace(values);
            this.props.close();
        }
    }
}
