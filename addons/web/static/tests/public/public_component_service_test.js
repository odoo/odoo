/** @odoo-module **/

import { registry } from "@web/core/registry";
import { publicComponentService } from "@web/public/public_component_service";
import { getFixture, mount, nextTick } from "../helpers/utils";
import { makeTestEnv } from "../helpers/mock_env";
import { Component, xml } from "@odoo/owl";

let target;

const serviceRegistry = registry.category("services");
const publicComponentRegistry = registry.category("public_components");

QUnit.module("Public Component Service", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serviceRegistry.add("public_components", publicComponentService);
    });
    QUnit.test("render Public Component", async (assert) => {
        class MyPublicComp extends Component {
            static template = xml`<div class="my_public_comp" t-esc="value" />`;
            setup() {
                const type = typeof this.props.info;
                this.value = type === "object" ? JSON.stringify(this.props.info) : this.props.info;
                assert.step(`MyPublicComp: ${this.value} - ${type}`);
            }
        }
        publicComponentRegistry.add("my_public_comp", MyPublicComp);

        class MyComponent extends Component {
            static template = xml`
                <div>
                    <owl-component name="my_public_comp" props='{"info": "blibli"}'/>
                    <owl-component name="my_public_comp" props='{"info": 3}'/>
                    <owl-component name="my_public_comp" props='{"info": {"test": "plop"}}'/>
                </div>`;
        }
        const env = await makeTestEnv({});
        await mount(MyComponent, target, { env });

        await env.services.public_components.mountComponents();
        await nextTick();
        assert.containsN(target, ".my_public_comp", 3);
        assert.deepEqual(
            [...target.querySelectorAll(".my_public_comp")].map((el) => el.textContent),
            ["blibli", "3", '{"test":"plop"}']
        );

        env.services.public_components.destroyComponents();
        await nextTick();
        assert.containsN(target, ".my_public_comp", 0);

        assert.verifySteps([
            "MyPublicComp: blibli - string",
            "MyPublicComp: 3 - number",
            'MyPublicComp: {"test":"plop"} - object',
        ]);
    });
});
