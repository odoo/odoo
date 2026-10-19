import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { SaleOrderFormStaticList } from "./sale_order_static_list";

class SaleOrderFormModel extends RelationalModel {
    static StaticList = SaleOrderFormStaticList;
}

export const saleOrderFormView = {
    ...formView,
    Model: SaleOrderFormModel,
};

registry.category("views").add("sale_order_form", saleOrderFormView);
