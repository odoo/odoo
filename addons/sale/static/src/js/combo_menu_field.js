import { Component, onWillStart, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { openComboConfigurator } from "@sale/js/combo_configurator_utils";

export class ComboMenuField extends Component {
    static template = "sale.ComboMenuField";
    static components = { Dropdown, DropdownItem };
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");

        this.state = proxy({ comboProducts: [] });

        onWillStart(async () => {
            this.state.comboProducts = await this.orm.searchRead(
                "product.product",
                [["type", "=", "combo"]],
                ["id", "display_name", "product_tmpl_id"],
            );
        });
    }

    get saleOrder() {
        return this.props.record.data;
    }

    get orderLineList() {
        return this.props.record.data.order_line;
    }

    async onComboProductSelected(product) {
        const comboLineRecord = await this.orderLineList.addNewRecord({ mode: "readonly" });
        await comboLineRecord.update({
            product_id: { id: product.id, display_name: product.display_name },
        });

        await openComboConfigurator({ dialog: this.dialog, comboLineRecord, edit: false });
    }
}

export const comboMenuFieldConfig = {
    component: ComboMenuField,
    supportedTypes: ["boolean", "char", "integer"],
};

registry.category("fields").add("combo_menu", comboMenuFieldConfig);
