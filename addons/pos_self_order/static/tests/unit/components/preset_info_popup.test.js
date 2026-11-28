import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { PresetInfoPopup } from "@pos_self_order/app/components/preset_info_popup/preset_info_popup";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { animationFrame } from "@odoo/hoot-dom";

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

test("selectedCountry", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const usa = store.config.company_id.country_id;
    usa.state_ids = [];
    usa.phone_code = 1;
    const canada = models["res.country"].get(234);
    canada.phone_code = 1;

    const order = await getFilledSelfOrder(store);
    const preset = models["pos.preset"].get(10);
    preset.identification = "name";
    order.preset_id = preset;

    const comp = await mountWithCleanup(PresetInfoPopup, {
        props: { close: () => {}, getPayload: () => {} },
    });
    expect(comp.selectedCountry.id).toBe(usa.id);
    expect(".input-group div.form-control").toHaveText(`${comp.flagEmoji(usa.code)} +1`, {
        inline: true,
    });
    comp.state.phoneCountryId = canada.id;
    await animationFrame();
    expect(comp.selectedCountry.id).toBe(canada.id);
    expect(".input-group div.form-control").toHaveText(`${comp.flagEmoji(canada.code)} +1`, {
        inline: true,
    });
});
