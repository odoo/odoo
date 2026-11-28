import { Component, onWillStart, signal, useProps } from "@odoo/owl";
import { openComboConfigurator } from "@sale/js/combo_configurator_utils";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class ComboMenuWidget extends Component {
    static template = "sale.ComboMenuWidget";
    static components = { Dropdown, DropdownItem };
    props = useProps(standardWidgetProps);

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");

        this.comboProducts = signal.Array([]);

        onWillStart(async () => {
            const comboProducts = await this.orm
                .cache({
                    type: "disk",
                    update: "always",
                    callback: (freshComboProducts, hasChanged) => {
                        if (hasChanged) {
                            this.comboProducts.set(freshComboProducts);
                        }
                    },
                })
                .searchRead("product.product", [["type", "=", "combo"]], ["id", "display_name"]);
            this.comboProducts.set(comboProducts);
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
