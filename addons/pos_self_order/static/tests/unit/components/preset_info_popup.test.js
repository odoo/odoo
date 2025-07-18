import { test, describe, expect, beforeEach } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { PresetInfoPopup } from "@pos_self_order/app/components/preset_info_popup/preset_info_popup";
import { setupSelfPosEnv, patchSession, getFilledSelfOrder } from "../utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();
beforeEach(patchSession);

describe("preset_info_popup", () => {
    test("validSelection", async () => {
        const store = await setupSelfPosEnv();
        store.config.company_id.country_id.state_ids = [];
        const models = store.models;

        const order = await getFilledSelfOrder(store);
        const preset = models["pos.preset"].get(10);
        order.preset_id = preset;
        const comp = await mountWithCleanup(PresetInfoPopup, { props: { callback: () => {} } });
        // name
        preset.identification = "name";
        preset.mail_template_id = false;
        expect(comp.validSelection).toBeEmpty();
        comp.state.name = "Good Person";
        expect(Boolean(comp.validSelection)).toBe(true);
        // mail
        preset.mail_template_id = models["mail.template"].get(10);
        expect(comp.validSelection).toBeEmpty();
        comp.state.email = "good.person@odoo.com";
        expect(Boolean(comp.validSelection)).toBe(true);
        // slots
        preset.use_timing = true;
        expect(comp.validSelection).toBeEmpty();
        comp.state.selectedSlot = "2025-07-30 14:25:21";
        expect(Boolean(comp.validSelection)).toBe(true);
        // Partner
        preset.identification = "address";
        expect(comp.validSelection).toBeEmpty();
        comp.state.phone = "987-654-3210";
        comp.state.street = "21, Wonderfull Street";
        comp.state.city = "Vice City";
        comp.state.zip = "000021";
        expect(Boolean(comp.validSelection)).toBe(true);
    });
});
