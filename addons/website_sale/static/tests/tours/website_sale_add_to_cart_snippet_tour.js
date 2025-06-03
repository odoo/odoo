import {
    clickOnEditAndWaitEditMode,
    clickOnElement,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    changeOptionInPopover,
} from "@website/js/tours/tour_utils";
import { assertCartContains } from '@website_sale/js/tours/tour_utils';
import { stepUtils } from "@web_tour/tour_service/tour_utils";


function editAddToCartSnippet() {
    return [
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet({id: 's_add_to_cart'})
    ]
}

registerWebsitePreviewTour('add_to_cart_snippet_tour', {
        url: '/',
        edition: true,
    },
    () => [
        ...insertSnippet({name: 'Add to Cart Button'}),

        // Basic product with no variants
        ...clickOnSnippet({id: 's_add_to_cart'}),
        ...changeOptionInPopover("Add to Cart Button", "Product", "Product No Variant", true),
        ...clickOnSave(),
        stepUtils.waitIframeIsReady(),
        clickOnElement("add to cart button", ":iframe .s_add_to_cart_btn"),

        // Product with 2 variants with visitor choice (will open modal)
        ...editAddToCartSnippet(),
        ...changeOptionInPopover("Add to Cart Button", "Product", "Product Yes Variant 1", true),
        ...clickOnSave(),
        stepUtils.waitIframeIsReady(),
        clickOnElement("add to cart button", ":iframe .s_add_to_cart_btn"),
        clickOnElement("continue shopping", ":iframe .modal button:contains(Continue Shopping)"),

        // Product with 2 variants with a variant selected
        ...editAddToCartSnippet(),
        ...changeOptionInPopover("Add to Cart Button", "Product", "Product Yes Variant 2", true),
        ...changeOptionInPopover("Add to Cart Button", "Variant", "Product Yes Variant 2 (Pink)"),
        ...clickOnSave(),
        stepUtils.waitIframeIsReady(),
        clickOnElement("add to cart button", ":iframe .s_add_to_cart_btn"),
        // Since 18.2, even if a specific variant is selected, the product configuration modal is displayed
        // The variant set on the modal used the default variants attributes (so will not correspond to the selected variant)
        // TODO: fix this misbahvior by setting the variant attributes based on the chosen variant 
        // https://github.com/odoo/odoo/pull/201217#issuecomment-2721871718
        {
            content: "Check if the red variant is selected",
            trigger: ":iframe .modal li:contains(Red) input:checked",
        },
        {
            content: "Click the pink variant",
            trigger: ":iframe .modal li:contains(Pink) input",
            run: "click",
        },
        {
            content: "Check if the pink variant is selected",
            trigger: ":iframe .modal li:contains(Pink) input:checked",
        },
        clickOnElement('continue shopping', ':iframe .modal button:contains(Continue Shopping)',),

        // Basic product with no variants and action=buy now
        ...editAddToCartSnippet(),
        ...changeOptionInPopover("Add to Cart Button", "Product", "Product No Variant", true),
        ...changeOptionInPopover("Add to Cart Button", "Action", "Buy Now", false),
        // At this point the "Add to cart" button was changed to a "Buy Now" button
        ...clickOnSave(),
        stepUtils.waitIframeIsReady(),
        clickOnElement('"Buy Now" button', ':iframe .s_add_to_cart_btn'),
        {
            // wait for the page to load, as the next check was sometimes too fast
            content: "Wait for the redirection to the cart page",
            trigger: ":iframe h4:contains(order summary)",
        },
        assertCartContains({productName: 'Product No Variant', backend: true}),
        assertCartContains({productName: 'Product Yes Variant 1 (Red)', backend: true}),
        assertCartContains({productName: 'Product Yes Variant 2 (Pink)', backend: true}),
    ],
);
