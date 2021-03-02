/** @odoo-module **/
import { currencyService } from "../../src/services/currency_service";
import { makeTestEnv } from "../helpers/index";
import { Registry } from "../../src/core/registry";
let env;
let serviceRegistry;
QUnit.module("Currency");
QUnit.test("get & getAll", async (assert) => {
  serviceRegistry = new Registry();
  serviceRegistry.add("currency", currencyService);
  env = await makeTestEnv({ serviceRegistry });
  const { currency: curSvc } = env.services;
  assert.deepEqual(curSvc.get(1).name, "USD");
  assert.deepEqual(curSvc.get("USD").name, "USD");
  assert.deepEqual(curSvc.get("OdooCoin"), undefined);
  assert.deepEqual(
    curSvc.getAll().map((c) => c.name),
    ["USD", "EUR"]
  );
});
QUnit.test("format", async (assert) => {
  serviceRegistry = new Registry();
  serviceRegistry.add("currency", currencyService);
  env = await makeTestEnv({ serviceRegistry });
  const { currency: curSvc } = env.services;
  assert.deepEqual(curSvc.format(1234567.654, "USD"), "$ 1234567.65");
  assert.deepEqual(curSvc.format(1234567.654, "EUR"), "1234567.65 €");
  assert.deepEqual(
    curSvc.format(1234567.654, "OdooCoin"),
    "1234567.65",
    "undefined currency should be fine too"
  );
  assert.deepEqual(curSvc.format(1234567.654, "EUR", { noSymbol: true }), "1234567.65");
  assert.deepEqual(curSvc.format(1234567.654, "EUR", { humanReadable: true }), "1M €");
  assert.deepEqual(curSvc.format(1234567.654, "OdooCoin", { digits: [69, 1] }), "1234567.7");
  assert.deepEqual(
    curSvc.format(1234567.654, "USD", { digits: [69, 1] }),
    "$ 1234567.65",
    "currency digits should take over options digits when both are defined"
  );
  assert.strictEqual(curSvc.format(false, "EUR"), "");
});
// BOI: we do not have a parse method, but here are some tests if we want to add this at some point.
// QUnit.test("parse", async (assert) => {
//   serviceRegistry = new Registry();
//   serviceRegistry.add("currency", currencyService);
//   env = await makeTestEnv({ serviceRegistry });
//   const { currency: curSvc } = env.services;
//   assert.deepEqual(curSvc.parse("$ 1234567.65", "USD"), 1234567.65);
//   assert.deepEqual(curSvc.parse("1234567.65 €", "EUR"), 1234567.65);
//   assert.deepEqual(curSvc.parse("1234567.65 €", "EUR"), 1234567.65);
//   assert.deepEqual(curSvc.parse("$ 1,234,567.65", "USD"), 1234567.65);
//   assert.deepEqual(curSvc.parse("1,234,567.65 €", "EUR"), 1234567.65);
//   assert.deepEqual(curSvc.parse("1,234,567.65 €", "EUR"), 1234567.65);
//   assert.throws(function () {
//     curSvc.parse("1234567.65 €", "OdooCoin");
//   }, /currency not found/);
//   assert.throws(function () {
//     curSvc.parse("$ 1,234,567.65", "EUR");
//   }, /not a correct 'EUR' monetary field/);
// });
