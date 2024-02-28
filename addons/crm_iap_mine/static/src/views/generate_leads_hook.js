/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

const { onWillStart, useComponent } = owl;

export function useGenerateLeadsButton() {
    const component = useComponent();
    const user = useService("user");
    const action = useService("action");

    onWillStart(async () => {
        component.isSalesManager = await user.hasGroup("sales_team.group_sale_manager");
    });

    component.onClickGenerateLead = () => {
        const leadType = component.props.context.default_type;
        action.doAction({
            name: "Generate Leads",
            type: "ir.actions.act_window",
            res_model: "crm.iap.lead.mining.request",
            target: "new",
            views: [[false, "form"]],
            context: { is_modal: true, default_lead_type: leadType },
        });
    };
}
