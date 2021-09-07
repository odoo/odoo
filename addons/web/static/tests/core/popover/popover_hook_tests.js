/** @odoo-module **/

import { usePopover } from "@web/core/popover/popover_hook";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { registerCleanup } from "../../helpers/cleanup";
import { clearRegistryWithCleanup, makeTestEnv } from "../../helpers/mock_env";
import { getFixture, nextTick } from "../../helpers/utils";

const { Component, mount } = owl;
const { xml } = owl.tags;

let env;
let fixture;
let popoverTarget;

const mainComponents = registry.category("main_components");

class PseudoWebClient extends Component {
    setup() {
        this.Components = mainComponents.getEntries();
    }
}
PseudoWebClient.template = xml`
    <div>
        <div id="anchor">Anchor</div>
        <div id="close">Close</div>
        <div>
            <t t-foreach="Components" t-as="Component" t-key="Component[0]">
                <t t-component="Component[1].Component" t-props="Component[1].props"/>
            </t>
        </div>
    </div>
`;

QUnit.module("Popover hook", {
    async beforeEach() {
        clearRegistryWithCleanup(mainComponents);
        registry.category("services").add("popover", popoverService);

        fixture = getFixture();
        env = await makeTestEnv();
        const pseudoWebClient = await mount(PseudoWebClient, {
            env,
            target: fixture,
        });
        registerCleanup(() => {
            pseudoWebClient.destroy();
        });
        popoverTarget = fixture.querySelector("#anchor");
    },
});

QUnit.test("close popover when component is unmounted", async (assert) => {
    class Comp extends Component {}
    Comp.template = xml`<div t-att-id="props.id">in popover</div>`;

    class CompWithPopover extends Component {
        setup() {
            this.popover = usePopover();
        }
    }
    CompWithPopover.template = xml`<div />`;

    const comp1 = await mount(CompWithPopover, { env, target: fixture });
    comp1.popover.add(popoverTarget, Comp, { id: "comp1" });
    await nextTick();

    const comp2 = await mount(CompWithPopover, { env, target: fixture });
    comp2.popover.add(popoverTarget, Comp, { id: "comp2" });
    await nextTick();

    assert.containsN(fixture, ".o_popover", 2);
    assert.containsOnce(fixture, ".o_popover #comp1");
    assert.containsOnce(fixture, ".o_popover #comp2");

    comp1.destroy();
    await nextTick();

    assert.containsOnce(fixture, ".o_popover");
    assert.containsNone(fixture, ".o_popover #comp1");
    assert.containsOnce(fixture, ".o_popover #comp2");

    comp2.destroy();
    await nextTick();

    assert.containsNone(fixture, ".o_popover");
    assert.containsNone(fixture, ".o_popover #comp1");
    assert.containsNone(fixture, ".o_popover #comp2");
});
