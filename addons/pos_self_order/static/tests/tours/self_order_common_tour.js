/* global posmodel */

import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";

registry.category("web_tour.tours").add("test_self_order_products_sorting_order", {
    steps: () => [
        LandingPage.isClosed(),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.checkNthProduct(1, "Free"),
        ProductPage.checkNthProduct(2, "Desk Organizer"),
        ProductPage.checkNthProduct(3, "Ketchup"),
        ProductPage.checkNthProduct(4, "Fanta"),
        ProductPage.checkNthProduct(5, "Coca-Cola"),
    ],
});

registry.category("web_tour.tours").add("test_preparation_categories_are_loaded", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        {
            trigger: "body",
            run: async () => {
                const availableCategIds = posmodel.availableCategories.map((categ) => categ.name);
                if (!availableCategIds.includes("MOOL") || availableCategIds.length !== 1) {
                    throw new Error("Preparation categories are not correctly loaded");
                }
            },
        },
        {
            content: `Check category 'MOOL' is not visible`,
            trigger: `.category_btn:contains('MOOL')`,
        },
        Utils.negateStep({
            content: `Check category 'MODA' is not visible`,
            trigger: `.category_btn:contains('MODA')`,
        }),
        Utils.negateStep({
            content: `Check category 'STVA' is not visible`,
            trigger: `.category_btn:contains('STVA')`,
        }),
        Utils.negateStep({
            content: `Check category 'MANV' is not visible`,
            trigger: `.category_btn:contains('MANV')`,
        }),
        Utils.negateStep({
            content: `Check category 'LTRA' is not visible`,
            trigger: `.category_btn:contains('LTRA')`,
        }),
        Utils.negateStep({
            content: `Check category 'LOWE' is not visible`,
            trigger: `.category_btn:contains('LOWE')`,
        }),
        Utils.negateStep({
            content: `Check category 'ADGU' is not visible`,
            trigger: `.category_btn:contains('ADGU')`,
        }),
    ],
});
