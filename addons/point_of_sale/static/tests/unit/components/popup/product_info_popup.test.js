import { expect, test, waitFor } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { mountPosDialog, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";

definePosModels();

const productInfo = {
    all_prices: { price_with_tax: 10, price_without_tax: 10 },
    free_qty: 0,
    optional_products: [],
    pricelists: [],
    suppliers: [],
    uom: "Units",
};

test("Product info popup displays product tag names and colors", async () => {
    const store = await setupPosEnv();
    const product = store.models["product.template"].get(5);
    const redTag = store.models["product.tag"].get(1001);
    const blueTag = store.models["product.tag"].get(1002);
    product.product_tag_ids = [redTag, blueTag];

    await mountPosDialog(ProductInfoPopup, {
        close: () => {},
        info: {
            productInfo,
            costCurrency: "$\u00a00.00",
            marginCurrency: "$\u00a00.00",
            marginPercent: 0,
            orderCostCurrency: "$\u00a00.00",
            orderMarginCurrency: "$\u00a00.00",
            orderMarginPercent: 0,
            orderPriceWithoutTaxCurrency: "$\u00a00.00",
            orderPriceWithTaxCurrency: "$\u00a00.00",
            orderTaxTotalCurrency: "$\u00a00.00",
            taxAmount: "$\u00a00.00",
            taxName: "",
        },
        productTemplate: product,
    });

    await waitFor("[data-product-tag-id]");
    expect("[data-product-tag-id]").toHaveCount(2);
    expect(`[data-product-tag-id="${redTag.id}"]`).toHaveText("Red tag");
    expect(`[data-product-tag-id="${redTag.id}"]`).toHaveStyle({
        backgroundColor: "rgb(255, 0, 0)",
    });
    expect(`[data-product-tag-id="${blueTag.id}"]`).toHaveText("Blue tag");
    expect(`[data-product-tag-id="${blueTag.id}"]`).toHaveStyle({
        backgroundColor: "rgb(0, 0, 255)",
    });
});
