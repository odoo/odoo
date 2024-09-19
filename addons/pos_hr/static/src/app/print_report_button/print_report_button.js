/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";
import { makeContext } from "@web/core/context";

class PrintReportButton extends Component {
    static template = "pos_hr.PrintReportButton";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.action = useService("action");
        // Why not `this.orm = useService("orm");` ?
        // Because in the `onClick` method, the first action call will potentially open the `new layout action wizard`
        // closing the current dialog. Once closed, the succeeding actions will be terminated because of the protection
        // made by calling `useService`. We want to continue with the full logic of the `onClick` method even if the
        // dialog is closed.
        this.orm = this.env.services.orm;
    }

    async onClick() {
        const context = makeContext([this.props.record.evalContext || {}]);

        const single_report_action = await this.orm.call(
            "pos.daily.sales.reports.wizard",
            "get_single_report_print_action",
            [[]],
            {
                pos_session_id: context.pos_session_id,
            }
        );
        await this.action.doAction({
            ...single_report_action,
            close_on_report_download: !context.add_report_per_employee,
        });

        if (context.add_report_per_employee) {
            const multi_report_action = await this.orm.call(
                "pos.daily.sales.reports.wizard",
                "get_multi_report_print_action",
                [[]],
                {
                    pos_session_id: context.pos_session_id,
                    employee_ids: context.employee_ids,
                }
            );
            await this.action.doAction({ ...multi_report_action, close_on_report_download: true });
        }
    }
}

export const printReportButton = {
    component: PrintReportButton,
};
registry.category("view_widgets").add("print_report_button", printReportButton);
