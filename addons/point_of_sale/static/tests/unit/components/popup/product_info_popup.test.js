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
            productTaxDetails: {
                taxes_data: [],
                total_excluded_currency: 0,
                total_included_currency: 0,
            },
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

test("Product info popup prices come from the tax details, not from the server prices", async () => {
    const store = await setupPosEnv();
    const product = store.models["product.template"].get(5);

    await mountPosDialog(ProductInfoPopup, {
        close: () => {},
        info: {
            productInfo,
            costCurrency: "$ 0.00",
            marginCurrency: "$ 0.00",
            marginPercent: 0,
            orderCostCurrency: "$ 0.00",
            orderMarginCurrency: "$ 0.00",
            orderMarginPercent: 0,
            orderPriceWithoutTaxCurrency: "$ 0.00",
            orderPriceWithTaxCurrency: "$ 0.00",
            orderTaxTotalCurrency: "$ 0.00",
            taxAmount: "$ 1.50",
            taxName: "15%",
            productTaxDetails: {
                taxes_data: [{ tax: { id: 1, name: "15%" }, tax_amount_currency: 1.5 }],
                total_excluded_currency: 10,
                total_included_currency: 11.5,
            },
        },
        productTemplate: product,
    });

    await waitFor(".section-financials");
    expect(".section-financials .price-excl-tax").toHaveText("$ 10.00");
    expect(".section-financials .vat-value").toHaveText("$ 1.50");
    expect(".section-financials .price-incl-tax").toHaveText("$ 11.50");
    // The dialog title shows the same price incl. tax, so it must use the same source.
    expect(".modal-header .section-title").toHaveText(/11\.50/);
});
