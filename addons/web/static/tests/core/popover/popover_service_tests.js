/** @odoo-module **/

import { Popover } from "@web/core/popover/popover";
import {
    KeyAlreadyExistsError,
    KeyNotFoundError,
    PopoverManager,
    popoverService,
} from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/service_hook";
import { registerCleanup } from "../../helpers/cleanup";
import { clearRegistryWithCleanup, makeTestEnv } from "../../helpers/mock_env";
import { click, getFixture, nextTick } from "../../helpers/utils";

const { Component, mount } = owl;
const { xml } = owl.tags;

let env;
let pseudoWebClient;
let popovers;
const mainComponentRegistry = registry.category("main_components");
const serviceRegistry = registry.category("services");

class PseudoWebClient extends Component {
    setup() {
        this.Components = mainComponentRegistry.getEntries();
    }
}
PseudoWebClient.template = xml`
    <div>
        <div id="anchor">Anchor</div>
        <div id="close">Close</div>
        <div>
            <t t-foreach="Components" t-as="Component" t-key="Component[0]">
                <t t-component="Component[1]"/>
            </t>
        </div>
    </div>
`;

QUnit.module("PopoverManager", {
    async beforeEach() {
        serviceRegistry.add("popover", popoverService);
        clearRegistryWithCleanup(mainComponentRegistry);
        mainComponentRegistry.add("PopoverManager", PopoverManager);
        env = await makeTestEnv();
        pseudoWebClient = await mount(PseudoWebClient, {
            env,
            target: getFixture(),
        });
        popovers = env.services.popover;
        registerCleanup(() => {
            pseudoWebClient.destroy();
        });
    },
});

QUnit.test("Render custom popover component", async function (assert) {
    assert.expect(10);

    class CustomPopover extends Component {}
    CustomPopover.components = { Popover };
    CustomPopover.template = xml`
        <Popover target="props.target">
            <t t-set-slot="content">
                <div>Popover</div>
            </t>
        </Popover>
    `;

    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    popovers.add({
        Component: CustomPopover,
        props: {
            target: "#anchor",
        },
    });
    await nextTick();

    await click(pseudoWebClient.el, "#anchor");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    await click(pseudoWebClient.el, "#close");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");
});

QUnit.test("Render popover with content arg", async function (assert) {
    assert.expect(11);

    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    popovers.add({
        content: "skibidi",
        props: {
            target: "#anchor",
        },
    });
    await nextTick();

    await click(pseudoWebClient.el, "#anchor");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.strictEqual(
        pseudoWebClient.el.querySelector(".o_popover_container .o_popover").textContent,
        "skibidi"
    );
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    await click(pseudoWebClient.el, "#close");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");
});

QUnit.test("Callback on close", async function (assert) {
    assert.expect(2);

    popovers.add({
        content: "skibidi",
        onClose() {
            assert.step("close");
        },
        props: {
            target: "#anchor",
        },
    });
    await nextTick();

    await click(pseudoWebClient.el, "#anchor");
    await click(pseudoWebClient.el, "#close");

    assert.verifySteps(["close"]);
});

QUnit.test("Keep popover in manager after close", async function (assert) {
    assert.expect(9);

    popovers.add({
        content: "skibidi",
        keepOnClose: true,
        props: {
            target: "#anchor",
        },
    });
    await nextTick();

    await click(pseudoWebClient.el, "#anchor");

    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    await click(pseudoWebClient.el, "#close");

    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    await click(pseudoWebClient.el, "#anchor");

    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");
});

QUnit.test("Remove popover manually", async function (assert) {
    assert.expect(6);

    popovers.add({
        key: "test",
        content: "skibidi",
        props: {
            target: "#anchor",
            trigger: "none",
        },
    });
    await nextTick();

    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    popovers.remove("test");
    await nextTick();

    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");
});

QUnit.test("Remove popover manually when click does not throw", async function (assert) {
    assert.expect(6);

    const close = pseudoWebClient.el.querySelector("#close");
    close.addEventListener("click", () => popovers.remove("test"));

    popovers.add({
        key: "test",
        content: "skibidi",
        props: {
            target: "#anchor",
            trigger: "none",
        },
    });
    await nextTick();

    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    await click(pseudoWebClient.el, "#close");

    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");
});

QUnit.test("Check errors", async function (assert) {
    assert.expect(2);

    popovers.add({ key: "test" });
    assert.throws(() => {
        popovers.add({ key: "test" });
    }, KeyAlreadyExistsError);

    popovers.remove("test");
    assert.throws(() => {
        popovers.remove("test");
    }, KeyNotFoundError);
});

QUnit.test("remove popover when component is unmount", async function (assert) {
    assert.expect(12);

    class MyComp extends Component {
        setup() {
            this.popoverService = useService("popover");
        }
        showPopover(key) {
            const params = {
                content: "skibidi",
                props: {
                    target: "#anchor",
                    trigger: "none",
                },
            };
            if (key) {
                params.key = key;
            }
            return this.popoverService.add(params);
        }
        hidePopover(key) {
            this.popoverService.remove(key);
        }
    }
    MyComp.template = xml`<div></div>`;

    const comp1 = await mount(MyComp, { env, target: getFixture() });
    const comp2 = await mount(MyComp, { env, target: getFixture() });

    comp1.showPopover("An other key");
    await nextTick();

    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    comp1.destroy();
    await nextTick();

    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    comp2.showPopover();
    await nextTick();

    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    comp2.destroy();
    await nextTick();

    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");
});

QUnit.test("service does not try to remove destroyed popover", async function (assert) {
    assert.expect(6);

    class MyComp extends Component {
        setup() {
            this.popoverService = useService("popover");
        }
        showPopover() {
            const params = {
                content: "skibidi",
                props: {
                    target: "#anchor",
                    trigger: "none",
                },
            };
            return this.popoverService.add(params);
        }
        hidePopover(key) {
            this.popoverService.remove(key);
        }
    }
    MyComp.template = xml`<div></div>`;

    const comp = await mount(MyComp, { env, target: getFixture() });
    const key = comp.showPopover();
    await nextTick();

    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    comp.hidePopover(key);
    await nextTick();

    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    comp.destroy();
});

QUnit.test("popover kept on close is removed when component unmount", async function (assert) {
    assert.expect(13);

    class MyComp extends Component {
        setup() {
            this.popoverService = useService("popover");
        }
        showPopover() {
            const params = {
                content: "skibidi",
                props: {
                    target: "#anchor",
                    trigger: "click",
                },
                keepOnClose: true,
            };
            return this.popoverService.add(params);
        }
    }
    MyComp.template = xml`<div></div>`;

    const comp = await mount(MyComp, { env, target: getFixture() });
    comp.showPopover();
    await nextTick();
    await click(pseudoWebClient.el, "#anchor");

    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    await click(pseudoWebClient.el, "#close");

    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    comp.unmount();
    await nextTick();
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    await comp.mount(getFixture());

    comp.showPopover();
    await nextTick();
    await click(pseudoWebClient.el, "#anchor");

    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsOnce(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");

    comp.destroy();
    await nextTick();

    assert.containsNone(pseudoWebClient.el, ".o_popover_manager portal");
    assert.containsNone(pseudoWebClient.el, ".o_popover_container .o_popover");
    assert.containsNone(pseudoWebClient.el, ".o_popover_manager > div:not(.o_popover_container)");
});
