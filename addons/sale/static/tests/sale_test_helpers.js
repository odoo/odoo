import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { ProductProduct } from "./mock_server/mock_models/product_product";
import { ProductTemplate } from "./mock_server/mock_models/product_template";
import { SaleOrder } from "./mock_server/mock_models/sale_order";
import { SaleOrderLine } from "./mock_server/mock_models/sale_order_line";


export const saleModels = {
    ...mailModels,
    ProductProduct,
    ProductTemplate,
    SaleOrder,
    SaleOrderLine,
};

export function defineSaleModels() {
    defineModels(saleModels);
}
