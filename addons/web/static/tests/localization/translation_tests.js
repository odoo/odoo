/** @odoo-module **/

import { translatedTerms } from "../../src/localization/translation";
import { patch, unpatch } from "../../src/utils/patch";
import { getFixture, makeTestEnv } from "../helpers/index";

const { mount } = owl;

const terms = { Hello: "Bonjour" };

class TestComponent extends owl.Component {}

QUnit.module("Translations");

QUnit.test("can translate a text node", async (assert) => {
  assert.expect(1);
  TestComponent.template = owl.tags.xml`<div>Hello</div>`;
  const env = await makeTestEnv();
  patch(translatedTerms, "add translations", terms);
  const target = getFixture();
  await mount(TestComponent, { env, target });
  assert.strictEqual(target.innerText, "Bonjour");
  unpatch(translatedTerms, "add translations");
});

QUnit.test("_t is in env", async (assert) => {
  assert.expect(1);
  TestComponent.template = owl.tags.xml`<div><t t-esc="env._t('Hello')"/></div>`;
  const env = await makeTestEnv();
  patch(translatedTerms, "add translations", terms);
  const target = getFixture();
  await mount(TestComponent, { env, target });
  assert.strictEqual(target.innerText, "Bonjour");
  unpatch(translatedTerms, "add translations");
});
