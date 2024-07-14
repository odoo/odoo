/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { pick } from "@web/core/utils/objects";

class ConsolidationDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    get datas() {
        return JSON.parse(this.props.record.data[this.props.name]);
    }


    async onUnmappedAccountClick(company_id) {
        await this.env.onClickViewButton({
            clickParams: {
                type: "object",
                name: "action_open_mapping",
            },
            getResParams: () => ({
                ...pick(this.props.record, "context", "evalContext", "resModel", "resId", "resIds"),
                context: { company_id: company_id },
            }),
        });
    }    
}
ConsolidationDashboard.template = "account_consolidation.ConsolidatedDashboardTemplate";

registry.category("fields").add("consolidation_dashboard_field", {
    component: ConsolidationDashboard,
    supportedTypes: ["char"],
});
