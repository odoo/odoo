import { describe, expect, test } from "@odoo/hoot";
import { cancelablePromise } from "@web/core/utils/cancellablePromise";

describe("cancellablePromise", () => {
    const prepare = (execSubFunctionMethod = "return") => {
        const deffereds = {};
        const deferred = (key) => {
            deffereds[key] ||= Promise.withResolvers();
            return deffereds[key].promise;
        };
        const resolve = async (key) => {
            deffereds[key] ||= Promise.withResolvers();
            return deffereds[key].resolve(key);
        };
        const execSubFunction = {
            return: (fn) => fn,
            call: (fn) => fn(),
            wrapReturn: (fn) => cancelablePromise(fn),
            wrapCall: (fn) => cancelablePromise(fn()),
        }[execSubFunctionMethod];

        return {
            resolve,
            cpromise: cancelablePromise(function* () {
                let result;
                expect.step("a before");
                result = yield deferred("a value");
                expect.step(`a after:${result}`);
                const genFunction = function* () {
                    let result;
                    expect.step("b.1 before");
                    result = yield deferred("b.1 value");
                    expect.step(`b.1 after:${result}`);
                    const genFunction = function* () {
                        let result;
                        expect.step("b.1.1 before");
                        result = yield deferred("b.1.1 value");
                        expect.step(`b.1.1 after:${result}`);
                        result = yield deferred("b.1.2 value");
                        expect.step(`b.1.2 after:${result}`);
                        return result;
                    };
                    result = yield execSubFunction(genFunction);
                    expect.step(`sub-sub gen result:${result}`);
                    result = yield deferred("b.2 value");
                    expect.step(`b.2 after:${result}`);
                    return result;
                };
                result = yield execSubFunction(genFunction);
                expect.step(`sub gen result:${result}`);
                result = yield deferred("b value");
                expect.step(`b after:${result}`);
            }),
        };
    };
    test("should execute with promises and sub generators", async () => {
        const { cpromise, resolve } = prepare();
        cpromise.call();
        expect.verifySteps(["a before"]);
        await resolve("a value");
        expect.verifySteps(["a after:a value", "b.1 before"]);
        await resolve("b.1 value");
        expect.verifySteps(["b.1 after:b.1 value", "b.1.1 before"]);
        await resolve("b.1.1 value");
        expect.verifySteps(["b.1.1 after:b.1.1 value"]);
        await resolve("b.1.2 value");
        expect.verifySteps(["b.1.2 after:b.1.2 value", "sub-sub gen result:b.1.2 value"]);
        await resolve("b.2 value");
        expect.verifySteps(["b.2 after:b.2 value", "sub gen result:b.2 value"]);
        await resolve("b value");
        expect.verifySteps(["b after:b value"]);
        expect(cpromise.isCancel).toBe(false);
    });
    test("should cancel in a sub generator", async () => {
        const { cpromise, resolve } = prepare();
        cpromise.call();
        expect.verifySteps(["a before"]);
        await resolve("a value");
        expect.verifySteps(["a after:a value", "b.1 before"]);
        await resolve("b.1 value");
        expect.verifySteps(["b.1 after:b.1 value", "b.1.1 before"]);
        await resolve("b.1.1 value");
        expect.verifySteps(["b.1.1 after:b.1.1 value"]);
        cpromise.cancel();
        expect(cpromise.isCancel).toBe(true);
        await resolve("b.1.2 value");
        await resolve("b.2 value");
        await resolve("b value");
        expect.verifySteps([]);
    });
});
