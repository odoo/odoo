/** @odoo-module **/

import { Mutex, KeepLast } from "../../src/utils/concurrency";
import { nextTick, makeDeferred } from "../helpers/utility";

QUnit.module("utils", () => {
  QUnit.module("Concurrency");

  QUnit.test("Mutex: simple scheduling", async function (assert) {
    assert.expect(5);

    const mutex = new Mutex();
    const def1 = makeDeferred(assert);
    const def2 = makeDeferred(assert);

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
    const def1 = makeDeferred(assert);
    const def2 = makeDeferred(assert);

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
    const def1 = makeDeferred(assert);
    const def2 = makeDeferred(assert);
    const def3 = makeDeferred(assert);

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
    const def1 = makeDeferred(assert);
    const def2 = makeDeferred(assert);

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
    const def = makeDeferred(assert);

    keepLast.add(def).then(() => assert.step("ok"));

    assert.verifySteps([]);

    def.resolve();
    await nextTick();

    assert.verifySteps(["ok"]);
  });

  QUnit.test("KeepLast: rejected promise", async function (assert) {
    assert.expect(3);

    const keepLast = new KeepLast();
    const def = makeDeferred(assert);

    keepLast.add(def).catch(() => assert.step("ko"));

    assert.verifySteps([]);

    def.reject();
    await nextTick();

    assert.verifySteps(["ko"]);
  });

  QUnit.test("KeepLast: two promises resolved in order", async function (assert) {
    assert.expect(4);

    const keepLast = new KeepLast();
    const def1 = makeDeferred(assert);
    const def2 = makeDeferred(assert);

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
    const def1 = makeDeferred(assert);
    const def2 = makeDeferred(assert);

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
});
