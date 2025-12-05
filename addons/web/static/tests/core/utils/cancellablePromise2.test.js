import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { getCancellableTask } from "@odoo/owl";
import { delay } from "@web/core/utils/concurrency";

const steps = [];
beforeEach(() => {
    steps.length = 0;
});
function step(message) {
    steps.push(message);
}
function verifySteps(expectedSteps) {
    expect(steps).toEqual(expectedSteps);
    steps.length = 0;
}

const deffereds = {};
const deferred = (key) => {
    deffereds[key] ||= Promise.withResolvers();
    return deffereds[key].promise;
};
const resolve = async (key) => {
    deffereds[key] ||= Promise.withResolvers();
    deffereds[key].resolve(key);
    await delay();
    return;
};
beforeEach(() => {
    for (const key in deffereds) {
        delete deffereds[key];
    }
});

describe.only("cancellablePromise2", () => {
    const prepare = (execSubFunctionMethod = "call") => {
        const deffereds = {};
        const deferred = (key) => {
            deffereds[key] ||= Promise.withResolvers();
            return deffereds[key].promise;
        };
        const resolve = async (key) => {
            deffereds[key] ||= Promise.withResolvers();
            deffereds[key].resolve(key);
            await delay();
            return;
        };

        return {
            resolve,
            getPromise: async () => {
                let result;
                expect.step("a before");
                result = await deferred("a value");
                expect.step(`a after:${result}`);
                const genFunction = async () => {
                    let result;
                    expect.step("b.1 before");
                    result = await deferred("b.1 value");
                    expect.step(`b.1 after:${result}`);
                    const genFunction = async () => {
                        let result;
                        expect.step("b.1.1 before");
                        result = await deferred("b.1.1 value");
                        expect.step(`b.1.1 after:${result}`);
                        result = await deferred("b.1.2 value");
                        expect.step(`b.1.2 after:${result}`);
                        return result;
                    };
                    result = await genFunction();
                    expect.step(`sub-sub gen result:${result}`);
                    result = await deferred("b.2 value");
                    expect.step(`b.2 after:${result}`);
                    return result;
                };
                result = await genFunction();
                expect.step(`sub gen result:${result}`);
                result = await deferred("b value");
                expect.step(`b after:${result}`);
            },
        };
    };
    test("should cancel in a sub generator", async () => {
        const { getPromise, resolve } = prepare();
        const context = getCancellableTask(() => getPromise());
        console.warn(`context:`, context);
        expect.verifySteps(["a before"]);
        await resolve("a value");
        expect.verifySteps(["a after:a value", "b.1 before"]);
        await resolve("b.1 value");
        expect.verifySteps(["b.1 after:b.1 value", "b.1.1 before"]);
        await resolve("b.1.1 value");
        expect.verifySteps(["b.1.1 after:b.1.1 value"]);
        context.cancel();

        expect(context.isCancel).toBe(true);
        await resolve("b.1.2 value");
        await resolve("b.2 value");
        await resolve("b value");
        expect.verifySteps([]);
    });

    test("should cancel a simple promise", async () => {
        // const { getPromise, resolve } = prepare();
        const context = getCancellableTask(async () => {
            step("a before");
            await deferred("a value");
            step("a after");
            const asyncFunction = async () => {
                step("b before");
                await deferred("b value");
                step("b after");
            };
            await asyncFunction();
            step("gen end");
        });
        verifySteps(["a before"]);
        await resolve("a value");
        verifySteps(["a after", "b before"]);
        context.cancel();
        await resolve("b value");
        expect(context.isCancel).toBe(true);
        verifySteps([]);
    });
});
