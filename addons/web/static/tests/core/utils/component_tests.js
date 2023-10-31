/** @odoo-module **/

import { NotUpdatable, ErrorHandler } from "@web/core/utils/components";
import { makeTestEnv } from "../../helpers/mock_env";
import { getFixture } from "../../helpers/utils";

const { Component, mount } = owl;

QUnit.module("utils", () => {
    QUnit.module("components");

    QUnit.test("NotUpdatable component", async function (assert) {
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
        Parent.template = owl.tags.xml`
          <div>
            <Child/>
            <NotUpdatable><Child/></NotUpdatable>
          </div>`;
        Parent.components = { Child, NotUpdatable };

        const target = getFixture();
        const parent = await mount(Parent, { env: makeTestEnv(), target });
        assert.verifySteps(["mounted", "mounted"]);

        await parent.render();
        assert.verifySteps(["willupdateprops"]);
        parent.destroy();
    });

    QUnit.test("ErrorHandler component", async function (assert) {
        class Boom extends Component {}
        Boom.template = owl.tags.xml`<div><t t-esc="this.will.throw"/></div>`;

        class Parent extends Component {
            setup() {
                this.flag = true;
            }
            handleError() {
                this.flag = false;
                this.render();
            }
        }
        Parent.template = owl.tags.xml`
        <div>
          <t t-if="flag">
            <ErrorHandler onError="() => handleError()">
              <Boom />
            </ErrorHandler>
          </t>
          <t t-else="">
            not boom
          </t>
        </div>`;
        Parent.components = { Boom, ErrorHandler };

        const target = getFixture();
        const parent = await mount(Parent, { env: makeTestEnv(), target });
        assert.strictEqual(target.innerHTML, "<div> not boom </div>");
        parent.destroy();
    });
});
