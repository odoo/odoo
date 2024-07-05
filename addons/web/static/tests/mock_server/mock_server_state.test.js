import { describe, expect, test } from "@odoo/hoot";
import { serverState } from "@web/../tests/web_test_helpers";

import { user } from "@web/core/user";
import { session } from "@web/session";

describe.current.tags("headless");

test("default state", () => {
    expect(odoo.debug).toBe("");
    const s = { ...serverState };
    expect("view_info" in s).toBe(true);
    delete s.view_info;
    expect(s).toEqual({
        companies: [{ id: 1, name: "Hermit" }],
        currencies: [
            { id: 1, name: "USD", position: "before", symbol: "$" },
            { id: 2, name: "EUR", position: "after", symbol: "€" },
        ],
        db: "test",
        debug: "",
        groupId: 11,
        lang: "en",
        multiLang: false,
        odoobotId: 418,
        partnerId: 17,
        partnerName: "Mitchell Admin",
        publicPartnerId: 18,
        publicPartnerName: "Public user",
        publicUserId: 8,
        serverVersion: [1, 0, 0, "final", 0, ""],
        timezone: "taht",
        userContext: {},
        userId: 7,
    });
});

test("state changes should be reflected on user and session", () => {
    expect(serverState.userId).toBe(7);
    expect(user.userId).toBe(7);
    expect(session.uid).toBe(undefined); // deleted by `user.js`

    serverState.userId = 42;

    expect(serverState.userId).toBe(42);
    expect(user.userId).toBe(42);
    expect(session.uid).toBe(undefined);
});

test("sanity check: server state is unaffected by previous tests", () => {
    expect(serverState.userId).toBe(7);
    expect(user.userId).toBe(7);
    expect(session.uid).toBe(undefined);
});
