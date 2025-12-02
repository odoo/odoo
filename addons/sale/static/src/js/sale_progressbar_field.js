import { useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    KanbanProgressBarField,
    kanbanProgressBarField,
} from "@web/views/fields/progress_bar/kanban_progress_bar_field";

/**
 * A custom Component for the view of sales teams on the kanban view in the CRM app.
 *
 * The wanted behavior is to show a progress bar when an invoicing target is defined or show
 * a link redirecting to the record's form view otherwise.
 */
export class SaleProgressBarField extends KanbanProgressBarField {
    static template = "sale.SaleProgressBarField";
    /**
     * Anything used by the component is defined on the setup method.
     */
    setup() {
        super.setup();

        this.actionService = useService("action");
        this.orm = useService("orm");

        useEffect(() => {
            this.state.isInvoicingTargetDefined = this.props.record.data[this.props.maxValueField];
        });
    }

    /**
     * Display the form view of the record on click.
     */
    async defineInvoicingTarget() {
        const { resId, resModel } = this.props.record;
        const action = await this.orm.call(resModel, "get_formview_action", [[resId]]);
        this.actionService.doAction(action);
    }
}

export const saleProgressBarField = {
    ...kanbanProgressBarField,
    component: SaleProgressBarField,
};

registry.category("fields").add("sales_team_progressbar", saleProgressBarField);
