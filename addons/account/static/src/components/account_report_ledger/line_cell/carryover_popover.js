/** @odoo-module native */
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AccountReportCarryoverPopover extends Component {
    static template = "account.AccountReportCarryoverPopover";
    static props = {
        close: Function,
        carryoverData: Object,
        options: Object,
        context: Object,
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
    }

    //------------------------------------------------------------------------------------------------------------------
    //
    //------------------------------------------------------------------------------------------------------------------
    async viewCarryoverLinesAction(expressionId, columnGroupKey) {
        const viewCarryoverLinesAction = await this.orm.call(
            "account.report.expression",
            "action_view_carryover_lines",
            [expressionId, this.props.options, columnGroupKey],
            {
                context: this.props.context,
            },
        );
        this.props.close();
        return this.actionService.doAction(viewCarryoverLinesAction);
    }
}
