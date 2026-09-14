import { defineMailModels, start, startServer } from "@mail/../tests/mail_test_helpers";
import {
    BASE_IM_STATUSES,
    baseImStatus,
    reachableDecoratedImStatuses,
    registeredImStatusDecorations,
    registerImStatusDecoration,
} from "@mail/core/common/presence_status";
import { describe, expect, test } from "@odoo/hoot";
import { getService } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");
defineMailModels();

test("mail's own words are their own base", () => {
    for (const status of BASE_IM_STATUSES) {
        expect(baseImStatus(status)).toBe(status);
    }
});

test("a word nobody has claimed passes through unchanged", () => {
    for (const status of ["bot", "im_partner", "agent", "something_new"]) {
        expect(baseImStatus(status)).toBe(status);
    }
});

test("a missing status is returned as it came", () => {
    expect(baseImStatus(undefined)).toBe(undefined);
    expect(baseImStatus(false)).toBe(false);
});

test("a registered decoration resolves to its base word", () => {
    registerImStatusDecoration("testzone_offline", "offline");
    registerImStatusDecoration("testzone_online", "online");
    expect(baseImStatus("testzone_offline")).toBe("offline");
    expect(baseImStatus("testzone_online")).toBe("online");
    expect(reachableDecoratedImStatuses()).toInclude("testzone_online");
    expect(reachableDecoratedImStatuses()).not.toInclude("testzone_offline");
});

test("every registration resolves to a word mail itself knows", () => {
    for (const [decorated, base] of registeredImStatusDecorations()) {
        expect(BASE_IM_STATUSES).toInclude(base, { message: decorated });
    }
});

test("a base word mail does not know is refused at registration", () => {
    expect(() =>
        registerImStatusDecoration("testzone_elsewhere", "elsewhere"),
    ).toThrow();
});

test("a decorated offline status still stamps offline_since", async () => {
    // presence_mixin.updateImStatus records when someone went offline. Compared
    // against the literal "offline" it never fires for a decorated status, so
    // "last seen" stays empty for every employee with a work location.
    registerImStatusDecoration("teststamp_offline", "offline");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Decorated" });
    await start();
    const store = getService("mail.store");
    const partner = store["res.partner"].insert({ id: partnerId });
    expect(partner.offline_since).toBe(undefined);
    partner.updateImStatus("teststamp_offline");
    expect(partner.im_status).toBe("teststamp_offline");
    expect(partner.offline_since).not.toBe(undefined);
});
