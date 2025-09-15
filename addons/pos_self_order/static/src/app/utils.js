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
