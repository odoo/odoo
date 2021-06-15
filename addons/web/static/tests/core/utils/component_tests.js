/** @odoo-module **/

import { makeNonUpdatableComponent } from "@web/core/utils/components";
import { makeTestEnv } from "../../helpers/mock_env";
import { getFixture } from "../../helpers/utils";

const { Component, mount } = owl;

QUnit.module("utils", () => {
    QUnit.module("components");

    QUnit.test("makeNonUpdatableComponent", async function (assert) {
        class Child extends Component {
            mounted() {
                assert.step("mounted");
            }
            willUpdateProps() {
                assert.step("willupdateprops");
            }
        }
        Child.template = owl.tags.xml`<div>hey</div>`;
        class Parent extends Component {}
        Parent.template = owl.tags.xml`<div><Child1/><Child2/></div>`;
        Parent.components = { Child1: Child, Child2: makeNonUpdatableComponent(Child) };

        const target = getFixture();
        const parent = await mount(Parent, { env: makeTestEnv(), target });
        assert.verifySteps(["mounted", "mounted"]);

        await parent.render();
        assert.verifySteps(["willupdateprops"]);
        parent.destroy();
    });
});
