/** @odoo-module */

export const categorySorter = (a, b, start_categ_id) => {
    if (a.id === start_categ_id && b.id !== start_categ_id) {
        return -1; // 'a' should come before 'b'
    }
    if (a.id !== start_categ_id && b.id === start_categ_id) {
        return 1; // 'b' should come before 'a'
    }
    if (a.sequence !== b.sequence) {
        return a.sequence - b.sequence; // sort by sequence
    }
    return a.id - b.id; // sort by id if sequences are the same
};

export const attributeFormatter = (attrById, values, customValues = []) => {
    if (!values) {
        return [];
    }

    const attrVals = {};
    for (const attr of Object.values(attrById)) {
        for (const value of attr.values) {
            attrVals[value.id] = value;
        }
    }

    const selectedValue = Object.values(attrVals)
        .filter((attr) => values.includes(attr.id))
        .reduce((acc, val) => {
            let description = "";
            const attribute = attrById[val.attribute_id];
            const isCustomValue = Object.values(customValues).find(
                (cus) => cus.custom_product_template_attribute_value_id === val.id
            );

            if (isCustomValue && val.is_custom) {
                description = `: ${isCustomValue.custom_value}`;
            }

            if (!acc[attribute.id]) {
                acc[attribute.id] = {
                    id: attribute.id,
                    name: attribute.name,
                    value: val.name + description,
                    valueIds: [val.id],
                };
            } else {
                acc[attribute.id].value += `, ${val.name}${description}`;
                acc[attribute.id].valueIds.push(val.id);
            }

            return acc;
        }, {});

    return Object.values(selectedValue);
};

export const attributeFlatter = (attribute) => {
    return Object.values(attribute)
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
};
