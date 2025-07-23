import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { SaleOrderDisplayOptions } from "./sale_order_display_options";
import { registry } from "@web/core/registry";


export class SaleOrderDisplayPlugin extends Plugin {
    static id = "SaleOrderDisplay";
    static dependencies = ["builderOptions", "builderActions"];

    resources = {
        builder_options: [
            {
                OptionComponent: SaleOrderDisplayOptions,
                selector: ".s_sale_order_display",
            }
        ],
        builder_actions: {
            ConfirmedOrders,
            ViewChange,
            LimitChange,
        }
    }
}

export class ConfirmedOrders extends BuilderAction {
    static id = "confirmedorders"
    setup() {
        super.setup();
    }
}

export class ViewChange extends BuilderAction {
    static id = "viewchange"
    setup() {
        super.setup();
    }
}


export class LimitChange extends BuilderAction {
    static id = "limitchange"
    setup() {
        super.setup();
    }
}

registry.category("website-plugins").add(SaleOrderDisplayPlugin.id, SaleOrderDisplayPlugin);
