import { Component, onWillStart, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class DiscountMenuWidget extends Component {
    static template = "sale.DiscountMenuWidget";
    static components = { Dropdown, DropdownItem };
    static props = { ...standardWidgetProps };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.state = proxy({ canManualDiscount: false });
        onWillStart(async () => {
            this.state.canManualDiscount = await user.hasGroup("sale.group_discount_per_so_line");
        });
    }

    async openDiscountWizard() {
        const action = await this.orm.call("sale.order", "action_open_discount_wizard", [this.props.record.resId]);
        await this.actionService.doAction(action, {
            additionalContext: {
                active_id: this.props.record.resId,
                active_model: "sale.order",
            },
            onClose: async () => {
                await this.props.record.load();
            },
        });
    }
}

export const discountMenuWidget = {
    component: DiscountMenuWidget,
};

registry.category("view_widgets").add("discount_menu", discountMenuWidget);
