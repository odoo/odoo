import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";

import { Deferred, Mutex, KeepLast, Race } from "@web/core/utils/concurrency";

describe.current.tags("headless");

describe("Deferred", () => {
    test("basic use", async () => {
        const def1 = new Deferred();
        def1.then((v) => expect.step(`ok (${v})`));
        def1.resolve(44);
        await tick();
        expect(["ok (44)"]).toVerifySteps();

        const def2 = new Deferred();
        def2.catch((v) => expect.step(`ko (${v})`));
        def2.reject(44);
        await tick();
        expect(["ko (44)"]).toVerifySteps();
    });
});

describe("Mutex", () => {
    test("simple scheduling", async () => {
        const mutex = new Mutex();
        const def1 = new Deferred();
        const def2 = new Deferred();

        mutex.exec(() => def1).then(() => expect.step("ok [1]"));
        mutex.exec(() => def2).then(() => expect.step("ok [2]"));
        expect([]).toVerifySteps();

        def1.resolve();
        await tick();
        expect(["ok [1]"]).toVerifySteps();

        def2.resolve();
        await tick();
        expect(["ok [2]"]).toVerifySteps();
    });

    test("simple scheduling (2)", async () => {
        const mutex = new Mutex();
        const def1 = new Deferred();
        const def2 = new Deferred();

        mutex.exec(() => def1).then(() => expect.step("ok [1]"));
        mutex.exec(() => def2).then(() => expect.step("ok [2]"));
        expect([]).toVerifySteps();

        def2.resolve();
        await tick();
        expect([]).toVerifySteps();

        def1.resolve();
        await tick();
        expect(["ok [1]", "ok [2]"]).toVerifySteps();
    });

    test("reject", async () => {
        const mutex = new Mutex();
        const def1 = new Deferred();
        const def2 = new Deferred();
        const def3 = new Deferred();

        mutex.exec(() => def1).then(() => expect.step("ok [1]"));
        mutex.exec(() => def2).catch(() => expect.step("ko [2]"));
        mutex.exec(() => def3).then(() => expect.step("ok [3]"));
        expect([]).toVerifySteps();

        def1.resolve();
        await tick();
        expect(["ok [1]"]).toVerifySteps();

        def2.reject({ name: "sdkjfmqsjdfmsjkdfkljsdq" });
        await tick();
        expect(["ko [2]"]).toVerifySteps();

        def3.resolve();
        await tick();
        expect(["ok [3]"]).toVerifySteps();
    });

    test("getUnlockedDef checks", async () => {
        const mutex = new Mutex();
        const def1 = new Deferred();
        const def2 = new Deferred();

        mutex.getUnlockedDef().then(() => expect.step("mutex unlocked (1)"));
        await tick();
        expect(["mutex unlocked (1)"]).toVerifySteps();

        mutex.exec(() => def1).then(() => expect.step("ok [1]"));
        await tick();
        mutex.getUnlockedDef().then(function () {
            expect.step("mutex unlocked (2)");
        });
        expect([]).toVerifySteps();

        mutex.exec(() => def2).then(() => expect.step("ok [2]"));
        await tick();
        expect([]).toVerifySteps();

        def1.resolve();
        await tick();
        expect(["ok [1]"]).toVerifySteps();

        def2.resolve();
        await tick();
        expect(["mutex unlocked (2)", "ok [2]"]).toVerifySteps();
    });

    test("error and getUnlockedDef", async () => {
        const mutex = new Mutex();
        const action = async () => {
            await Promise.resolve();
            throw new Error("boom");
        };
        mutex.exec(action).catch(() => expect.step("prom rejected"));
        await tick();
        expect(["prom rejected"]).toVerifySteps();

        mutex.getUnlockedDef().then(() => expect.step("mutex unlocked"));
        await tick();
        expect(["mutex unlocked"]).toVerifySteps();
    });
});

describe("KeepLast", () => {
    test("basic use", async () => {
        const keepLast = new KeepLast();
        const def = new Deferred();

        keepLast.add(def).then(() => expect.step("ok"));
        expect([]).toVerifySteps();

        def.resolve();
        await tick();
        expect(["ok"]).toVerifySteps();
    });

    test("rejected promise", async () => {
        const keepLast = new KeepLast();
        const def = new Deferred();

        keepLast.add(def).catch(() => expect.step("ko"));
        expect([]).toVerifySteps();

        def.reject();
        await tick();
        expect(["ko"]).toVerifySteps();
    });

    test("two promises resolved in order", async () => {
        const keepLast = new KeepLast();
        const def1 = new Deferred();
        const def2 = new Deferred();

        keepLast.add(def1).then(() => {
            throw new Error("should not be executed");
        });
        keepLast.add(def2).then(() => expect.step("ok [2]"));
        expect([]).toVerifySteps();

        def1.resolve();
        await tick();
        expect([]).toVerifySteps();

        def2.resolve();
        await tick();
        expect(["ok [2]"]).toVerifySteps();
    });

    test("two promises resolved in reverse order", async () => {
        const keepLast = new KeepLast();
        const def1 = new Deferred();
        const def2 = new Deferred();

        keepLast.add(def1).then(() => {
            throw new Error("should not be executed");
        });
        keepLast.add(def2).then(() => expect.step("ok [2]"));
        expect([]).toVerifySteps();

        def2.resolve();
        await tick();
        expect(["ok [2]"]).toVerifySteps();

        def1.resolve();
        await tick();
        expect([]).toVerifySteps();
    });
});

