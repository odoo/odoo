export const formatProductName = (product) => {
    const attributes = product.product_template_attribute_value_ids?.map((v) => v.name).join(",");
    return attributes ? `${product.name} (${attributes})` : product.name;
};

export const shouldShowMissingDetails = (product, selectedValues) => {
    if (!product || !product.attribute_line_ids.length) {
        return false;
    }

    const scrollContainerEl = document.getElementById("o-self-scroll-container");
    if (!scrollContainerEl) {
        return false;
    }

    const containerRect = scrollContainerEl.getBoundingClientRect();
    const selection = selectedValues[product.id];

    return product.attribute_line_ids.some((attr) => {
        const attributeEl = document.getElementById(attr.attribute_id.id);

        return (
            attributeEl?.hasAttribute("attr-required") &&
            !selection?.hasValueSelected(attr) &&
            attributeEl.getBoundingClientRect().top < containerRect.top
        );
    });
};
