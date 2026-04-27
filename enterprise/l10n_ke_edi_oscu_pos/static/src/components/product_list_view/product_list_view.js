/** @odoo-module **/
import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

export class ProductListController extends ListController {
    static template = "l10n_ke_edi_oscu_pos.ProductListController";
}

export const ProductListView = {
    ...listView,
    Controller: ProductListController,
};

registry.category("views").add("product_list_view", ProductListView);
