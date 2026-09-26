import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { PresetInfoPopup } from "@pos_self_order/app/components/preset_info_popup/preset_info_popup";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("validSelection", async () => {
    const store = await setupSelfPosEnv();
    store.config.company_id.country_id.state_ids = [];
    store.config.company_id.country_id.phone_code = 1;
    const models = store.models;

    const order = await getFilledSelfOrder(store);
    const preset = models["pos.preset"].get(1);
    order.preset_id = preset;
    const comp = await mountWithCleanup(PresetInfoPopup, {
        props: { close: () => {}, getPayload: () => {} },
    });
    // none
    preset.identification = "none";
    expect(Boolean(comp.validSelection)).toBe(true);
    // name
    preset.identification = "name";
    expect(comp.validSelection).toBeEmpty();
    comp.state.name = "Good Person";
    expect(Boolean(comp.validSelection)).toBe(true);
    // mail
    preset.mail_template_id = 21;
    expect(comp.validSelection).toBeEmpty();
    comp.state.email = "good.person@odoo.com";
    expect(Boolean(comp.validSelection)).toBe(true);
    // Partner
    preset.identification = "address";
    expect(comp.validSelection).toBeEmpty();
    comp.state.phoneLocal = "2025551234";
    comp.state.street = "21, Wonderfull Street";
    comp.state.city = "Vice City";
    comp.state.zip = "000021";
    expect(Boolean(comp.validSelection)).toBe(true);
});

test("floating_order_name is always the entered name, with or without a partner", async () => {
    const store = await setupSelfPosEnv();
    store.config.company_id.country_id.state_ids = [];
    store.config.company_id.country_id.phone_code = 1;
    const models = store.models;

    const order = await getFilledSelfOrder(store);
    const preset = models["pos.preset"].get(1);
    order.preset_id = preset;
    const comp = await mountWithCleanup(PresetInfoPopup, {
        props: { close: () => {}, getPayload: () => {} },
    });

    // No partner is created for a preset that only asks for a name.
    preset.identification = "none";
    comp.state.name = "Alex";
    await comp.setInformations();
    expect(store.currentOrder.floating_order_name).toBe("Alex");
    expect(Boolean(store.currentOrder.partner_id)).toBe(false);

    // A partner is created for a preset that asks for an address, but
    // floating_order_name still gets the entered name too.
    preset.identification = "address";
    comp.state.name = "Jordan";
    comp.state.phoneLocal = "2025551234";
    comp.state.street = "21, Wonderfull Street";
    comp.state.city = "Vice City";
    comp.state.zip = "000021";
    await comp.setInformations();
    expect(store.currentOrder.floating_order_name).toBe("Jordan");
    expect(store.currentOrder.partner_id).not.toBe(false);
    expect(store.currentOrder.partner_id.name).toBe("Jordan");
});
