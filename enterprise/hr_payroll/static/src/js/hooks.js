import { useComponent } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export function useOpenViews() {
    const orm = useService('orm')
    const component = useComponent();
    const actionService = useService('action')

    const { title } = component.model.metaData;
    return async (domain, views, context) => {
        const result = await orm.searchRead("hr.payroll.report", domain, ["payslip_id"]);
        const contractDomain = [["id", "in", result.map((r) => r.payslip_id[0])]];
        actionService.doAction({
            type: "ir.actions.act_window",
            name: title,
            views: [
                [false, "list"],
                [false, "form"],
            ],
            context,
            res_model: "hr.payslip",
            target: "current",
            domain: contractDomain,
        });
    };
}
