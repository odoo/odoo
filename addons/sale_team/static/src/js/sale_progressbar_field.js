/** @odoo-module native */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    KanbanProgressBarField,
    kanbanProgressBarField,
} from "@web/fields/display/progress_bar";

export class SaleProgressBarField extends KanbanProgressBarField {
    static template = "sale_team.SaleProgressBarField";
    setup() {
        super.setup();

        this.actionService = useService("action");
        this.orm = useService("orm");
    }

    get isInvoicingTargetDefined() {
        return this.props.record.data[this.props.maxValueField];
    }

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
