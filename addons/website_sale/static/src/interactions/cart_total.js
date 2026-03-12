import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { CartTotal as CartTotalComponent } from "@website_sale/js/cart_total/cart_total";
import wSaleUtils from "@website_sale/js/website_sale_utils";

export class CartTotal extends Interaction {
    static selector = "#cart_totals";
    dynamicContent = {
        _root: {
            "t-component": (el) => {
                const root = el.parentElement;

                const selectors = {
                    deliveryLabel: "#cart_totals_edit_mode .cart_delivery_label",
                    untaxedLabel: "#cart_totals_edit_mode .cart_untaxed_label",
                    totalLabel: "#cart_totals_edit_mode .cart_total_label",
                };

                const templateData = wSaleUtils.extractEditModeText(root, selectors);

                return [CartTotalComponent, { templateData }];
            },
        },
    };
}

registry.category("public.interactions").add("website_sale.total", CartTotal);
