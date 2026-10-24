import { expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

async function search(query, assertDomain) {
    const partnerList = Object.create(PartnerList.prototype);
    partnerList.state = { query, currentOffset: 30 };
    partnerList.pos = {
        data: {
            async searchRead(model, domain, fields, options) {
                expect(model).toBe("res.partner");
                expect(fields).toEqual([]);
                expect(options).toEqual({ limit: 30, offset: 30 });
                assertDomain(domain);
                return [{ id: 1 }];
            },
        },
    };
    expect(await partnerList.getNewPartners()).toEqual([{ id: 1 }]);
}

test("ordinary contact fields retain their search wildcard", async () => {
    await search("123", (domain) => {
        expect(domain).toInclude(["phone", "ilike", "123%"]);
        expect(domain).toInclude(["mobile", "ilike", "123%"]);
        expect(domain).toInclude(["name", "ilike", "123%"]);
    });
});

for (const query of ["12", "+32 485 11 22 33"]) {
    test(`phone search receives the original query ${query}`, async () => {
        // POS SMS uses the phone mixin's search field, which adds its own wildcards
        // and validates the length of the original query.
        patchWithCleanup(PartnerList.prototype, {
            getPhoneSearchTerms() {
                return ["phone_mobile_search"];
            },
        });
        await search(query, (domain) => {
            expect(domain).toInclude(["phone_mobile_search", "ilike", query]);
            expect(domain).toInclude(["name", "ilike", `${query}%`]);
            expect(domain).toInclude(["email", "ilike", `${query}%`]);
        });
    });
}

test("empty partner search keeps an empty domain", async () => {
    await search("", (domain) => expect(domain).toEqual([]));
});
