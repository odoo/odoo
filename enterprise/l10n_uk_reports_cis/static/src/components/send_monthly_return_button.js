/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";
export class SendCISMonthlyReturnButton extends Component {
    /**
     * We need a custom widget as the password field is set as non stored.
     * The client side don't write the password from the field to the orm cache because of that.
     * 
     * The only way to pass the password to the function is by making a manual orm call, and manually passing it as parameter.
     */
    static template = "l10n_uk_cis.SendCISMonthlyReturn";
    static props = { ...standardWidgetProps };
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action")
        this.title = _t("Send CIS monthly return to HMRC")
    }
    async sendMonthlyReturn() {
        this.env.services.ui.block();
        try {
            await this.orm.call("cis.monthly.return.wizard", "action_send_montlhy_return", [
                this.props.record.data.date_from,
                this.props.record.data.date_to,
                this.props.record.data.employment_status,
                this.props.record.data.subcontractor_verification,
                this.props.record.data.inactivity_indicator,
                this.props.record.data.hmrc_cis_password
            ]);
            this.actionService.doAction({ type: "ir.actions.act_window_close" });
        }
        finally {
            this.env.services.ui.unblock();
        }
    }
}
export const sendCISMonthlyReturnButton = {
    component: SendCISMonthlyReturnButton,
}
registry.category("view_widgets").add("send_cis_monthly_return_button", sendCISMonthlyReturnButton);
