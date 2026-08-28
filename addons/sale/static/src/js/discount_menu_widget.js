import { Component, onWillStart } from "@odoo/owl";
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

        onWillStart(async () => {
            this.canAddManualDiscount = await user.hasGroup("sale.group_discount_per_so_line");
        });
    }

    async doActionButton(type, name) {
        await this.actionService.doActionButton({
            type,
            name,
            resModel: "sale.order",
            resId: this.props.record.resId,
            onClose: () => this.props.record.load(),
        });
    }
}

export const discountMenuWidget = {
    component: DiscountMenuWidget,
};

registry.category("view_widgets").add("discount_menu", discountMenuWidget);
