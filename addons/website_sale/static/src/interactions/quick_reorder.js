import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { CartQuickReorder } from "@website_sale/js/cart_quick_reorder/cart_quick_reorder";
import wSaleUtils from "@website_sale/js/website_sale_utils";

export class QuickReorder extends Interaction {
    static selector = "#quick_reorder";
    dynamicContent = {
        _root: {
            "t-component": (el) => {
                const selectors = {
                    quickReorderLabel: ".quick_reorder_edit_mode",
                };

                const templateData = wSaleUtils.extractEditModeText(el.parentElement, selectors);

                return [CartQuickReorder, { templateData }];
            },
        },
    };
}

registry
    .category("public.interactions")
    .add("website_sale.quick_reorder", QuickReorder);
