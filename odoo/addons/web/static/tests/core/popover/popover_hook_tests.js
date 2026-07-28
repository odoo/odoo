/** @odoo-module **/

import { usePopover } from "@web/core/popover/popover_hook";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { clearRegistryWithCleanup, makeTestEnv } from "../../helpers/mock_env";
import { click, destroy, getFixture, mount, nextTick } from "../../helpers/utils";

import { Component, xml } from "@odoo/owl";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { makeFakeLocalizationService } from "../../helpers/mock_services";

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
        registry
            .category("services")
            .add("popover", popoverService)
            .add("localization", makeFakeLocalizationService())
            .add("hotkey", hotkeyService);
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
            this.popover = usePopover(Comp);
        }
    }
    CompWithPopover.template = xml`<div />`;

    const comp1 = await mount(CompWithPopover, target, { env });
    comp1.popover.open(popoverTarget, { id: "comp1" });
    await nextTick();

    const comp2 = await mount(CompWithPopover, target, { env });
    comp2.popover.open(popoverTarget, { id: "comp2" });
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

QUnit.test("popover opened from another", async (assert) => {
    class Comp extends Component {
        static id = 0;
        static template = xml`
            <div class="p-4">
                <button class="pop-open" t-on-click="(ev) => this.popover.open(ev.target, {})">open popover</button>
            </div>
        `;
        setup() {
            this.popover = usePopover(Comp, {
                popoverClass: `popover-${++Comp.id}`,
            });
        }
    }

    await mount(Comp, target, { env });

    await click(target, ".pop-open");
    assert.containsOnce(target, ".popover-1", "open first popover");

    await click(target, ".popover-1 .pop-open");
    assert.containsN(target, ".o_popover", 2, "open second popover from the first one");
    assert.containsOnce(target, ".popover-1");
    assert.containsOnce(target, ".popover-2");

    await click(target, ".popover-2 .pop-open");
    assert.containsN(target, ".o_popover", 3, "open third popover from the second one");
    assert.containsOnce(target, ".popover-1");
    assert.containsOnce(target, ".popover-2");
    assert.containsOnce(target, ".popover-3");

    await click(target, ".popover-3");
    assert.containsN(target, ".o_popover", 3, "clicking inside third popover closes nothing");
    assert.containsOnce(target, ".popover-1");
    assert.containsOnce(target, ".popover-2");
    assert.containsOnce(target, ".popover-3");

    await click(target, ".popover-2");
    assert.containsN(
        target,
        ".o_popover",
        2,
        "clicking inside second popover closes third popover"
    );
    assert.containsOnce(target, ".popover-1");
    assert.containsOnce(target, ".popover-2");

    await click(target, "#close");
    assert.containsNone(target, ".o_popover", "clicking out of any popover closes them all");
});
