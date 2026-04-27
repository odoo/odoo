import { expect, test, describe } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";

import { deepCopy } from "@web/core/utils/objects";
import { defineModels, mountView, onRpc, contains } from "@web/../tests/web_test_helpers";

import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import { ProductProduct } from "@industry_fsm_sale/../tests/industry_fsm_sale_mock_model";

const stockSaleOrderLineInfo = {
    1: {
        quantity: 0,
        readOnly: false,
        price: 14,
        deliveredQty: 0,
        minimumQuantityOnProduct: 0,
        tracking: false,
        productType: "consu",
    },
    2: {
        quantity: 1,
        readOnly: false,
        price: 400,
        deliveredQty: 0,
        minimumQuantityOnProduct: 0,
        tracking: true,
        productType: "consu",
    },
    3: {
        quantity: 3,
        price: 70,
        readOnly: false,
        deliveredQty: 2,
        minimumQuantityOnProduct: 2,
        tracking: false,
        productType: "consu",
    },
};

describe.current.tags("desktop");
defineModels([ProductProduct]);
defineMailModels();

onRpc("/product/catalog/order_lines_info", () => deepCopy(stockSaleOrderLineInfo));

test("check disabling of decrease/remove buttons when quantity of product is equal to minimumQuantityOnProduct", async () => {
    onRpc("/product/catalog/update_order_line_info", async (request) => {
        const { params } = await request.json();
        const { product_id, quantity } = params;
        expect.step("update_sale_order_line_info");
        if (product_id === 3) {
            expect(quantity).toBe(2, {
                message: "Using the Remove button should set the quantity to 0 in the route params",
            });
        }
        return {};
    });

    await mountView({
        resModel: "product.product",
        type: "kanban",
        context: {
            product_catalog_order_model: "sale.order",
            fsm_task_id: 1,
        },
    });

    await click(".o_kanban_record:nth-of-type(3) .o_product_catalog_quantity button:has(i.fa-minus)");
    await runAllTimers(); // for skipping the debounce delay

    expect(
        ".o_kanban_record:nth-of-type(3) .o_product_catalog_quantity button:has(i.fa-minus)[disabled]"
    ).toHaveCount(1, {
        message: "The minus button should be disabled",
    });
    expect(
        ".o_kanban_record:nth-of-type(3) .o_product_catalog_buttons button:has(i.fa-trash)[disabled]"
    ).toHaveCount(1, {
        message: "The remove button should be disabled",
    });
    expect.verifySteps(["update_sale_order_line_info"]);
});

test("check quantity not decreasable below minimumQuantityOnProduct", async () => {
    onRpc("/product/catalog/update_order_line_info", async (request) => {
        const { params } = await request.json();
        const { product_id, quantity } = params;
        expect.step("update_sale_order_line_info");
        if (product_id === 3) {
            expect(quantity).toBe(2, {
                message:
                    "Trying to set a quantity below the minimumQuantityOnProduct should result in giving minimumQuantityOnProduct value in the route params",
            });
        }
        return {};
    });

    await mountView({
        resModel: "product.product",
        type: "kanban",
        context: {
            product_catalog_order_model: "sale.order",
            fsm_task_id: 1,
        },
    });

    expect(".o_kanban_record:nth-child(3) .o_product_catalog_quantity .o_input").toHaveValue(3, {
        message: "The product quantity should be equal to 3.",
    });

    await contains(".o_kanban_record:nth-child(3) .o_product_catalog_quantity .o_input").edit(1);
    await runAllTimers(); // for skipping the debounce delay

    expect(".o_kanban_record:nth-child(3) .o_product_catalog_quantity .o_input").toHaveValue(2, {
        message:
            "Trying to remove a product that has a minimumQuantityOnProduct should set the value to minimuQuantityOnProduct",
    });
    expect.verifySteps(["update_sale_order_line_info"]);
});

test("check fa-list display", async () => {
    await mountView({
        resModel: "product.product",
        type: "kanban",
        context: {
            product_catalog_order_model: "sale.order",
            fsm_task_id: 1,
        },
    });

    expect(".o_kanban_record:nth-of-type(2) button:has(i.fa-list)").toHaveCount(1, {
        message: "The fa-list icon should be available",
    });
});
