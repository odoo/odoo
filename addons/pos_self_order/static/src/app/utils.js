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
