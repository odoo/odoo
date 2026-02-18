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

    // Get all attributes that are marked as required in the DOM
    const requiredAttributes = product.attribute_line_ids.filter((attr) => {
        const element = document.getElementById(attr.attribute_id.id);
        return element && element.hasAttribute("required");
    });

    // Check if any required attribute without a selection is scrolled above the viewport
    for (const attribute of requiredAttributes) {
        const hasSelection = selection?.hasValueSelected(attribute);

        if (!hasSelection) {
            const attributeEl = document.getElementById(attribute.attribute_id.id);
            if (attributeEl) {
                if (attributeEl.getBoundingClientRect().top < containerRect.top) {
                    return true;
                }
            }
        }
    }

    return false;
};
