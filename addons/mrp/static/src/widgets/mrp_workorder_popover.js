import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import {
    PopoverComponent,
    PopoverWidgetField,
    popoverWidgetField,
} from "@stock/widgets/popover_widget";

/**
 * Link to a Char field representing a JSON:
 * {
 *  'replan': <REPLAN_BOOL>, // Show the replan btn
 *  'color': '<COLOR_CLASS>', // Color Class of the icon (d-none to hide)
 *  'infos': [
 *      {'msg' : '<MESSAGE>', 'color' : '<COLOR_CLASS>'},
 *      {'msg' : '<MESSAGE>', 'color' : '<COLOR_CLASS>'},
 *      ... ]
 * }
 */

class WorkOrderPopover extends PopoverComponent {
    setup(){
        this.orm = useService("orm");
    }

    async onReplanClick() {
        await this.orm.call(
            'mrp.workorder',
            'action_replan',
            [this.props.record.resId]
        );
        await this.props.record.model.load();
    }
};

class WorkOrderPopoverField extends PopoverWidgetField {
    static components = {
        Popover: WorkOrderPopover,
    };
}

registry.category("fields").add("mrp_workorder_popover", {
    ...popoverWidgetField,
    component: WorkOrderPopoverField,
});
