import { describe, expect, test } from "@odoo/hoot";
import { delay } from "@odoo/hoot-dom";
import { Operation } from "../src/core/operation";

describe("Operation", () => {
    test("handle 3 concurrent cancellable operations (with delay)", async () => {
        const operation = new Operation();
        function makeCall(data) {
            let resolve;
            const promise = new Promise((r) => {
                resolve = r;
            });
            async function load() {
                expect.step(`load before ${data}`);
                await promise;
                expect.step(`load after ${data}`);
            }
            function apply() {
                expect.step(`apply ${data}`);
            }

            operation.next(apply, { load, cancellable: true });
            return {
                resolve,
            };
        }
        const call1 = makeCall(1);
        await delay();
        const call2 = makeCall(2);
        await delay();
        const call3 = makeCall(3);
        await delay();
        call1.resolve();
        call2.resolve();
        call3.resolve();
        await operation.mutex.getUnlockedDef();
        expect.verifySteps([
            //
            "load before 1",
            "load after 1",
            "load before 3",
            "load after 3",
            "apply 3",
        ]);
    });
    test("handle 3 concurrent cancellable operations (without delay)", async () => {
        const operation = new Operation();
        function makeCall(data) {
            let resolve;
            const promise = new Promise((r) => {
                resolve = r;
            });
            async function load() {
                expect.step(`load before ${data}`);
                await promise;
                expect.step(`load after ${data}`);
            }
            function apply() {
                expect.step(`apply ${data}`);
            }

            operation.next(apply, { load, cancellable: true });
            return {
                resolve,
            };
        }
        const call1 = makeCall(1);
        const call2 = makeCall(2);
        const call3 = makeCall(3);
        call1.resolve();
        call2.resolve();
        call3.resolve();
        await operation.mutex.getUnlockedDef();
        expect.verifySteps(["load before 3", "load after 3", "apply 3"]);
    });
});
