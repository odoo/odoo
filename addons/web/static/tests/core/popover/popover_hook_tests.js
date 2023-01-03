/** @odoo-module **/

import { usePopover } from "@web/core/popover/popover_hook";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { clearRegistryWithCleanup, makeTestEnv } from "../../helpers/mock_env";
import { destroy, getFixture, mount, nextTick } from "../../helpers/utils";

import { Component, xml } from "@odoo/owl";

let env;
let target;
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
        target = getFixture();
        env = await makeTestEnv();
        await mount(PseudoWebClient, target, { env });
        popoverTarget = target.querySelector("#anchor");
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

    const comp1 = await mount(CompWithPopover, target, { env });
    comp1.popover.add(popoverTarget, Comp, { id: "comp1" });
    await nextTick();

    const comp2 = await mount(CompWithPopover, target, { env });
    comp2.popover.add(popoverTarget, Comp, { id: "comp2" });
    await nextTick();

    assert.containsN(target, ".o_popover", 2);
    assert.containsOnce(target, ".o_popover #comp1");
    assert.containsOnce(target, ".o_popover #comp2");

    destroy(comp1);
    await nextTick();

    assert.containsOnce(target, ".o_popover");
    assert.containsNone(target, ".o_popover #comp1");
    assert.containsOnce(target, ".o_popover #comp2");

    destroy(comp2);
    await nextTick();

    assert.containsNone(target, ".o_popover");
    assert.containsNone(target, ".o_popover #comp1");
    assert.containsNone(target, ".o_popover #comp2");
});
