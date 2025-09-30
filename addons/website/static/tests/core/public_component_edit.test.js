import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { startInteractions } from "@web/../tests/public/helpers";
import { switchToEditMode } from "../helpers";

const publicComponentRegistry = registry.category("public_components");
const publicComponentRegistryEdit = registry.category("public_components.edit");

test(`owl components are neutered in edit mode`, async () => {
    class MyPublicComp extends Component {
        static template = xml`<div>hello</div>`;
        static props = ["*"];
        setup() {}
    }
    publicComponentRegistry.add("my_public_comp", MyPublicComp);

    const html = `
            <div class="test">
                <owl-component name="my_public_comp"></owl-component>
            </div>
    `;

    const { core } = await startInteractions(html);
    await animationFrame();

    // components are now mounted
    expect(`.test`).toHaveInnerHTML(`
        <owl-component name="my_public_comp">
            <owl-root contenteditable="false" data-oe-protected="true" style="display: contents;">
                <div>hello</div>
            </owl-root>
        </owl-component>
    `);

    await switchToEditMode(core);
    await animationFrame();

    // in edit mode, we have pointer-events: none on owl-component
    expect(`.test`).toHaveInnerHTML(`
        <owl-component name="my_public_comp" style="pointer-events: none;">
            <owl-root contenteditable="false" data-oe-protected="true" style="display: contents;">
                <div>hello</div>
            </owl-root>
        </owl-component>
    `);
});

test(`edit owl components are not neutered in edit mode`, async () => {
    class MyPublicComp extends Component {
        static template = xml`<div>hello</div>`;
        static props = ["*"];
        setup() {}
    }
    publicComponentRegistry.add("my_public_comp", MyPublicComp);
    publicComponentRegistryEdit.add("my_public_comp", MyPublicComp);

    const html = `
            <div class="test">
                <owl-component name="my_public_comp"></owl-component>
            </div>
    `;

    const { core } = await startInteractions(html);
    await animationFrame();

    // components are now mounted
    expect(`.test`).toHaveInnerHTML(`
        <owl-component name="my_public_comp" >
            <owl-root contenteditable="false" data-oe-protected="true" style="display: contents;">
                <div>hello</div>
            </owl-root>
        </owl-component>
    `);

    await switchToEditMode(core);
    await animationFrame();

    // in edit mode, there should not be a pointer-events: none
    expect(`.test`).toHaveInnerHTML(`
        <owl-component name="my_public_comp" >
            <owl-root contenteditable="false" data-oe-protected="true" style="display: contents;">
                <div>hello</div>
            </owl-root>
        </owl-component>
    `);
});
