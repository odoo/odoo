/** @odoo-module **/

import { formatCurrency } from "../../src/utils/currency";
import { patch, unpatch } from "../../src/utils/patch";
import { localization } from "../../src/localization/localization_settings";
import { defaultLocalization } from "../helpers/mocks";

QUnit.module("utils", () => {
  QUnit.module("Currency");

  QUnit.test("format", async (assert) => {
    patch(localization, "locpatch", defaultLocalization);
    assert.deepEqual(formatCurrency(1234567.654, 1), "$ 1,234,567.65");
    assert.deepEqual(formatCurrency(1234567.654, 2), "1,234,567.65 €");
    assert.deepEqual(
      formatCurrency(1234567.654, 44),
      "1,234,567.65",
      "undefined currency should be fine too"
    );
    assert.deepEqual(formatCurrency(1234567.654, 2, { noSymbol: true }), "1,234,567.65");
    assert.deepEqual(formatCurrency(1234567.654, 2, { humanReadable: true }), "1M €");
    assert.deepEqual(formatCurrency(1234567.654, 44, { digits: [69, 1] }), "1,234,567.7");
    assert.deepEqual(
      formatCurrency(1234567.654, 1, { digits: [69, 1] }),
      "$ 1,234,567.65",
      "currency digits should take over options digits when both are defined"
    );
    assert.strictEqual(formatCurrency(false, 2), "");
    unpatch(localization, "locpatch");
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
});
