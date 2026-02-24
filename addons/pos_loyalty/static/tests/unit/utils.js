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

    // If the line is marked as a reward but no reward_id was provided,
    // attach a default reward record from the loaded models to avoid
    // tests creating reward lines without a proper `reward_id`.
    if (lineData.is_reward_line && !lineData.reward_id) {
        const rewards = store.models["loyalty.reward"].getAll();
        if (rewards.length) {
            lineData.reward_id = rewards[0];
        }
    }

    const line = await store.addLineToOrder(lineData, order);

    return line;
};
