import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { productModels } from "@product/../tests/product_test_helpers";
import { SaleOrder } from "./mock_server/mock_models/sale_order";
import { SaleOrderLine } from "./mock_server/mock_models/sale_order_line";


export const saleModels = {
    ...mailModels,
    ...productModels,
    SaleOrder,
    SaleOrderLine,
};

export function defineSaleModels() {
    defineModels(saleModels);
}
