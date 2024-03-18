import { describe, expect, test } from "@odoo/hoot";
import { serverState } from "@web/../tests/web_test_helpers";

import { user } from "@web/core/user";
import { session } from "@web/session";

describe.current.tags("headless");

test("default state", () => {
    expect(odoo.debug).toBe(false);
    expect(serverState).toEqual({
        companies: [{ id: 1, name: "Hermit" }],
        debug: false,
        groupId: 11,
        lang: "en",
        multiLang: false,
        odoobotId: 418,
        partnerId: 17,
        partnerName: "Mitchell Admin",
        publicPartnerId: 18,
        publicPartnerName: "Public user",
        publicUserId: 8,
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
