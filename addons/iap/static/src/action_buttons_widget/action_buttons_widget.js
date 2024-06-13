/** @odoo-modules */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";

class IAPActionButtonsWidget extends Component {
    static template = "iap.ActionButtonsWidget";
    static props = {
        ...standardWidgetProps,
        serviceName: String,
        showServiceButtons: Boolean,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async onViewServicesClicked() {
        this.action.doAction("iap.iap_account_action");
    }

    async onBuyLinkClicked() {
        const url = await this.orm.silent.call("iap.account", "get_credits_url", [this.props.serviceName]);
        this.action.doAction({
            type: "ir.actions.act_url",
            url: url,
        });
    }
}

export const iapActionButtonsWidget = {
    component: IAPActionButtonsWidget,
    extractProps: ({ attrs }) => {
        return {
            serviceName: attrs.service_name,
            showServiceButtons: !Boolean(attrs.hide_service),
        };
    },
};
registry.category("view_widgets").add("iap_buy_more_credits", iapActionButtonsWidget);
