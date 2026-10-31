import { createTestProduct } from "@point_of_sale/../tests/unit/utils";

export function createDeposit(store, { id, name, price }) {
    const { template, variant } = createTestProduct(store, { id, name, price });
    template.is_deposit = true;
    return variant;
}
