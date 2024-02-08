import { expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";

import { Cache } from "@web/core/utils/cache";

test.tags("headless")("do not call getValue if already cached", () => {
    const cache = new Cache((key) => {
        expect.step(key);
        return key.toUpperCase();
    });

    expect(cache.read("a")).toBe("A");
    expect(cache.read("b")).toBe("B");
    expect(cache.read("a")).toBe("A");

    expect(["a", "b"]).toVerifySteps();
});

test.tags("headless")("multiple cache key", async () => {
    const cache = new Cache((...keys) => expect.step(keys.join("-")));

    cache.read("a", 1);
    cache.read("a", 2);
    cache.read("a", 1);

    expect(["a-1", "a-2"]).toVerifySteps();
});

test.tags("headless")("compute key", async () => {
    const cache = new Cache(
        (key) => expect.step(key),
        (key) => key.toLowerCase()
    );

    cache.read("a");
    cache.read("A");

    expect(["a"]).toVerifySteps();
});

test.tags("headless")("cache promise", async () => {
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

    expect(["read a", "read b", "then a", "then a", "then b"]).toVerifySteps();
});

test.tags("headless")("clear cache", async () => {
    const cache = new Cache((key) => expect.step(key));

    cache.read("a");
    cache.read("b");
    expect(["a", "b"]).toVerifySteps();

    cache.read("a");
    cache.read("b");
    expect([]).toVerifySteps();

    cache.clear("a");
    cache.read("a");
    cache.read("b");
    expect(["a"]).toVerifySteps();

    cache.clear();
    cache.read("a");
    cache.read("b");
    expect([]).toVerifySteps();

    cache.invalidate();
    cache.read("a");
    cache.read("b");
    expect(["a", "b"]).toVerifySteps();
});
