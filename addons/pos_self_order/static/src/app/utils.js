export const attributeFlatter = (attribute) =>
    Object.values(attribute)
        .map((v) => {
            if (v instanceof Object) {
                return Object.entries(v)
                    .filter((v) => v[1])
                    .map((v) => v[0]);
            } else {
                return v;
            }
        })
        .flat()
        .map((v) => parseInt(v));

export const formatProductName = (product) => {
    const attributes = product.product_template_attribute_value_ids?.map((v) => v.name).join(",");
    return attributes ? `${product.name} (${attributes})` : product.name;
};

export const shouldShowMissingDetails = (product, selectedValues, scrollContainerRef) => {
    if (!product || !product.attribute_line_ids.length) {
        return false;
    }

    const scrollContainerEl = scrollContainerRef?.el;
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
