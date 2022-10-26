/** @odoo-modules */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

class IAPActionButtonsWidget extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async onViewServicesClicked() {
        const url = await this.orm.silent.call("iap.account", "get_account_url");
        this.action.doAction({
            type: "ir.actions.act_url",
            url: url,
        });
    }

    async onBuyLinkClicked() {
        const url = await this.orm.silent.call("iap.account", "get_credits_url", [this.props.serviceName]);
        this.action.doAction({
            type: "ir.actions.act_url",
            url: url,
        });
    }
}
IAPActionButtonsWidget.template = "iap.ActionButtonsWidget";
IAPActionButtonsWidget.extractProps = ({ attrs }) => {
    return {
        serviceName: attrs.service_name,
        showServiceButtons: !Boolean(attrs.hide_service),
    };
};

registry.category("view_widgets").add("iap_buy_more_credits", IAPActionButtonsWidget);
