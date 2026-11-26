import { expect, test } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ResPartner } from "@point_of_sale/app/models/res_partner";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

definePosModels();

test("PartnerList skips exactMatch on empty query, uses normalized searchString, and caps at 50 matches", async () => {
    const store = await setupPosEnv();
    const accented = store.models["res.partner"].create({
        id: 1001,
        name: "Élodie Café",
        barcode: "PARTNER-1001",
    });
    for (let i = 0; i < 60; i++) {
        store.models["res.partner"].create({
            id: 2000 + i,
            name: `Bulk Match ${i}`,
        });
    }

    let exactMatchCalls = 0;
    patchWithCleanup(ResPartner.prototype, {
        exactMatch(searchWord) {
            exactMatchCalls++;
            return super.exactMatch(searchWord);
        },
    });

    const comp = await mountWithCleanup(PartnerList, {
        props: {
            partner: accented,
            getPayload: () => {},
            close: () => {},
        },
    });

    expect(exactMatchCalls).toBe(0);
    expect(accented.searchString).toBe("elodie cafe partner-1001");

    comp.state.query = "elodie";
    const accentResults = comp.getPartners(comp.state.initialPartners);
    expect(accentResults.map((p) => p.id)).toEqual([1001]);

    comp.state.query = "PARTNER-1001";
    const barcodeResults = comp.getPartners(comp.state.initialPartners);
    expect(barcodeResults.map((p) => p.id)).toEqual([1001]);

    accented.barcode = "CAFÉ-1001";
    comp.state.query = "cafe-1001";
    expect(comp.getPartners(comp.state.initialPartners).map((p) => p.id)).toEqual([1001]);

    comp.state.query = "Bulk Match";
    let searchStringReads = 0;
    const spiedPartners = comp.state.initialPartners.filter((p) => p.id >= 2000);
    for (const partner of spiedPartners) {
        const origDesc = Object.getOwnPropertyDescriptor(ResPartner.prototype, "searchString");
        Object.defineProperty(partner, "searchString", {
            get() {
                searchStringReads++;
                return origDesc.get.call(this);
            },
            configurable: true,
        });
    }
    const capped = comp.getPartners(spiedPartners);
    expect(capped.length).toBe(50);
    expect(searchStringReads).toBe(50);
});
