import { expect, getFixture, mountOnFixture, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { Component, useChildSubEnv, xml } from "@odoo/owl";
import { ErrorHandler, WithEnv } from "@web/core/utils/components";

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

test("WithEnv component", async () => {
    class Child extends Component {
        static props = ["*"];
        static template = xml`
            <ul t-att-class="props.name">
                <li t-if="env.A">A=<t t-out="env.A"/></li>
                <li t-if="env.B">B=<t t-out="env.B"/></li>
            </ul>
        `;
    }
    class Parent extends Component {
        static props = ["*"];
        static template = xml`
            <Child name="'outer'"/>
            <WithEnv env="childEnv">
                <Child name="'inner'"/>
            </WithEnv>
        `;
        static components = { Child, WithEnv };
        setup() {
            useChildSubEnv({ A: "blip" });
            this.childEnv = { A: "gnap" };
        }
    }
    await mountOnFixture(Parent, { env: { A: "foo", B: "bar" } });
    expect(queryAllTexts("ul.outer > li")).toEqual(["A=blip", "B=bar"]);
    expect(queryAllTexts("ul.inner > li")).toEqual(["A=gnap"]);
});
