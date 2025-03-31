import { describe, expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";

import { Cache } from "@web/core/utils/cache";

describe.current.tags("headless");

test("do not call getValue if already cached", () => {
    const cache = new Cache((key) => {
        expect.step(key);
        return key.toUpperCase();
    });

    expect(cache.read("a")).toBe("A");
    expect(cache.read("b")).toBe("B");
    expect(cache.read("a")).toBe("A");

    expect.verifySteps(["a", "b"]);
});

test("multiple cache key", async () => {
    const cache = new Cache((...keys) => expect.step(keys.join("-")));

    cache.read("a", 1);
    cache.read("a", 2);
    cache.read("a", 1);

    expect.verifySteps(["a-1", "a-2"]);
});

test("compute key", async () => {
    const cache = new Cache(
        (key) => expect.step(key),
        (key) => key.toLowerCase()
    );

    cache.read("a");
    cache.read("A");

    expect.verifySteps(["a"]);
});

test("cache promise", async () => {
    const cache = new Cache((key) => {
        expect.step(`read ${key}`);
        return new Deferred();
    });

    cache.read("a").then((k) => expect.step(`then ${k}`));
    cache.read("b").then((k) => expect.step(`then ${k}`));
    cache.read("a").then((k) => expect.step(`then ${k}`));
    cache.read("a").resolve("a");
    cache.read("b").resolve("b");

    await Promise.resolve();

    expect.verifySteps(["read a", "read b", "then a", "then a", "then b"]);
});

test("clear cache", async () => {
    const cache = new Cache((key) => expect.step(key));

    cache.read("a");
    cache.read("b");
    expect.verifySteps(["a", "b"]);

    cache.read("a");
    cache.read("b");
    expect.verifySteps([]);

    cache.clear("a");
    cache.read("a");
    cache.read("b");
    expect.verifySteps(["a"]);

    cache.clear();
    cache.read("a");
    cache.read("b");
    expect.verifySteps([]);

    cache.invalidate();
    cache.read("a");
    cache.read("b");
    expect.verifySteps(["a", "b"]);
});
