import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, onWillStart, signal, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
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

test(`an interaction mounting a component crashing in onWillStart does not break edit mode`, async () => {
    expect.errors(1);
    class CrashingComponent extends Component {
        static template = xml`<div>crash</div>`;
        setup() {
            onWillStart(() => {
                throw new Error("crash in willStart");
            });
        }
    }
    class TestInteraction extends Interaction {
        static selector = ".test";
        start() {
            this.mountComponent(this.el, CrashingComponent);
        }
    }
    registry.category("public.interactions.edit").add("test.interaction", {
        Interaction: TestInteraction,
    });

    const { core } = await startInteractions(`<div class="test"></div>`);

    await switchToEditMode(core);
    await core.isReady;
    expect.verifyErrors(["crash in willStart"]);
    expect(core.owlApp.destroyed).not.toBe(true);
    expect(".test owl-root").toHaveCount(0);
});

test(`an interaction mounting a component crashing in setup removes its root in edit mode`, async () => {
    expect.errors(1);
    class CrashingComponent extends Component {
        static template = xml`<div>crash</div>`;
        setup() {
            throw new Error("crash in setup");
        }
    }
    class TestInteraction extends Interaction {
        static selector = ".test";
        start() {
            this.mountComponent(this.el, CrashingComponent);
        }
    }
    registry.category("public.interactions.edit").add("test.interaction", {
        Interaction: TestInteraction,
    });

    const { core } = await startInteractions(`<div class="test"></div>`);

    await switchToEditMode(core);
    await core.isReady;
    expect.verifyErrors(["crash in setup"]);
    expect(core.owlApp.destroyed).not.toBe(true);
    expect(".test owl-root").toHaveCount(0);
});

test(`an interaction component crashing after being mounted does not break edit mode`, async () => {
    expect.errors(1);
    const crash = signal(false);
    class CrashingComponent extends Component {
        static template = xml`<div class="crashing" t-out="this.label()"/>`;
        label() {
            if (crash()) {
                throw new Error("crash in re-render");
            }
            return "crash";
        }
    }
    class HealthyComponent extends Component {
        static template = xml`<div class="healthy">healthy</div>`;
    }
    class TestInteraction extends Interaction {
        static selector = ".test";
        start() {
            this.mountComponent(this.el, CrashingComponent);
            this.mountComponent(this.el, HealthyComponent);
        }
    }
    registry.category("public.interactions.edit").add("test.interaction", {
        Interaction: TestInteraction,
    });

    const { core } = await startInteractions(`<div class="test"></div>`);

    await switchToEditMode(core);
    await core.isReady;
    await animationFrame();
    expect(".test .crashing").toHaveCount(1);

    crash.set(true);
    await animationFrame();
    expect.verifyErrors(["crash in re-render"]);
    expect(core.owlApp.destroyed).not.toBe(true);
    expect(".test .crashing").toHaveCount(0);
    expect(".test owl-root").toHaveCount(1);
    expect(".test .healthy").toHaveCount(1);
});
