import {
    clickOnEditAndWaitEditMode,
    clickOnElement,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    changeOptionInPopover,
} from "@website/js/tours/tour_utils";
import { assertCartContains } from "@website_sale/js/tours/tour_utils";

function editAddToCartSnippet() {
    return [
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet({ id: "s_add_to_cart" }),
    ];
}

function checkQuanityInCart(quantity) {
    return {
        content: `Check if the cart quantity is ${quantity}`,
        trigger: `:iframe .my_cart_quantity:contains(${quantity})`,
    };
}

registerWebsitePreviewTour(
    "add_to_cart_snippet_tour",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ name: "Add to Cart Button" }),

        ...clickOnSnippet({ id: "s_add_to_cart" }),
        ...changeOptionInPopover("Add to Cart Button", "Product", "Product No Variant"),
        ...clickOnSave(),
        clickOnElement("add to cart button", ":iframe .s_add_to_cart_btn"),
        checkQuanityInCart("1"),

        ...editAddToCartSnippet(),
        ...changeOptionInPopover(
            "Add to Cart Button",
            "Product",
            "Product Yes Variant 1",
        ),
        ...clickOnSave(),
        clickOnElement("add to cart button", ":iframe .s_add_to_cart_btn"),
        clickOnElement("add to cart", ":iframe .modal button:contains(Add to Cart)"),
        checkQuanityInCart("2"),

        // Product with 2 variants with a variant selected in the snippet option.
        // WARNING: this section does NOT assert that the configured variant is
        // pre-selected in the add-to-cart modal. It pins the opposite, known-broken
        // behaviour (see the regression note further down) and then re-selects the
        // configured variant by hand just to reach the cart. When that bug is fixed,
        // the "known bug" step below must be inverted and the manual re-click dropped.
        ...editAddToCartSnippet(),
        ...changeOptionInPopover(
            "Add to Cart Button",
            "Product",
            "Product Yes Variant 2",
        ),
        {
            content: "Check if variant option is visible",
            trigger:
                "[data-container-title='Add to Cart Button'] [data-label='Variant']",
        },
        ...changeOptionInPopover(
            "Add to Cart Button",
            "Variant",
            "Product Yes Variant 2 (Pink)",
        ),
        ...clickOnSave(),
        clickOnElement("add to cart button", ":iframe .s_add_to_cart_btn"),
        // Since 18.2, even if a specific variant is selected, the product configuration modal is displayed
        // The variant set on the modal used the default variants attributes (so will not correspond to the selected variant)
        // TODO: fix this misbehavior by setting the variant attributes based on the chosen variant
        // https://github.com/odoo/odoo/pull/201217#issuecomment-2721871718
        {
            content:
                "KNOWN BUG: the default (Red) variant is pre-selected instead of the" +
                " configured (Pink) one — invert this step once the bug above is fixed",
            trigger: ":iframe .modal li:contains(Red) input:checked",
        },
        {
            content:
                "Work around the known bug: manually select the configured Pink variant",
            trigger: ":iframe .modal li:contains(Pink) input",
            run: "click",
        },
        {
            content: "Check if the pink variant is selected",
            trigger: ":iframe .modal li:contains(Pink) input:checked",
        },
        clickOnElement("add to cart", ":iframe .modal button:contains(Add to Cart)"),
        checkQuanityInCart("3"),

        ...editAddToCartSnippet(),
        ...changeOptionInPopover("Add to Cart Button", "Product", "Product No Variant"),
        {
            content: "Check if action option is visible",
            trigger:
                "[data-container-title='Add to Cart Button'] [data-label='Action']",
        },
        ...changeOptionInPopover("Add to Cart Button", "Action", "Buy Now"),
        ...clickOnSave(),
        clickOnElement('"Buy Now" button', ":iframe .s_add_to_cart_btn"),
        checkQuanityInCart("4"),
        {
            content: "Wait for the redirection to the cart page",
            trigger: ":iframe h4:contains(order summary)",
        },
        ...assertCartContains({ productName: "Product No Variant", backend: true }),
        ...assertCartContains({
            productName: "Product Yes Variant 1",
            combinationName: "Red",
            backend: true,
        }),
        ...assertCartContains({
            productName: "Product Yes Variant 2",
            combinationName: "Pink",
            backend: true,
        }),
    ],
);
