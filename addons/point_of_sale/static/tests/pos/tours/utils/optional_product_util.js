import * as ProductConfigurator from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";

export function addOptionalProduct(productName, quantity, configurable) {
    const step = [
        // Verify that the optional product is visible in the list
        {
            content: `Verify that the optional product "${productName}" is available in the list.`,
            trigger: `.optional-product-line .product-name:contains("${productName}")`,
        },
        {
            content: `Click the "+ Add" button to add the optional product "${productName}" to the cart.`,
            trigger: `.optional-product-line .cart-buttons button:contains("+ Add")`,
            run: "click",
        },
    ];

    // Handle configuration steps for configurable optional products
    if (configurable) {
        step.push(
            // Choose the color attribute for the configurable product
            ...ProductConfigurator.pickColor("Blue"),
            // Select the material type from dropdown options
            ...ProductConfigurator.pickSelect("Metal"),
            // Choose the texture or fabric type via radio buttons
            ...ProductConfigurator.pickRadio("wool"),
            // confirm Attribute Selection dialogue
            {
                trigger: ".o-overlay-item:nth-child(2) .modal-footer button:contains('Add')",
                run: "click",
            }
        );
    }

    if (quantity > 1) {
        for (let i = 1; i < quantity; i++) {
            // Increment the product quantity by clicking the "+" button
            step.push(
                {
                    content: `Verify the quantity of "${productName}" is updated to ${i}.`,
                    trigger: `.optional-product-line .cart-buttons input:value("${i}")`,
                },
                {
                    content: `Increase the quantity of "${productName}" by clicking the "+" button.`,
                    trigger: `.optional-product-line .cart-buttons button:eq(1)`,
                    run: "click",
                }
            );
        }
        step.push({
            content: `Click the "Add" button to confirm adding "${productName}" to the order.`,
            trigger: `.modal-footer button:contains("Add")`,
            run: "click",
        });

        return step;
    }
}
