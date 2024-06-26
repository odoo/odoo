import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";
import "@web/public/public_component_service";

const publicComponentRegistry = registry.category("public_components");

test(`render Public Component`, async () => {
    class MyPublicComp extends Component {
        static template = xml`<div class="my_public_comp" t-esc="value"/>`;
        static props = ["*"];
        setup() {
            const { info } = this.props;
            this.value = typeof info === "object" ? JSON.stringify(info) : info;
            expect.step(`MyPublicComp: ${this.value} - ${typeof info}`);
        }
    }
    publicComponentRegistry.add("my_public_comp", MyPublicComp);

    class MyComponent extends Component {
        static template = xml`
            <div>
                <owl-component name="my_public_comp" props='{"info": "blibli"}'/>
                <owl-component name="my_public_comp" props='{"info": 3}'/>
                <owl-component name="my_public_comp" props='{"info": {"test": "plop"}}'/>
            </div>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(MyComponent);
    expect.verifySteps([]);

    await getService("public_component").mountComponents();
    await animationFrame();
    expect.verifySteps([
        "MyPublicComp: blibli - string",
        "MyPublicComp: 3 - number",
        'MyPublicComp: {"test":"plop"} - object',
    ]);

    expect(`.my_public_comp`).toHaveCount(3);
    expect(queryAllTexts`.my_public_comp`).toEqual(["blibli", "3", `{"test":"plop"}`]);

    getService("public_component").destroyComponents();
    await animationFrame();
    expect(`.my_public_comp`).toHaveCount(0);
    expect.verifySteps([]);
});
