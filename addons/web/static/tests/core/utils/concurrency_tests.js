/** @odoo-module **/

import { Mutex, KeepLast, Race } from "@web/core/utils/concurrency";
import { nextTick, makeDeferred } from "../../helpers/utils";

QUnit.module("utils", () => {
    QUnit.module("Concurrency");

    QUnit.test("Mutex: simple scheduling", async function (assert) {
        assert.expect(5);

        const mutex = new Mutex();
        const def1 = makeDeferred();
        const def2 = makeDeferred();

        mutex.exec(() => def1).then(() => assert.step("ok [1]"));
        mutex.exec(() => def2).then(() => assert.step("ok [2]"));

        assert.verifySteps([]);

        def1.resolve();
        await nextTick();

        assert.verifySteps(["ok [1]"]);

        def2.resolve();
        await nextTick();

        assert.verifySteps(["ok [2]"]);
    });

    QUnit.test("Mutex: simple scheduling (2)", async function (assert) {
        assert.expect(5);

        const mutex = new Mutex();
        const def1 = makeDeferred();
        const def2 = makeDeferred();

        mutex.exec(() => def1).then(() => assert.step("ok [1]"));
        mutex.exec(() => def2).then(() => assert.step("ok [2]"));

        assert.verifySteps([]);

        def2.resolve();
        await nextTick();

        assert.verifySteps([]);

        def1.resolve();
        await nextTick();

        assert.verifySteps(["ok [1]", "ok [2]"]);
    });

    QUnit.test("Mutex: reject", async function (assert) {
        assert.expect(7);

        const mutex = new Mutex();
        const def1 = makeDeferred();
        const def2 = makeDeferred();
        const def3 = makeDeferred();

        mutex.exec(() => def1).then(() => assert.step("ok [1]"));
        mutex.exec(() => def2).catch(() => assert.step("ko [2]"));
        mutex.exec(() => def3).then(() => assert.step("ok [3]"));

        assert.verifySteps([]);

        def1.resolve();
        await nextTick();

        assert.verifySteps(["ok [1]"]);

        def2.reject({ name: "sdkjfmqsjdfmsjkdfkljsdq" });
        await nextTick();

        assert.verifySteps(["ko [2]"]);

        def3.resolve();
        await nextTick();

        assert.verifySteps(["ok [3]"]);
    });

    QUnit.test("Mutex: getUnlockedDef checks", async function (assert) {
        assert.expect(9);

        const mutex = new Mutex();
        const def1 = makeDeferred();
        const def2 = makeDeferred();

        mutex.getUnlockedDef().then(() => assert.step("mutex unlocked (1)"));

        await nextTick();

        assert.verifySteps(["mutex unlocked (1)"]);

        mutex.exec(() => def1).then(() => assert.step("ok [1]"));
        await nextTick();

        mutex.getUnlockedDef().then(function () {
            assert.step("mutex unlocked (2)");
        });

        assert.verifySteps([]);

        mutex.exec(() => def2).then(() => assert.step("ok [2]"));
        await nextTick();

        assert.verifySteps([]);

        def1.resolve();
        await nextTick();

        assert.verifySteps(["ok [1]"]);

        def2.resolve();
        await nextTick();

        assert.verifySteps(["mutex unlocked (2)", "ok [2]"]);
    });

    QUnit.test("KeepLast: basic use", async function (assert) {
        assert.expect(3);

        const keepLast = new KeepLast();
        const def = makeDeferred();

        keepLast.add(def).then(() => assert.step("ok"));

        assert.verifySteps([]);

        def.resolve();
        await nextTick();

        assert.verifySteps(["ok"]);
    });

    QUnit.test("KeepLast: rejected promise", async function (assert) {
        assert.expect(3);

        const keepLast = new KeepLast();
        const def = makeDeferred();

        keepLast.add(def).catch(() => assert.step("ko"));

        assert.verifySteps([]);

        def.reject();
        await nextTick();

        assert.verifySteps(["ko"]);
    });

    QUnit.test("KeepLast: two promises resolved in order", async function (assert) {
        assert.expect(4);

        const keepLast = new KeepLast();
        const def1 = makeDeferred();
        const def2 = makeDeferred();

        keepLast.add(def1).then(() => {
            throw new Error("should not be executed");
        });
        keepLast.add(def2).then(() => assert.step("ok [2]"));

        assert.verifySteps([]);

        def1.resolve();
        await nextTick();

        assert.verifySteps([]);

        def2.resolve();
        await nextTick();

        assert.verifySteps(["ok [2]"]);
    });

    QUnit.test("KeepLast: two promises resolved in reverse order", async function (assert) {
        assert.expect(4);

        const keepLast = new KeepLast();
        const def1 = makeDeferred();
        const def2 = makeDeferred();

        keepLast.add(def1).then(() => {
            throw new Error("should not be executed");
        });
        keepLast.add(def2).then(() => assert.step("ok [2]"));

        assert.verifySteps([]);

        def2.resolve();
        await nextTick();

        assert.verifySteps(["ok [2]"]);

        def1.resolve();
        await nextTick();

        assert.verifySteps([]);
    });

    QUnit.test("Race: basic use", async function (assert) {
        assert.expect(3);

        const race = new Race();
        const def = makeDeferred();

        race.add(def).then((v) => assert.step(`ok (${v})`));

        assert.verifySteps([]);

        def.resolve(44);
        await nextTick();

        assert.verifySteps(["ok (44)"]);
    });

    QUnit.test("Race: two promises resolved in order", async function (assert) {
        assert.expect(5);

        const race = new Race();
        const def1 = makeDeferred();
        const def2 = makeDeferred();

        race.add(def1).then((v) => assert.step(`ok (${v}) [1]`));
        race.add(def2).then((v) => assert.step(`ok (${v}) [2]`));

        assert.verifySteps([]);

        def1.resolve(44);
        await nextTick();

        assert.verifySteps(["ok (44) [1]", "ok (44) [2]"]);

        def2.resolve();
        await nextTick();

        assert.verifySteps([]);
    });

    QUnit.test("Race: two promises resolved in reverse order", async function (assert) {
        assert.expect(5);

        const race = new Race();
        const def1 = makeDeferred();
        const def2 = makeDeferred();

        race.add(def1).then((v) => assert.step(`ok (${v}) [1]`));
        race.add(def2).then((v) => assert.step(`ok (${v}) [2]`));

        assert.verifySteps([]);

        def2.resolve(44);
        await nextTick();

        assert.verifySteps(["ok (44) [1]", "ok (44) [2]"]);

        def1.resolve();
        await nextTick();

        assert.verifySteps([]);
    });

    QUnit.test("Race: multiple resolutions", async function (assert) {
        assert.expect(5);

        const race = new Race();
        const def1 = makeDeferred();
        const def2 = makeDeferred();
        const def3 = makeDeferred();

        race.add(def1).then((v) => assert.step(`ok (${v}) [1]`));
        def1.resolve(44);
        await nextTick();

        assert.verifySteps(["ok (44) [1]"]);

        race.add(def2).then((v) => assert.step(`ok (${v}) [2]`));
        race.add(def3).then((v) => assert.step(`ok (${v}) [3]`));

        def2.resolve(44);
        await nextTick();

        assert.verifySteps(["ok (44) [2]", "ok (44) [3]"]);
    });

    QUnit.test("Race: getCurrentProm", async function (assert) {
        assert.expect(7);

        const race = new Race();
        const def1 = makeDeferred();
        const def2 = makeDeferred();
        const def3 = makeDeferred();

        assert.strictEqual(race.getCurrentProm(), null);

        race.add(def1);
        race.getCurrentProm().then((v) => assert.step(`ok (${v})`));
        def1.resolve(44);
        await nextTick();
        assert.verifySteps(["ok (44)"]);
        assert.strictEqual(race.getCurrentProm(), null);

        race.add(def2);
        race.getCurrentProm().then((v) => assert.step(`ok (${v})`));
        race.add(def3);
        def3.resolve(44);
        await nextTick();
        assert.verifySteps(["ok (44)"]);
        assert.strictEqual(race.getCurrentProm(), null);
    });
});
