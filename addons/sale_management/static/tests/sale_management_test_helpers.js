import { saleModels } from "@sale/../tests/sale_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { SaleOrderTemplate } from "./mock_server/mock_models/sale_order_template";
import { SaleOrderTemplateLine } from "./mock_server/mock_models/sale_order_template_line";

export const saleManagementModels = {
    ...saleModels,
    SaleOrderTemplate,
    SaleOrderTemplateLine,
};

export function defineSaleManagementModels() {
    defineModels(saleManagementModels);
}
