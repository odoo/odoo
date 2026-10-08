import { test, expect } from "@odoo/hoot";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
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
    const preset = models["pos.preset"].get(10);
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

test("validated partner keeps the form values locally", async () => {
    const store = await setupSelfPosEnv();
    store.config.company_id.country_id.state_ids = [];
    store.config.company_id.country_id.phone_code = 1;
    const models = store.models;

    const order = await getFilledSelfOrder(store);
    const preset = models["pos.preset"].get(10);
    preset.identification = "address";
    order.preset_id = preset;
    const comp = await mountWithCleanup(PresetInfoPopup, {
        props: { close: () => {}, getPayload: () => {} },
    });
    comp.state.name = "Demo User";
    comp.state.email = "demo@odoo.com";
    comp.state.phoneLocal = "2025551234";
    comp.state.street = "Chaussée de Namur 40";
    comp.state.city = "Ramillies";
    comp.state.zip = "1367";

    const signedPartnerId = "7-0123456789abcdef";
    onRpc("/pos-self-order/validate-partner", () => ({
        "res.partner": [{ id: signedPartnerId }],
    }));
    await comp.setInformations();

    const partner = order.partner_id;
    expect(partner.id).toBe(signedPartnerId);
    expect(partner.name).toBe("Demo User");
    expect(partner.email).toBe("demo@odoo.com");
    expect(partner.phone).toBe("+12025551234");
    expect(partner.street).toBe("Chaussée de Namur 40");
    expect(partner.city).toBe("Ramillies");
    expect(partner.zip).toBe("1367");
    expect(partner.country_id?.id).toBe(store.config.company_id.country_id.id);

    const generator = store.ticketPrinter.getGenerator({ models, order });
    const receipt = generator.generateReceiptData();
    expect(receipt.partner.name).toBe("Demo User");
    expect(receipt.partner.street).toBe("Chaussée de Namur 40");
});
