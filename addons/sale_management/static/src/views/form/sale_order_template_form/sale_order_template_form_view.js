import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { SaleOrderTemplateFormStaticList } from "./sale_order_template_static_list";

class SaleOrderTemplateModel extends RelationalModel {
    static StaticList = SaleOrderTemplateFormStaticList;
}

export const saleOrderTemplateFormView = {
    ...formView,
    Model: SaleOrderTemplateModel,
};

registry.category("views").add("sale_order_template_form", saleOrderTemplateFormView);
