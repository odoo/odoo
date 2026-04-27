export function containsProduct(productName) {
    return [
        {
            content: "product screen is shown",
            trigger: `.o_pdis_product-name:contains("${productName}")`,
        },
    ];
}
