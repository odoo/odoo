import { Component, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class InvoiceGuide extends Component {
    static template = "account.InvoiceGuide";

    props = useProps(standardWidgetProps);

    setup() {
        this.action = useService("action");
        this.kanbanDashboard = JSON.parse(this.props.record.data.kanban_dashboard);
    }

    handleActionClick() {
        this.action.doAction(this.kanbanDashboard.onboarding_action_data.action);
    }

    openCompanyDetailsPage() {
        return this.action.doAction({
            name: _t("Set your Company Data"),
            type: "ir.actions.act_window",
            res_model: "res.company",
            res_id: user.activeCompany.id,
            views: [[false, "form"]],
            target: "new",
        });
    }
}

export const invoiceGuide = {
    component: InvoiceGuide,
};

registry.category("view_widgets").add("invoice_upload_guide", invoiceGuide);
