import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";

import { Mutex, KeepLast, Race } from "@web/core/utils/concurrency";

describe.current.tags("headless");

describe("Deferred", () => {
    test("basic use", async () => {
        const def1 = Promise.withResolvers();
        def1.promise.then((v) => expect.step(`ok (${v})`));
        def1.resolve(44);
        await tick();
        expect.verifySteps(["ok (44)"]);

        const def2 = Promise.withResolvers();
        def2.promise.catch((v) => expect.step(`ko (${v})`));
        def2.reject(44);
        await tick();
        expect.verifySteps(["ko (44)"]);
    });
});

describe("Mutex", () => {
    test("simple scheduling", async () => {
        const mutex = new Mutex();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();

        mutex.exec(() => def1.promise).then(() => expect.step("ok [1]"));
        mutex.exec(() => def2.promise).then(() => expect.step("ok [2]"));
        expect.verifySteps([]);

        def1.resolve();
        await tick();
        expect.verifySteps(["ok [1]"]);

        def2.resolve();
        await tick();
        expect.verifySteps(["ok [2]"]);
    });

    test("simple scheduling (2)", async () => {
        const mutex = new Mutex();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();

        mutex.exec(() => def1.promise).then(() => expect.step("ok [1]"));
        mutex.exec(() => def2.promise).then(() => expect.step("ok [2]"));
        expect.verifySteps([]);

        def2.resolve();
        await tick();
        expect.verifySteps([]);

        def1.resolve();
        await tick();
        expect.verifySteps(["ok [1]", "ok [2]"]);
    });

    test("reject", async () => {
        const mutex = new Mutex();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();
        const def3 = Promise.withResolvers();

        mutex.exec(() => def1.promise).then(() => expect.step("ok [1]"));
        mutex.exec(() => def2.promise).catch(() => expect.step("ko [2]"));
        mutex.exec(() => def3.promise).then(() => expect.step("ok [3]"));
        expect.verifySteps([]);

        def1.resolve();
        await tick();
        expect.verifySteps(["ok [1]"]);

        def2.reject({ name: "sdkjfmqsjdfmsjkdfkljsdq" });
        await tick();
        expect.verifySteps(["ko [2]"]);

        def3.resolve();
        await tick();
        expect.verifySteps(["ok [3]"]);
    });

    test("getUnlockedDef checks", async () => {
        const mutex = new Mutex();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();

        mutex.getUnlockedDef().then(() => expect.step("mutex unlocked (1)"));
        await tick();
        expect.verifySteps(["mutex unlocked (1)"]);

        mutex.exec(() => def1.promise).then(() => expect.step("ok [1]"));
        await tick();
        mutex.getUnlockedDef().then(function () {
            expect.step("mutex unlocked (2)");
        });
        expect.verifySteps([]);

        mutex.exec(() => def2.promise).then(() => expect.step("ok [2]"));
        await tick();
        expect.verifySteps([]);

        def1.resolve();
        await tick();
        expect.verifySteps(["ok [1]"]);

        def2.resolve();
        await tick();
        expect.verifySteps(["mutex unlocked (2)", "ok [2]"]);
    });

    test("error and getUnlockedDef", async () => {
        const mutex = new Mutex();
        const action = async () => {
            await Promise.resolve();
            throw new Error("boom");
        };
        mutex.exec(action).catch(() => expect.step("prom rejected"));
        await tick();
        expect.verifySteps(["prom rejected"]);

        mutex.getUnlockedDef().then(() => expect.step("mutex unlocked"));
        await tick();
        expect.verifySteps(["mutex unlocked"]);
    });
});

describe("KeepLast", () => {
    test("basic use", async () => {
        const keepLast = new KeepLast();
        const def = Promise.withResolvers();

        keepLast.add(def.promise).then(() => expect.step("ok"));
        expect.verifySteps([]);

        def.resolve();
        await tick();
        expect.verifySteps(["ok"]);
    });

    test("rejected promise", async () => {
        const keepLast = new KeepLast();
        const def = Promise.withResolvers();

        keepLast.add(def.promise).catch(() => expect.step("ko"));
        expect.verifySteps([]);

        def.reject();
        await tick();
        expect.verifySteps(["ko"]);
    });

    test("two promises resolved in order", async () => {
        const keepLast = new KeepLast();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();

        keepLast.add(def1.promise).then(() => {
            throw new Error("should not be executed");
        });
        keepLast.add(def2.promise).then(() => expect.step("ok [2]"));
        expect.verifySteps([]);

        def1.resolve();
        await tick();
        expect.verifySteps([]);

        def2.resolve();
        await tick();
        expect.verifySteps(["ok [2]"]);
    });

    test("two promises resolved in reverse order", async () => {
        const keepLast = new KeepLast();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();

        keepLast.add(def1.promise).then(() => {
            throw new Error("should not be executed");
        });
        keepLast.add(def2.promise).then(() => expect.step("ok [2]"));
        expect.verifySteps([]);

        def2.resolve();
        await tick();
        expect.verifySteps(["ok [2]"]);

        def1.resolve();
        await tick();
        expect.verifySteps([]);
    });
});

