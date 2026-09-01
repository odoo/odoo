import { Component, onWillStart, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { openComboConfigurator } from "@sale/js/combo_configurator_utils";

export class ComboMenuWidget extends Component {
    static template = "sale.ComboMenuWidget";
    static components = { Dropdown, DropdownItem };
    props = useProps(standardWidgetProps);

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");

        onWillStart(async () => {
            this.comboProducts = await this.orm.searchRead(
                "product.product",
                [["type", "=", "combo"]],
                ["id", "display_name"],
            );
        });
    }

    get orderLineList() {
        return this.props.record.data.order_line;
    }

    async onComboProductSelected(product) {
        const comboLineRecord = await this.orderLineList.addNewRecord({
            mode: "readonly",
            context: { default_product_id: product.id },
        });

        await openComboConfigurator({ dialog: this.dialog, comboLineRecord, edit: false });
    }
}

export const comboMenuWidget = {
    component: ComboMenuWidget,
};

registry.category("view_widgets").add("combo_menu", comboMenuWidget);
