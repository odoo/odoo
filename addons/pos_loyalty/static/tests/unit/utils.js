export const addProductLineToOrder = async (
    store,
    order,
<<<<<<< 3b5ffdc4184b25128fa8204bccffcce82cad345e
    { templateId = 60, productId = 60, qty = 1, price_unit = 10, ...extraFields } = {},
    opts = {}
||||||| df947972f49099b7cd5638f4d277f36d19339b2c
    { templateId = 1, productId = 1, qty = 1, price_unit = 10, ...extraFields } = {}
=======
    { templateId = 1, productId = 1, qty = 1, price_unit = 10, ...extraFields } = {},
    opts = {}
>>>>>>> 5c7cedf731ae735be0ce2fdd1edd306f3230697c
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

<<<<<<< 3b5ffdc4184b25128fa8204bccffcce82cad345e
    const line = await store.addLineToOrder(lineData, order, opts, false);
||||||| df947972f49099b7cd5638f4d277f36d19339b2c
    const line = await store.addLineToOrder(lineData, order);
=======
    const line = await store.addLineToOrder(lineData, order, opts);
>>>>>>> 5c7cedf731ae735be0ce2fdd1edd306f3230697c

    return line;
};

export const deactivateAllProgramsExcept = (store, keepIds) => {
    const to_delete = store.models["loyalty.program"]
        .getAllIds()
        .filter((id) => !keepIds.includes(id));
    store.models["loyalty.program"].deleteMany(store.models["loyalty.program"].readMany(to_delete));
};