describe("Race", () => {
    test("basic use", async () => {
        const race = new Race();
        const def = Promise.withResolvers();

        race.add(def.promise).then((v) => expect.step(`ok (${v})`));
        expect.verifySteps([]);

        def.resolve(44);
        await tick();
        expect.verifySteps(["ok (44)"]);
    });

    test("two promises resolved in order", async () => {
        const race = new Race();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();

        race.add(def1.promise).then((v) => expect.step(`ok (${v}) [1]`));
        race.add(def2.promise).then((v) => expect.step(`ok (${v}) [2]`));
        expect.verifySteps([]);

        def1.resolve(44);
        await tick();
        expect.verifySteps(["ok (44) [1]", "ok (44) [2]"]);

        def2.resolve();
        await tick();
        expect.verifySteps([]);
    });

    test("two promises resolved in reverse order", async () => {
        const race = new Race();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();

        race.add(def1.promise).then((v) => expect.step(`ok (${v}) [1]`));
        race.add(def2.promise).then((v) => expect.step(`ok (${v}) [2]`));
        expect.verifySteps([]);

        def2.resolve(44);
        await tick();
        expect.verifySteps(["ok (44) [1]", "ok (44) [2]"]);

        def1.resolve();
        await tick();
        expect.verifySteps([]);
    });

    test("multiple resolutions", async () => {
        const race = new Race();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();
        const def3 = Promise.withResolvers();

        race.add(def1.promise).then((v) => expect.step(`ok (${v}) [1]`));
        def1.resolve(44);
        await tick();
        expect.verifySteps(["ok (44) [1]"]);

        race.add(def2.promise).then((v) => expect.step(`ok (${v}) [2]`));
        race.add(def3.promise).then((v) => expect.step(`ok (${v}) [3]`));
        def2.resolve(44);
        await tick();
        expect.verifySteps(["ok (44) [2]", "ok (44) [3]"]);
    });

    test("catch rejected promise", async () => {
        const race = new Race();
        const def = Promise.withResolvers();

        race.add(def.promise).catch((v) => expect.step(`not ok (${v})`));
        expect.verifySteps([]);

        def.reject(44);
        await tick();
        expect.verifySteps(["not ok (44)"]);
    });

    test("first promise rejects first", async () => {
        const race = new Race();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();

        race.add(def1.promise).catch((v) => expect.step(`not ok (${v}) [1]`));
        race.add(def2.promise).catch((v) => expect.step(`not ok (${v}) [2]`));
        expect.verifySteps([]);

        def1.reject(44);
        await tick();
        expect.verifySteps(["not ok (44) [1]", "not ok (44) [2]"]);

        def2.resolve();
        await tick();
        expect.verifySteps([]);
    });

    test("second promise rejects after", async () => {
        const race = new Race();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();

        race.add(def1.promise).then((v) => expect.step(`ok (${v}) [1]`));
        race.add(def2.promise).then((v) => expect.step(`ok (${v}) [2]`));
        expect.verifySteps([]);

        def1.resolve(44);
        await tick();
        expect.verifySteps(["ok (44) [1]", "ok (44) [2]"]);

        def2.reject();
        await tick();
        expect.verifySteps([]);
    });

    test("second promise rejects first", async () => {
        const race = new Race();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();

        race.add(def1.promise).catch((v) => expect.step(`not ok (${v}) [1]`));
        race.add(def2.promise).catch((v) => expect.step(`not ok (${v}) [2]`));
        expect.verifySteps([]);

        def2.reject(44);
        await tick();
        expect.verifySteps(["not ok (44) [1]", "not ok (44) [2]"]);

        def1.resolve();
        await tick();
        expect.verifySteps([]);
    });

    test("first promise rejects after", async () => {
        const race = new Race();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();

        race.add(def1.promise).then((v) => expect.step(`ok (${v}) [1]`));
        race.add(def2.promise).then((v) => expect.step(`ok (${v}) [2]`));
        expect.verifySteps([]);

        def2.resolve(44);
        await tick();
        expect.verifySteps(["ok (44) [1]", "ok (44) [2]"]);

        def1.reject();
        await tick();
        expect.verifySteps([]);
    });

    test("getCurrentProm", async () => {
        const race = new Race();
        const def1 = Promise.withResolvers();
        const def2 = Promise.withResolvers();
        const def3 = Promise.withResolvers();
        expect(race.getCurrentProm()).toBe(null);

        race.add(def1.promise);
        race.getCurrentProm().then((v) => expect.step(`ok (${v})`));
        def1.resolve(44);
        await tick();
        expect.verifySteps(["ok (44)"]);
        expect(race.getCurrentProm()).toBe(null);

        race.add(def2.promise);
        race.getCurrentProm().then((v) => expect.step(`ok (${v})`));
        race.add(def3.promise);
        def3.resolve(44);
        await tick();
        expect.verifySteps(["ok (44)"]);
        expect(race.getCurrentProm()).toBe(null);
    });
});
