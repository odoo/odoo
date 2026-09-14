import { describe, expect, test } from "@odoo/hoot";
import { workLocationPresence } from "@hr_homeworking/work_location_presence";

describe.current.tags("headless");

test("every location and every presence word is recognised", () => {
    for (const [location, icon] of [
        ["home", "fa-solid fa-house"],
        ["office", "fa-solid fa-building"],
        ["other", "fa-solid fa-location-dot"],
    ]) {
        for (const [status, color] of [
            ["online", "text-success"],
            ["away", "o-yellow"],
            ["busy", "text-danger"],
            ["offline", "text-body"],
        ]) {
            const presence = workLocationPresence(`${location}_${status}`);
            expect(presence).not.toBe(null, {
                message: `${location}_${status} is a located status`,
            });
            expect(presence.icon).toBe(icon);
            expect(presence.color).toBe(color);
        }
    }
});

test("a status another module owns is left to it", () => {
    for (const status of [
        "leave_online",
        "leave_away",
        "leave_busy",
        "leave_offline",
        "agent",
    ]) {
        expect(workLocationPresence(status)).toBe(null, { message: status });
    }
});

test("a plain status is not a located one", () => {
    for (const status of ["online", "away", "busy", "offline", "bot", "im_partner"]) {
        expect(workLocationPresence(status)).toBe(null, { message: status });
    }
});

test("a missing status is not a located one", () => {
    expect(workLocationPresence(undefined)).toBe(null);
    expect(workLocationPresence(false)).toBe(null);
    expect(workLocationPresence("")).toBe(null);
    expect(workLocationPresence("home_")).toBe(null);
    expect(workLocationPresence("home_elsewhere")).toBe(null);
});
