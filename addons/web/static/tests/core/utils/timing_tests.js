/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { debounce } from "@web/core/utils/timing";
import { makeDeferred, patchWithCleanup } from "../../helpers/utils";

QUnit.module("utils", () => {
    QUnit.module("timing");

    QUnit.test("debounce on an async function", async function (assert) {
        let callback;
        patchWithCleanup(browser, {
            setTimeout: (later) => {
                callback = later;
            },
        });
        const imSearchDef = makeDeferred();
        const myFunc = () => {
            assert.step("myFunc");
            return imSearchDef;
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc().then(() => {
            throw new Error("Should never be resolved");
        });
        myDebouncedFunc().then((x) => {
            assert.step("resolved " + x);
        });
        assert.verifySteps([]);
        callback();
        assert.verifySteps(["myFunc"]);
        imSearchDef.resolve(42);
        await Promise.resolve(); // wait for promise returned by myFunc
        await Promise.resolve(); // wait for promise returned by debounce

        assert.verifySteps(["resolved 42"]);
    });

    QUnit.test("debounce on a sync function", async function (assert) {
        let callback;
        patchWithCleanup(browser, {
            setTimeout: (later) => {
                callback = later;
            },
        });
        const myFunc = () => {
            assert.step("myFunc");
            return 42;
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc().then(() => {
            throw new Error("Should never be resolved");
        });
        myDebouncedFunc().then((x) => {
            assert.step("resolved " + x);
        });
        assert.verifySteps([]);
        callback();
        assert.verifySteps(["myFunc"]);
        await Promise.resolve(); // wait for promise returned by myFunc
        await Promise.resolve(); // wait for promise returned by debounce

        assert.verifySteps(["resolved 42"]);
    });

    QUnit.test("debounce with immediate", async function (assert) {
        patchWithCleanup(browser, {
            setTimeout: (later) => {
                later();
            },
        });
        const myFunc = () => {
            assert.step("myFunc");
            return 42;
        };
        const myDebouncedFunc = debounce(myFunc, 3000, true);
        myDebouncedFunc().then((x) => {
            assert.step("resolved " + x);
        });
        assert.verifySteps(["myFunc"]);
        await Promise.resolve(); // wait for promise returned by myFunc
        await Promise.resolve(); // wait for promise returned by debounce

        assert.verifySteps(["resolved 42"]);
    });
});
