/** @odoo-module **/

import { Cache } from "@web/core/utils/cache";
import { makeDeferred, nextTick } from "../helpers/utils";

QUnit.module("utils", () => {
    QUnit.module("cache");

    QUnit.test("do not call getValue if already cached", async (assert) => {
        const cache = new Cache((key) => {
            assert.step(key);
            return key.toUpperCase();
        });

        assert.strictEqual(cache.read("a"), "A");
        assert.strictEqual(cache.read("b"), "B");
        assert.strictEqual(cache.read("a"), "A");

        assert.verifySteps(["a", "b"]);
    });

    QUnit.test("multiple cache key", async (assert) => {
        const cache = new Cache((...keys) => assert.step(keys.join("-")));

        cache.read("a", 1);
        cache.read("a", 2);
        cache.read("a", 1);

        assert.verifySteps(["a-1", "a-2"]);
    });

    QUnit.test("compute key", async (assert) => {
        const cache = new Cache(
            (key) => assert.step(key),
            (key) => key.toLowerCase()
        );

        cache.read("a");
        cache.read("A");

        assert.verifySteps(["a"]);
    });

    QUnit.test("cache promise", async (assert) => {
        const cache = new Cache((key) => {
            assert.step(`read ${key}`);
            return makeDeferred();
        });

        cache.read("a").then((k) => assert.step(`then ${k}`));
        cache.read("b").then((k) => assert.step(`then ${k}`));
        cache.read("a").then((k) => assert.step(`then ${k}`));
        cache.read("a").resolve("a");
        cache.read("b").resolve("b");
        await nextTick();

        assert.verifySteps(["read a", "read b", "then a", "then a", "then b"]);
    });

    QUnit.test("clear cache", async (assert) => {
        const cache = new Cache((key) => assert.step(key));

        cache.read("a");
        cache.read("b");
        assert.verifySteps(["a", "b"]);

        cache.read("a");
        cache.read("b");
        assert.verifySteps([]);

        cache.clear("a");
        cache.read("a");
        cache.read("b");
        assert.verifySteps(["a"]);

        cache.clear();
        cache.read("a");
        cache.read("b");
        assert.verifySteps([]);

        cache.invalidate();
        cache.read("a");
        cache.read("b");
        assert.verifySteps(["a", "b"]);
    });
});
