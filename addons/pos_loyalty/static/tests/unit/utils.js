export const addProductLineToOrder = async (
    store,
    order,
    { templateId = 1, productId = 1, qty = 1, price_unit = 10, ...extraFields } = {}
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

    const line = await store.addLineToOrder(lineData, order);

    return line;
};
