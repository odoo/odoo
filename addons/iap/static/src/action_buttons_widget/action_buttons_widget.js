import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

class IAPActionButtonsWidget extends Component {
    static template = "iap.ActionButtonsWidget";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async onViewServicesClicked() {
        const action = await this.orm.call("iap.account", "action_view_my_services");
        this.action.doAction(action);
    }
}

export const iapActionButtonsWidget = {
    component: IAPActionButtonsWidget,
};
registry.category("view_widgets").add("iap_view_my_services", iapActionButtonsWidget);
