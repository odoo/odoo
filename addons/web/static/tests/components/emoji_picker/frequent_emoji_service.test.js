// @ts-check

import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

const KEY = "web.emoji.frequent";

beforeEach(() => {
    browser.localStorage.removeItem(KEY);
});

test("usage counts accumulate and persist", async () => {
    await makeMockEnv();
    const emoji = getService("web.frequent.emoji");
    emoji.incrementEmojiUsage("1f600");
    emoji.incrementEmojiUsage("1f600");
    emoji.incrementEmojiUsage("1f382");

    expect(emoji.all).toEqual({ "1f600": 2, "1f382": 1 });
    expect(JSON.parse(browser.localStorage.getItem(KEY))).toEqual({
        "1f600": 2,
        "1f382": 1,
    });
});

test("getMostFrequent sorts by descending usage and honours the limit", async () => {
    await makeMockEnv();
    const emoji = getService("web.frequent.emoji");
    for (const [codepoints, count] of /** @type {[string, number][]} */ ([
        ["a", 1],
        ["b", 5],
        ["c", 3],
    ])) {
        for (let i = 0; i < count; i++) {
            emoji.incrementEmojiUsage(codepoints);
        }
    }

    expect(emoji.getMostFrequent()).toEqual(["b", "c", "a"]);
    expect(emoji.getMostFrequent(2)).toEqual(["b", "c"]);
    expect(emoji.getMostFrequent(0)).toEqual([]);
});

test("a corrupt stored value degrades to an empty map instead of bricking the picker", async () => {
    for (const stored of ["null", "42", '"a string"', "[1,2]", "{not json"]) {
        browser.localStorage.setItem(KEY, stored);
        await makeMockEnv();
        const emoji = getService("web.frequent.emoji");
        expect(emoji.all).toEqual({}, { message: `stored: ${stored}` });
        expect(emoji.getMostFrequent()).toEqual([]);
    }
});

test("a storage write failure does not break emoji selection", async () => {
    await makeMockEnv();
    const emoji = getService("web.frequent.emoji");
    patchWithCleanup(browser.localStorage, {
        setItem() {
            throw new Error("QuotaExceededError");
        },
    });

    expect(() => emoji.incrementEmojiUsage("1f600")).not.toThrow();
    expect(emoji.all).toEqual(
        { "1f600": 1 },
        { message: "in-memory state still updated" },
    );
});

test("another tab's write is adopted", async () => {
    await makeMockEnv();
    const emoji = getService("web.frequent.emoji");
    emoji.incrementEmojiUsage("1f600");

    browser.dispatchEvent(
        Object.assign(new Event("storage"), {
            key: KEY,
            newValue: JSON.stringify({ "1f382": 7 }),
        }),
    );
    expect(emoji.all).toEqual({ "1f382": 7 });
});

test("another tab's localStorage.clear() resets the map", async () => {
    await makeMockEnv();
    const emoji = getService("web.frequent.emoji");
    emoji.incrementEmojiUsage("1f600");

    browser.dispatchEvent(
        Object.assign(new Event("storage"), { key: null, newValue: null }),
    );
    expect(emoji.all).toEqual({});
});

test("an unrelated storage key is ignored", async () => {
    await makeMockEnv();
    const emoji = getService("web.frequent.emoji");
    emoji.incrementEmojiUsage("1f600");

    browser.dispatchEvent(
        Object.assign(new Event("storage"), {
            key: "something.else",
            newValue: "{}",
        }),
    );
    expect(emoji.all).toEqual({ "1f600": 1 });
});

test("destroy detaches the cross-tab listener", async () => {
    await makeMockEnv();
    const emoji = getService("web.frequent.emoji");
    emoji.incrementEmojiUsage("1f600");
    emoji.destroy();

    browser.dispatchEvent(
        Object.assign(new Event("storage"), {
            key: KEY,
            newValue: JSON.stringify({ "1f382": 7 }),
        }),
    );
    expect(emoji.all).toEqual(
        { "1f600": 1 },
        { message: "a torn-down service no longer tracks other tabs" },
    );
});

test("tracked emojis are capped, and a newly used one is never the eviction", async () => {
    const seeded = {};
    for (let i = 0; i < 200; i++) {
        seeded[`e${i}`] = i + 1;
    }
    browser.localStorage.setItem(KEY, JSON.stringify(seeded));
    await makeMockEnv();
    const emoji = getService("web.frequent.emoji");
    expect(Object.keys(emoji.all).length).toBe(200);

    emoji.incrementEmojiUsage("newbie");

    const kept = Object.keys(emoji.all);
    expect(kept.length).toBe(200);
    expect(kept).not.toInclude("e0");
    expect(kept).toInclude("newbie");
    expect(kept).toInclude("e199");
});

test("a cross-tab update reaches a component watching the service", async () => {
    class Watcher extends Component {
        static template = xml`<div class="revision" t-out="this.emoji.revision"/>`;
        static props = ["*"];
        setup() {
            this.emoji = useState(useService("web.frequent.emoji"));
        }
    }
    await mountWithCleanup(Watcher);
    expect(".revision").toHaveText("0");

    browser.dispatchEvent(
        Object.assign(new Event("storage"), {
            key: KEY,
            newValue: JSON.stringify({ "😀": 3 }),
        }),
    );
    await animationFrame();

    expect(".revision").toHaveText("1");
    expect(getService("web.frequent.emoji").getMostFrequent()).toEqual(["😀"]);
});
