/** @odoo-module **/

import { CheckBox } from "../../src/components/checkbox/checkbox";
import { translatedTerms } from "../../src/localization/translation";
import { makeTestEnv } from "../helpers/mock_env";
import { getFixture, patchWithCleanup } from "../helpers/utils";

const { mount, tags } = owl;
const { xml } = tags;

let env;
let target;

QUnit.module("Components", (hooks) => {
  hooks.beforeEach(async () => {
    env = await makeTestEnv();
    target = getFixture();
  });

  QUnit.module("CheckBox");

  QUnit.test("can be rendered", async (assert) => {
    await mount(CheckBox, { env, target, props: {} });
    assert.containsOnce(target, "div.custom-checkbox");
  });

  QUnit.test("has a slot for translatable text", async (assert) => {
    patchWithCleanup(translatedTerms, { ragabadabadaba: "rugubudubudubu" });

    class Parent extends Component {}
    Parent.template = xml`<CheckBox>ragabadabadaba</CheckBox>`;

    const parent = await mount(Parent, { env, target });
    assert.containsOnce(target, "div.custom-checkbox");
    assert.strictEqual(parent.el.innerText, "rugubudubudubu");

  });
});
