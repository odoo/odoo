import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";

const checkProductsLoaded = (categoryName, productCount) =>
    Array.from({ length: productCount }, (_, i) => `${categoryName}-P${i}`).map((product) =>
        ProductPage.checkProductLoaded(product)
    );

const checkProductsNotLoaded = (categoryName, productCount) =>
    Array.from({ length: productCount }, (_, i) => `${categoryName}-P${i}`).map((product) =>
        ProductPage.checkProductNotLoaded(product)
    );

registry.category("web_tour.tours").add("test_self_order_virtual_consultation", {
    steps: () => [
        // -- Init
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),

        // -- Virtual
        ProductPage.checkCategoryButtonNotLoaded("C10"),
        ProductPage.checkActiveCategoryButton("C0"),

        ProductPage.checkCategoryLoaded("C0"),
        ...checkProductsLoaded("C0", 6),
        ProductPage.checkCategoryLoaded("C1"),
        ...checkProductsLoaded("C1", 4),
        ProductPage.checkCategoryNotLoaded("C8"),
        ...checkProductsNotLoaded("C8", 6),

        ProductPage.clickOnCategory("C8"),
        ProductPage.checkActiveCategoryButton("C8"),

        ProductPage.checkCategoryLoaded("C8"),
        ...checkProductsLoaded("C8", 6),
        ProductPage.checkCategoryLoaded("C9"),
        ...checkProductsLoaded("C9", 4),
        ProductPage.checkCategoryNotLoaded("C1"),
        ...checkProductsNotLoaded("C1", 6),
    ],
});

registry.category("web_tour.tours").add("test_self_order_virtual_kiosk", {
    steps: () => [
        // -- Init
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),

        // -- Virtual
        ProductPage.checkCategoryButtonNotLoaded("C10"),
        ProductPage.checkActiveCategoryButton("C0"),
        ProductPage.checkActiveSubcategoryButton("All"),

        ProductPage.checkCategoryNotLoaded("C0"),
        ...checkProductsLoaded("C0", 6),
        ProductPage.checkCategoryNotLoaded("C1"),
        ...checkProductsNotLoaded("C1", 6),
        ProductPage.checkCategoryNotLoaded("C8"),
        ...checkProductsNotLoaded("C8", 6),

        ProductPage.clickOnCategory("C8"),
        ProductPage.checkActiveCategoryButton("C8"),
        ProductPage.checkActiveSubcategoryButton("All"),

        ProductPage.checkCategoryNotLoaded("C8"),
        ...checkProductsLoaded("C8", 6),
        ProductPage.checkCategoryNotLoaded("C9"),
        ...checkProductsNotLoaded("C9", 6),
        ProductPage.checkCategoryNotLoaded("C1"),
        ...checkProductsNotLoaded("C1", 6),

        ProductPage.clickOnSubcategory("C8.2"),
        ProductPage.checkActiveCategoryButton("C8"),
        ProductPage.checkActiveSubcategoryButton("C8.2"),
        ProductPage.checkCategoryNotLoaded("C8"),
        ProductPage.checkProductNotLoaded("C8-P0"),
        ProductPage.checkProductNotLoaded("C8-P1"),
        ProductPage.checkProductLoaded("C8-P2"),
        ProductPage.checkProductNotLoaded("C8-P3"),
        ProductPage.checkProductNotLoaded("C8-P4"),
        ProductPage.checkProductNotLoaded("C8-P5"),

        ProductPage.clickOnSubcategory("C8.0"),
        ProductPage.checkActiveCategoryButton("C8"),
        ProductPage.checkActiveSubcategoryButton("C8.0"),
        ProductPage.checkCategoryNotLoaded("C8"),
        ProductPage.checkProductLoaded("C8-P0"),
        ProductPage.checkProductNotLoaded("C8-P1"),
        ProductPage.checkProductNotLoaded("C8-P2"),
        ProductPage.checkProductNotLoaded("C8-P3"),
        ProductPage.checkProductLoaded("C8-P4"),
        ProductPage.checkProductNotLoaded("C8-P5"),
    ],
});
