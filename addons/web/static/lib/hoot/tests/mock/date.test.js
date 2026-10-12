/** @odoo-module */

import { advanceTime, describe, expect, freezeTime, mockDate, test } from "@odoo/hoot";
import { parseUrl } from "../local_helpers";

describe(parseUrl(import.meta.url), () => {
    test("mock date constructor with no arguments", async () => {
        const date = new Date();
        expect(date.getFullYear()).toBe(2019);
        expect(date.getMonth()).toBe(2);
        expect(date.getDate()).toBe(11);
        expect(date.getHours()).toBe(10);
        expect(date.getMinutes()).toBe(30);
        expect(date.getSeconds()).toBe(0);
        // Do not test milliseconds as they can vary
    });

    test("mock date constructor with no arguments and with time frozen", async () => {
        freezeTime();
        mockDate("2019-03-11 10:30:28.030"); // add milliseconds to mock date

        const date = new Date();
        expect(date.getFullYear()).toBe(2019);
        expect(date.getMonth()).toBe(2);
        expect(date.getDate()).toBe(11);
        expect(date.getHours()).toBe(10);
        expect(date.getMinutes()).toBe(30);
        expect(date.getSeconds()).toBe(28);
        expect(date.getMilliseconds()).toBe(30);
    });

    test("mock date constructor with a single timestamp argument", async () => {
        const date = new Date(/* 2026-07-09 10:10:55 */ 1783594500000);
        expect(date.getFullYear()).toBe(2026);
        expect(date.getMonth()).toBe(6);
        expect(date.getDate()).toBe(9);
        expect(date.getHours()).toBe(10);
        expect(date.getMinutes()).toBe(10);
        expect(date.getSeconds()).toBe(55);
        expect(date.getMilliseconds()).toBe(0);
    });

    test("mock date constructor with date argument", async () => {
        const date = new Date(2026, 6, 9);
        expect(date.getFullYear()).toBe(2026);
        expect(date.getMonth()).toBe(6);
        expect(date.getDate()).toBe(9);
        expect(date.getHours()).toBe(10);
        expect(date.getMinutes()).toBe(30);
        expect(date.getSeconds()).toBe(0);
    });

    test("mock date constructor with hour argument", async () => {
        freezeTime();

        const date = new Date(2026, 6, 9, 12);
        expect(date.getFullYear()).toBe(2026);
        expect(date.getMonth()).toBe(6);
        expect(date.getDate()).toBe(9);
        expect(date.getHours()).toBe(12);
        expect(date.getMinutes()).toBe(30);
        expect(date.getSeconds()).toBe(0);

        // Add 1 hour
        const offset = 60 * 60 * 1000;
        await advanceTime(offset);

        const otherDate = new Date(2026, 6, 9, 12, 25, 0, 20);
        expect(Number(date)).toBe(Number(otherDate) + offset);
    });

    test("mock date constructor with all arguments", async () => {
        const date = new Date(2026, 6, 9, 12, 25, 0, 420);
        expect(date.getFullYear()).toBe(2026);
        expect(date.getMonth()).toBe(6);
        expect(date.getDate()).toBe(9);
        expect(date.getHours()).toBe(12);
        expect(date.getMinutes()).toBe(25);
        expect(date.getSeconds()).toBe(0);
        expect(date.getMilliseconds()).toBe(420);

        // Add 1 hour
        await advanceTime(60 * 60 * 1000);

        expect(date).toEqual(new Date(2026, 6, 9, 12, 25, 0, 420), {
            message: "date with all 7 arguments shouldn't be offset",
        });
    });
});
