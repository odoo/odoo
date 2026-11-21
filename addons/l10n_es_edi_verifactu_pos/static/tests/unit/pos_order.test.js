import { expect, test } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("payment can't be edited when Veri*Factu is required", async () => {
    const store = await setupPosEnv();
    const company = store.config.company_id;
    // Also blocked by l10n_at_pos when installed (enterprise)
    company.l10n_at_is_fon_authenticated = false;
    company.l10n_es_edi_verifactu_required = false;
    const order = await getFilledOrder(store);
    order.state = "paid";
    expect(order.canEditPayment).toBe(true);

    company.l10n_es_edi_verifactu_required = true;
    expect(order.canEditPayment).toBe(false);
    expect(store.canEditPayment(order)).toBe(false);
});
