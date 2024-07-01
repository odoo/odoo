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
        this.orm = useService("orm");
    }

    async onClick() {
        const context = makeContext([this.props.record.evalContext || {}]);

        const promises = [];

        const single_report_action = await this.orm.call(
            "pos.daily.sales.reports.wizard",
            "get_single_report_print_action",
            [[]],
            {
                pos_session_id: context.pos_session_id,
            }
        );
        promises.push(this.action.doAction(single_report_action));

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
            promises.push(this.action.doAction(multi_report_action));
        }

        await Promise.all(promises);
    }
}

export const printReportButton = {
    component: PrintReportButton,
};
registry.category("view_widgets").add("print_report_button", printReportButton);
