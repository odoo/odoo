import { expect, getFixture, mountOnFixture, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { ErrorHandler } from "@web/core/utils/components";

test("ErrorHandler component", async () => {
    class Boom extends Component {
        static template = xml`<div><t t-esc="this.will.throw"/></div>`;
        static props = ["*"];
    }

    class Parent extends Component {
        static template = xml`
            <div>
                <t t-if="flag">
                    <ErrorHandler onError="() => this.handleError()">
                        <Boom/>
                    </ErrorHandler>
                </t>
                <t t-else="">not boom</t>
            </div>
        `;
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

    await mountOnFixture(Parent);
    expect(getFixture()).toHaveText("not boom");
});
