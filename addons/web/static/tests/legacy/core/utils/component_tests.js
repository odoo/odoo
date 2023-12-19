/** @odoo-module alias=@web/../tests/core/utils/component_tests default=false */

import { ErrorHandler } from "@web/core/utils/components";
import { makeTestEnv } from "../../helpers/mock_env";
import { getFixture, mount } from "../../helpers/utils";

import { Component, xml } from "@odoo/owl";

QUnit.module("utils", () => {
    QUnit.module("components");

    QUnit.test("ErrorHandler component", async function (assert) {
        class Boom extends Component {
            static template = xml`<div><t t-esc="this.will.throw"/></div>`;
            static props = ["*"];
        }

        class Parent extends Component {
            static template = xml`
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
            static components = { Boom, ErrorHandler };
            static props = ["*"];
            setup() {
                this.flag = true;
            }
            handleError() {
                this.flag = false;
                this.render();
            }
        }

        const target = getFixture();
        await mount(Parent, target, { env: makeTestEnv() });
        assert.strictEqual(target.innerHTML, "<div> not boom </div>");
    });
});
