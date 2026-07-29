import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

definePosModels();

const mountPartnerList = async () =>
    await mountWithCleanup(PartnerList, {
        props: {
            getPayload: () => {},
            close: () => {},
        },
    });

test("countFields", async () => {
    await setupPosEnv();
    const comp = await mountPartnerList();

    const partner = {
        email: "test",
        phone: "test",
        name: "test",
        city: "test",
        country_id: 1,
        state_id: 1,
        street: "test",
        street2: "test",
        zip: "test",
    };

    expect(comp.countFields(partner)).toBe(9);

    partner.email = "";
    partner.phone = false;
    partner.name = null;
    partner.city = undefined;
    expect(comp.countFields(partner)).toBe(5);
});

test("isRicherThan", async () => {
    await setupPosEnv();
    const comp = await mountPartnerList();

    const richer = {
        email: "test",
        phone: "test",
        name: "test",
    };

    const poorer = {
        email: "test",
    };

    expect(comp.isRicherThan(richer, poorer)).toBe(true);
    expect(comp.isRicherThan(poorer, richer)).toBe(false);
    expect(comp.isRicherThan(richer, richer)).toBe(false);
});

test("getDeduplicationKey", async () => {
    await setupPosEnv();
    const comp = await mountPartnerList();

    const savedMathRandom = Math.random;
    Math.random = () => 0.123456789; // toString(36) = 0.4fzzzxjylrx

    // total_due > 0 — unique key each time, just check the format
    const key1 = comp.getDeduplicationKey({ total_due: 100 });
    expect(key1).toBe("id:4fzzz");

    // email takes priority
    const key2 = comp.getDeduplicationKey({ email: "Test@Example.COM", phone: "0123456789" });
    expect(key2).toBe("email:test@example.com");

    // email normalization
    const key3 = comp.getDeduplicationKey({ email: "  test@example.com  " });
    expect(key3).toBe("email:test@example.com");

    // phone fallback when no email
    const key4 = comp.getDeduplicationKey({ phone: "+32 472 12 34 56" });
    expect(key4).toBe("phone:32472123456");

    // name fallback when no email or phone
    const key5 = comp.getDeduplicationKey({ name: "John Doe" });
    expect(key5).toBe("name:john doe");

    // unknown fallback
    const key6 = comp.getDeduplicationKey({});
    expect(key6).toBe("name:__unknown__");

    Math.random = savedMathRandom;
});

test("mergeBatch", async () => {
    await setupPosEnv();
    const comp = await mountPartnerList();

    // helper
    let idCounter = 1;
    const makePartner = (data) => ({ id: idCounter++, exactMatch: () => {}, ...data });

    // basic merge — two unique partners
    comp.state.partners.clear();
    const partnerA = makePartner({ email: "a@test.com", name: "Alice" });
    const partnerB = makePartner({ email: "b@test.com", name: "Bob" });
    const result1 = comp.mergeBatch([partnerA, partnerB]);
    expect(comp.state.partners.size).toBe(2);
    expect(result1).toEqual([partnerA, partnerB]);

    // duplicate email — richer one wins
    const poorer = makePartner({ email: "a@test.com" });
    const richer = makePartner({ email: "a@test.com", name: "Alice", phone: "0123456789" });
    comp.state.partners.clear();
    const result2 = comp.mergeBatch([poorer, richer]);
    expect(comp.state.partners.size).toBe(1);
    expect(comp.state.partners.get("email:a@test.com")).toEqual(richer);
    expect(result2).toEqual([richer]);

    // incremental — merging a new batch on top of existing state
    comp.state.partners.clear();
    comp.mergeBatch([partnerA]);
    const richerA = makePartner({ email: "a@test.com", name: "Alice", phone: "0123456789" });
    const result3 = [...comp.mergeBatch([richerA, partnerB])];
    expect(comp.state.partners.size).toBe(2);
    expect(comp.state.partners.get("email:a@test.com")).toEqual(richerA);
    expect(comp.state.partners.get("email:b@test.com")).toEqual(partnerB);
    expect(result3).toEqual([richerA, partnerB]);

    // no new richer partner — state should remain unchanged
    const result4 = comp.mergeBatch([poorer]);
    expect(comp.state.partners.size).toBe(2);
    expect(comp.state.partners.get("email:a@test.com")).toEqual(richerA);
    expect(comp.state.partners.get("email:b@test.com")).toEqual(partnerB);
    expect(result4).toBeEmpty();
});

test("initPartnerLoad", async () => {
    await setupPosEnv();
    const comp = await mountPartnerList();

    // helpers
    let idCounter = 1;
    const makePartner = (email, nonTrade = false) => ({
        id: idCounter++,
        email,
        property_account_receivable_id: nonTrade ? { non_trade: true } : null,
        exactMatch: () => {},
    });

    const makePartners = (count, prefix = "p") =>
        Array.from({ length: count }, (_, i) => makePartner(`${prefix}${i}@test.com`));

    // --- case 1: non_trade partners are filtered out ---
    comp.pos.models["res.partner"] = [
        makePartner("kept@test.com", false),
        makePartner("excluded@test.com", true),
    ];
    comp.getNewPartners = async () => [];
    comp.state.partners.clear();

    await comp.initPartnerLoad();
    expect(comp.state.partners.has("email:kept@test.com")).toBe(true);
    expect(comp.state.partners.has("email:excluded@test.com")).toBe(false);

    // --- case 2: stops fetching when partners.size >= 25 ---
    comp.pos.models["res.partner"] = makePartners(10);
    let fetchCount = 0;
    comp.getNewPartners = async () => comp.mergeBatch(makePartners(10, `batch${fetchCount++}-`));
    comp.state.partners.clear();

    await comp.initPartnerLoad();
    expect(fetchCount).toBe(2);
    expect(comp.state.partners.size).toBe(30);

    // --- case 3: stops when batch is empty ---
    comp.getNewPartners = async () => {
        fetchCount++;
        return [];
    };
    fetchCount = 0;
    comp.state.partners.clear();

    await comp.initPartnerLoad();
    expect(fetchCount).toBe(1);
    expect(comp.state.partners.size).toBe(10);

    // --- case 4: safeCount cap — never infinite loops ---
    comp.getNewPartners = async () => comp.mergeBatch(makePartners(1, `batch${fetchCount++}-`));
    fetchCount = 0;
    comp.state.partners.clear();

    await comp.initPartnerLoad();
    expect(fetchCount).toBe(10);
    expect(comp.state.partners.size).toBe(20);
});
