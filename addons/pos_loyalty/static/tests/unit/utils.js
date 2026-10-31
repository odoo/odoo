import { signal } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

export const addProductLineToOrder = async (
    store,
    order,
    { templateId = 60, productId = 60, qty = 1, price_unit = 10, ...extraFields } = {}
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

    const line = await store.addLineToOrder(lineData, order, {}, false);

    return line;
};

export const deactivateAllProgramsExcept = (store, keepIds) => {
    const to_delete = store.models["loyalty.program"]
        .getAllIds()
        .filter((id) => !keepIds.includes(id));
    store.models["loyalty.program"].deleteMany(store.models["loyalty.program"].readMany(to_delete));
};

/**
 * Mock an access-right getter with a reactive signal for tests.
 * Call `.set(value)` on the returned signal to change the permission
 * and trigger reactive UI updates.
 */
export function mockAccessRight(store, getterName, initialValue = store.accessRight[getterName]) {
    const value = signal(initialValue);

    patch(store.accessRight, {
        get [getterName]() {
            return value();
        },
    });

    return value;
}
