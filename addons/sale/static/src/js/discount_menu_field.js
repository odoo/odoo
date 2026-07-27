import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class DiscountMenuField extends Component {
    static template = "sale.DiscountMenuField";
    static components = { Dropdown, DropdownItem };
    static props = { ...standardFieldProps };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
    }

    async openDiscountWizard() {
        const action = await this.orm.call("sale.order", "action_open_discount_wizard", [this.props.record.resId]);
        this.actionService.doAction(action);
    }
}

export const discountMenuFieldConfig = {
    component: DiscountMenuField,
    supportedTypes: ["boolean", "char", "integer"],
};

registry.category("fields").add("discount_menu", discountMenuFieldConfig);