describe("Race", () => {
    test("basic use", async () => {
        const race = new Race();
        const def = new Deferred();

        race.add(def).then((v) => expect.step(`ok (${v})`));
        expect([]).toVerifySteps();

        def.resolve(44);
        await tick();
        expect(["ok (44)"]).toVerifySteps();
    });

    test("two promises resolved in order", async () => {
        const race = new Race();
        const def1 = new Deferred();
        const def2 = new Deferred();

        race.add(def1).then((v) => expect.step(`ok (${v}) [1]`));
        race.add(def2).then((v) => expect.step(`ok (${v}) [2]`));
        expect([]).toVerifySteps();

        def1.resolve(44);
        await tick();
        expect(["ok (44) [1]", "ok (44) [2]"]).toVerifySteps();

        def2.resolve();
        await tick();
        expect([]).toVerifySteps();
    });

    test("two promises resolved in reverse order", async () => {
        const race = new Race();
        const def1 = new Deferred();
        const def2 = new Deferred();

        race.add(def1).then((v) => expect.step(`ok (${v}) [1]`));
        race.add(def2).then((v) => expect.step(`ok (${v}) [2]`));
        expect([]).toVerifySteps();

        def2.resolve(44);
        await tick();
        expect(["ok (44) [1]", "ok (44) [2]"]).toVerifySteps();

        def1.resolve();
        await tick();
        expect([]).toVerifySteps();
    });

    test("multiple resolutions", async () => {
        const race = new Race();
        const def1 = new Deferred();
        const def2 = new Deferred();
        const def3 = new Deferred();

        race.add(def1).then((v) => expect.step(`ok (${v}) [1]`));
        def1.resolve(44);
        await tick();
        expect(["ok (44) [1]"]).toVerifySteps();

        race.add(def2).then((v) => expect.step(`ok (${v}) [2]`));
        race.add(def3).then((v) => expect.step(`ok (${v}) [3]`));
        def2.resolve(44);
        await tick();
        expect(["ok (44) [2]", "ok (44) [3]"]).toVerifySteps();
    });

    test("catch rejected promise", async () => {
        const race = new Race();
        const def = new Deferred();

        race.add(def).catch((v) => expect.step(`not ok (${v})`));
        expect([]).toVerifySteps();

        def.reject(44);
        await tick();
        expect(["not ok (44)"]).toVerifySteps();
    });

    test("first promise rejects first", async () => {
        const race = new Race();
        const def1 = new Deferred();
        const def2 = new Deferred();

        race.add(def1).catch((v) => expect.step(`not ok (${v}) [1]`));
        race.add(def2).catch((v) => expect.step(`not ok (${v}) [2]`));
        expect([]).toVerifySteps();

        def1.reject(44);
        await tick();
        expect(["not ok (44) [1]", "not ok (44) [2]"]).toVerifySteps();

        def2.resolve();
        await tick();
        expect([]).toVerifySteps();
    });

    test("second promise rejects after", async () => {
        const race = new Race();
        const def1 = new Deferred();
        const def2 = new Deferred();

        race.add(def1).then((v) => expect.step(`ok (${v}) [1]`));
        race.add(def2).then((v) => expect.step(`ok (${v}) [2]`));
        expect([]).toVerifySteps();

        def1.resolve(44);
        await tick();
        expect(["ok (44) [1]", "ok (44) [2]"]).toVerifySteps();

        def2.reject();
        await tick();
        expect([]).toVerifySteps();
    });

    test("second promise rejects first", async () => {
        const race = new Race();
        const def1 = new Deferred();
        const def2 = new Deferred();

        race.add(def1).catch((v) => expect.step(`not ok (${v}) [1]`));
        race.add(def2).catch((v) => expect.step(`not ok (${v}) [2]`));
        expect([]).toVerifySteps();

        def2.reject(44);
        await tick();
        expect(["not ok (44) [1]", "not ok (44) [2]"]).toVerifySteps();

        def1.resolve();
        await tick();
        expect([]).toVerifySteps();
    });

    test("first promise rejects after", async () => {
        const race = new Race();
        const def1 = new Deferred();
        const def2 = new Deferred();

        race.add(def1).then((v) => expect.step(`ok (${v}) [1]`));
        race.add(def2).then((v) => expect.step(`ok (${v}) [2]`));
        expect([]).toVerifySteps();

        def2.resolve(44);
        await tick();
        expect(["ok (44) [1]", "ok (44) [2]"]).toVerifySteps();

        def1.reject();
        await tick();
        expect([]).toVerifySteps();
    });

    test("getCurrentProm", async () => {
        const race = new Race();
        const def1 = new Deferred();
        const def2 = new Deferred();
        const def3 = new Deferred();
        expect(race.getCurrentProm()).toBe(null);

        race.add(def1);
        race.getCurrentProm().then((v) => expect.step(`ok (${v})`));
        def1.resolve(44);
        await tick();
        expect(["ok (44)"]).toVerifySteps();
        expect(race.getCurrentProm()).toBe(null);

        race.add(def2);
        race.getCurrentProm().then((v) => expect.step(`ok (${v})`));
        race.add(def3);
        def3.resolve(44);
        await tick();
        expect(["ok (44)"]).toVerifySteps();
        expect(race.getCurrentProm()).toBe(null);
    });
});
