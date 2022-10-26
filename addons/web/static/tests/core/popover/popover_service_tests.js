/** @odoo-module **/

import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { clearRegistryWithCleanup, makeTestEnv } from "../../helpers/mock_env";
import { click, getFixture, mount, nextTick } from "../../helpers/utils";

const { Component, xml } = owl;

let env;
let fixture;
let popovers;
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
        <div id="sibling">Sibling</div>
        <div>
            <t t-foreach="Components" t-as="C" t-key="C[0]">
                <t t-component="C[1].Component" t-props="C[1].props"/>
            </t>
        </div>
    </div>
`;

QUnit.module("Popover service", {
    async beforeEach() {
        clearRegistryWithCleanup(mainComponents);
        registry.category("services").add("popover", popoverService);

        fixture = getFixture();
        env = await makeTestEnv();
        await mount(PseudoWebClient, fixture, { env });
        popovers = env.services.popover;
        popoverTarget = fixture.querySelector("#anchor");
    },
});

QUnit.test("simple use", async (assert) => {
    assert.containsOnce(fixture, ".o_popover_container");

    class Comp extends Component {}
    Comp.template = xml`<div id="comp">in popover</div>`;

    assert.containsNone(fixture, ".o_popover");

    const remove = popovers.add(popoverTarget, Comp, {});
    await nextTick();

    assert.containsOnce(fixture, ".o_popover");
    assert.containsOnce(fixture, ".o_popover #comp");

    remove();
    await nextTick();

    assert.containsNone(fixture, ".o_popover");
    assert.containsNone(fixture, ".o_popover #comp");
});

QUnit.test("close on click away", async (assert) => {
    assert.containsOnce(fixture, ".o_popover_container");

    class Comp extends Component {}
    Comp.template = xml`<div id="comp">in popover</div>`;

    popovers.add(popoverTarget, Comp, {});
    await nextTick();

    assert.containsOnce(fixture, ".o_popover");
    assert.containsOnce(fixture, ".o_popover #comp");

    await click(fixture, "#close");

    assert.containsNone(fixture, ".o_popover");
    assert.containsNone(fixture, ".o_popover #comp");
});

QUnit.test("do not close on click away", async (assert) => {
    assert.containsOnce(fixture, ".o_popover_container");

    class Comp extends Component {}
    Comp.template = xml`<div id="comp">in popover</div>`;

    const remove = popovers.add(popoverTarget, Comp, {}, { closeOnClickAway: false });
    await nextTick();

    assert.containsOnce(fixture, ".o_popover");
    assert.containsOnce(fixture, ".o_popover #comp");

    await click(fixture, "#close");

    assert.containsOnce(fixture, ".o_popover");
    assert.containsOnce(fixture, ".o_popover #comp");

    remove();
    await nextTick();

    assert.containsNone(fixture, ".o_popover");
    assert.containsNone(fixture, ".o_popover #comp");
});

QUnit.test("close callback", async (assert) => {
    assert.expect(3);

    assert.containsOnce(fixture, ".o_popover_container");

    class Comp extends Component {}
    Comp.template = xml`<div id="comp">in popover</div>`;

    function onClose() {
        assert.step("close");
    }

    popovers.add(popoverTarget, Comp, {}, { onClose });
    await nextTick();

    await click(fixture, "#close");

    assert.verifySteps(["close"]);
});

QUnit.test("sub component triggers close", async (assert) => {
    assert.containsOnce(fixture, ".o_popover_container");

    class Comp extends Component {}
    Comp.template = xml`<div id="comp" t-on-click="() => this.props.close()">in popover</div>`;

    popovers.add(popoverTarget, Comp, {});
    await nextTick();

    assert.containsOnce(fixture, ".o_popover");
    assert.containsOnce(fixture, ".o_popover #comp");

    await click(fixture, "#comp");

    assert.containsNone(fixture, ".o_popover");
    assert.containsNone(fixture, ".o_popover #comp");
});

QUnit.test("close popover if target is removed", async (assert) => {
    assert.containsOnce(fixture, ".o_popover_container");

    class Comp extends Component {}
    Comp.template = xml`<div id="comp">in popover</div>`;

    popovers.add(popoverTarget, Comp, {});
    await nextTick();

    assert.containsOnce(fixture, ".o_popover");
    assert.containsOnce(fixture, ".o_popover #comp");

    popoverTarget.remove();
    await nextTick();

    assert.containsNone(fixture, ".o_popover");
    assert.containsNone(fixture, ".o_popover #comp");
});

QUnit.test("keep popover if target sibling is removed", async (assert) => {
    assert.containsOnce(fixture, ".o_popover_container");

    class Comp extends Component {}
    Comp.template = xml`<div id="comp">in popover</div>`;

    popovers.add(popoverTarget, Comp, {});
    await nextTick();

    assert.containsOnce(fixture, ".o_popover");
    assert.containsOnce(fixture, ".o_popover #comp");

    fixture.querySelector("#sibling").remove();
    await nextTick();

    assert.containsOnce(fixture, ".o_popover");
    assert.containsOnce(fixture, ".o_popover #comp");
});
