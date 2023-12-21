import { ListRenderer } from "@web/views/list/list_renderer";
import { SaleActionHelper } from "../../js/sale_action_helper/sale_action_helper";

export class SaleListRenderer extends ListRenderer {
    static template = "sale.SaleListRenderer";
    static components = {
        ...ListRenderer.components,
        SaleActionHelper,
    };
};
