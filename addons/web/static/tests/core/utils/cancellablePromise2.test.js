import { describe, expect, test } from "@odoo/hoot";
import { effect } from "@web/core/utils/cancellablePromise2";
import { delay } from "@web/core/utils/concurrency";

describe("cancellablePromise2", () => {
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
    // test("should execute with promises and sub generators", async () => {
    //     const { cpromise, resolve } = prepare();
    //     cpromise.call();
    //     expect.verifySteps(["a before"]);
    //     await resolve("a value");
    //     expect.verifySteps(["a after:a value", "b.1 before"]);
    //     await resolve("b.1 value");
    //     expect.verifySteps(["b.1 after:b.1 value", "b.1.1 before"]);
    //     await resolve("b.1.1 value");
    //     expect.verifySteps(["b.1.1 after:b.1.1 value"]);
    //     await resolve("b.1.2 value");
    //     expect.verifySteps(["b.1.2 after:b.1.2 value", "sub-sub gen result:b.1.2 value"]);
    //     await resolve("b.2 value");
    //     expect.verifySteps(["b.2 after:b.2 value", "sub gen result:b.2 value"]);
    //     await resolve("b value");
    //     expect.verifySteps(["b after:b value"]);
    //     expect(cpromise.isCancel).toBe(false);
    // });
    // test("simple", async () => {
    //     const prepare = (execSubFunctionMethod = "call") => {
    //         const deffereds = {};
    //         const deferred = (key) => {
    //             deffereds[key] ||= Promise.withResolvers();
    //             return deffereds[key].promise;
    //         };
    //         const resolve = async (key) => {
    //             deffereds[key] ||= Promise.withResolvers();
    //             deffereds[key].resolve(key);
    //             await delay();
    //             return;
    //         };

    //         return {
    //             resolve,
    //             getPromise: async () => {
    //                 let result;
    //                 expect.step("a before");
    //                 debugger;
    //                 result = await deferred("a value");
    //                 debugger;
    //                 console.warn("here");
    //                 expect.step(`a after:${result}`);
    //                 // const genFunction = async () => {
    //                 //     let result;
    //                 //     expect.step("b.1 before");
    //                 //     result = await deferred("b.1 value");
    //                 //     expect.step(`b.1 after:${result}`);
    //                 //     const genFunction = async () => {
    //                 //         let result;
    //                 //         expect.step("b.1.1 before");
    //                 //         result = await deferred("b.1.1 value");
    //                 //         expect.step(`b.1.1 after:${result}`);
    //                 //         result = await deferred("b.1.2 value");
    //                 //         expect.step(`b.1.2 after:${result}`);
    //                 //         return result;
    //                 //     };
    //                 //     result = await genFunction();
    //                 //     expect.step(`sub-sub gen result:${result}`);
    //                 //     result = await deferred("b.2 value");
    //                 //     expect.step(`b.2 after:${result}`);
    //                 //     return result;
    //                 // };
    //                 // result = await genFunction();
    //                 // expect.step(`sub gen result:${result}`);
    //                 result = await deferred("b value");
    //                 debugger;
    //                 console.warn("here2");
    //                 expect.step(`b after:${result}`);
    //                 result = await deferred("c value");
    //                 debugger;
    //                 console.warn("here3");
    //                 expect.step(`c after:${result}`);
    //             },
    //         };
    //     };

    //     const { getPromise, resolve } = prepare();
    //     window.d = true;
    //     console.clear();
    //     const context = effect(() => getPromise());
    //     window.d = false;
    //     window.b = true;
    //     expect.verifySteps(["a before"]);
    //     await resolve("a value");
    //     expect.verifySteps(["a after:a value"]);
    //     context.cancel();
    //     expect(context.isCancel).toBe(true);
    //     await resolve("b value");
    //     await resolve("c value");
    //     expect.verifySteps([]);
    //     window.b = false;
    //     await delay(4000000000);
    // });
    test("should cancel in a sub generator", async () => {
        const { getPromise, resolve } = prepare();
        const context = effect(() => getPromise());
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
});
