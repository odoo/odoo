import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { setupInteractionWhiteList, startInteractions } from "./helpers";
import { registry } from "@web/core/registry";

setupInteractionWhiteList("public_components");

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

    const html = `
            <div>
                <owl-component name="my_public_comp" props='{"info": "blibli"}'></owl-component>
                <owl-component name="my_public_comp" props='{"info": 3}'></owl-component>
                <owl-component name="my_public_comp" props='{"info": {"test": "plop"}}'></owl-component>
            </div>
    `;

    await startInteractions(html);
    // interaction is now ready, but components not mounted yet
    expect(`.my_public_comp`).toHaveCount(0);
    expect.verifySteps([
        "MyPublicComp: blibli - string",
        "MyPublicComp: 3 - number",
        'MyPublicComp: {"test":"plop"} - object',
    ]);

    await animationFrame();
    // components are now mounted
    expect(`.my_public_comp`).toHaveCount(3);
    expect(queryAllTexts`.my_public_comp`).toEqual(["blibli", "3", `{"test":"plop"}`]);
});

test(`content of owl-component tag is cleared`, async () => {
    class MyPublicComp extends Component {
        static template = xml`<div>component</div>`;
        static props = ["*"];
    }
    publicComponentRegistry.add("my_public_comp", MyPublicComp);

    const html = `
            <div>
                <owl-component name="my_public_comp">some content</owl-component>
            </div>
    `;

    await startInteractions(html);
    await animationFrame();
    expect(`.my_public_comp`).toHaveCount(0);
    expect("owl-component").toHaveOuterHTML(`
        <owl-component name="my_public_comp">
            <owl-root contenteditable="false" data-oe-protected="true" style="display: contents;">
                <div> component </div>
            </owl-root> 
        </owl-component>`);
});
