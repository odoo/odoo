import { ListRenderer } from "@web/views/list/list_renderer";
import { ProductActionHelper } from "@product/js/views/product_action_helper/product_action_helper";

export class ProductActionListRenderer extends ListRenderer {
    static components = {
        ...ListRenderer.components,
        ActionHelper: ProductActionHelper,
    };
}
