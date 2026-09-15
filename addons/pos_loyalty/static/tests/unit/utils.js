export const addProductLineToOrder = async (
    store,
    order,
    { templateId = 1, productId = 1, qty = 1, price_unit = 10, ...extraFields } = {},
    opts = {}
) => {
    const template = store.models["product.template"].get(templateId);
    const product = store.models["product.product"].get(productId);

    const lineData = {
        product_tmpl_id: template,
        product_id: product,
        qty,
        price_unit,
        ...extraFields,
    };

    const line = await store.addLineToOrder(lineData, order, opts);

    return line;
};

export const deactivateAllProgramsExcept = (store, keepIds) => {
    const to_delete = store.models["loyalty.program"]
        .getAllIds()
        .filter((id) => !keepIds.includes(id));
    store.models["loyalty.program"].deleteMany(store.models["loyalty.program"].readMany(to_delete));
};
