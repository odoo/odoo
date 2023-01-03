/** @odoo-module **/

import { ErrorHandler } from "@web/core/utils/components";
import { makeTestEnv } from "../../helpers/mock_env";
import { getFixture, mount } from "../../helpers/utils";

import { Component, xml } from "@odoo/owl";

QUnit.module("utils", () => {
    QUnit.module("components");

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
        await mount(Parent, target, { env: makeTestEnv() });
        assert.strictEqual(target.innerHTML, "<div> not boom </div>");
    });
});
