import { MultiCreatePopover } from "@web/views/view_components/multi_create_popover";

export class WorkEntryMultiCreatePopover extends MultiCreatePopover {
    static template = "hr_work_entry.WorkEntryMultiCreatePopover";
    static props = {
        ...MultiCreatePopover.props,
        onReplace: Function,
    };

    async onReplace() {
        this.props.onReplace(this.multiCreateData);
        this.props.close();
    }
}
