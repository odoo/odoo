import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";

export const saleManagementOrderFormView = {
    ...formView,
    buttonTemplate: "sale_management.SaleManagementOrderFormView.Buttons",
};

registry.category("views").add("sale_order_form", saleManagementOrderFormView);
