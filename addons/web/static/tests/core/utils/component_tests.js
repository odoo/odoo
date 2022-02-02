/** @odoo-module **/

import { NotUpdatable, ErrorHandler } from "@web/core/utils/components";
import { makeTestEnv } from "../../helpers/mock_env";
import { getFixture, mount } from "../../helpers/utils";

const { Component, xml } = owl;

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
        Child.template = xml`<div>hey</div>`;
        class Parent extends Component {}
        Parent.template = xml`
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
    });

    QUnit.test("ErrorHandler component", async function (assert) {
        class Boom extends Component {}
        Boom.template = xml`<div><t t-esc="this.will.throw"/></div>`;

        class Parent extends Component {
            setup() {
                this.flag = true;
            }
            handleError() {
                this.flag = false;
                this.render();
            }
        }
        Parent.template = xml`
        <div>
          <t t-if="flag">
            <ErrorHandler onError="() => this.handleError()">
              <Boom />
            </ErrorHandler>
          </t>
          <t t-else="">
            not boom
          </t>
        </div>`;
        Parent.components = { Boom, ErrorHandler };

        const target = getFixture();
        await mount(Parent, { env: makeTestEnv(), target });
        assert.strictEqual(target.innerHTML, "<div> not boom </div>");
    });
});
