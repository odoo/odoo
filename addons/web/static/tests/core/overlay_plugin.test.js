import { expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    Component,
    Plugin,
    effect,
    providePlugins,
    useConfig,
    usePlugin,
    useProps,
    useScope,
    xml,
} from "@odoo/owl";
import {
    assignTestEnv,
    getService,
    makeTestApp,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";

import { MainComponentsContainer } from "@web/core/main_components_container";
import { useService } from "@web/core/utils/hooks";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";

test("simple case", async () => {
    await mountWithCleanup(MainComponentsContainer);
    expect(".o-overlay-container").toHaveCount(1);

    class MyComp extends Component {
        static template = xml`
            <div class="overlayed"></div>
        `;
    }

    const remove = getService(OverlayPlugin).add(MyComp, {});
    await animationFrame();
    expect(".o-overlay-container .overlayed").toHaveCount(1);

    remove();
    await animationFrame();
    expect(".o-overlay-container .overlayed").toHaveCount(0);
});

test("shadow DOM overlays are visible when registered before main component is mounted", async () => {
    class MyComp extends Component {
        static template = xml`
            <div class="overlayed"></div>
        `;
    }

    const root = document.createElement("div");
    root.setAttribute("id", "my-root-id");
    root.attachShadow({ mode: "open" });
    getFixture().appendChild(root);

    assignTestEnv({ rootId: "my-root-id" });
    await makeTestApp();
    getService(OverlayPlugin).add(MyComp, {}, { rootId: "my-root-id" });
    await mountWithCleanup(MainComponentsContainer, {
        target: root.shadowRoot,
    });
    await animationFrame();

    expect("#my-root-id:shadow .o-overlay-container .overlayed").toHaveCount(1);
});

test("onRemove callback", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class MyComp extends Component {
        static template = xml``;
    }

    const onRemove = () => expect.step("onRemove");
    const remove = getService(OverlayPlugin).add(MyComp, {}, { onRemove });

    expect.verifySteps([]);
    remove();
    expect.verifySteps(["onRemove"]);
});

test("multiple overlays", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class MyComp extends Component {
        static template = xml`
            <div class="overlayed" t-att-class="this.props.className"></div>
        `;
        props = useProps();
    }

    const remove1 = getService(OverlayPlugin).add(MyComp, { className: "o1" });
    const remove2 = getService(OverlayPlugin).add(MyComp, { className: "o2" });
    const remove3 = getService(OverlayPlugin).add(MyComp, { className: "o3" });
    await animationFrame();
    expect(".overlayed").toHaveCount(3);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o1");
    expect(".o-overlay-container :nth-child(2) .overlayed").toHaveClass("o2");
    expect(".o-overlay-container :nth-child(3) .overlayed").toHaveClass("o3");

    remove1();
    await animationFrame();
    expect(".overlayed").toHaveCount(2);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o2");
    expect(".o-overlay-container :nth-child(2) .overlayed").toHaveClass("o3");

    remove2();
    await animationFrame();
    expect(".overlayed").toHaveCount(1);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o3");

    remove3();
    await animationFrame();
    expect(".overlayed").toHaveCount(0);
});

test("sequence", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class MyComp extends Component {
        static template = xml`
            <div class="overlayed" t-att-class="this.props.className"></div>
        `;
        props = useProps();
    }

    const remove1 = getService(OverlayPlugin).add(MyComp, { className: "o1" }, { sequence: 50 });
    const remove2 = getService(OverlayPlugin).add(MyComp, { className: "o2" }, { sequence: 60 });
    const remove3 = getService(OverlayPlugin).add(MyComp, { className: "o3" }, { sequence: 40 });
    await animationFrame();
    expect(".overlayed").toHaveCount(3);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o3");
    expect(".o-overlay-container :nth-child(2) .overlayed").toHaveClass("o1");
    expect(".o-overlay-container :nth-child(3) .overlayed").toHaveClass("o2");

    remove1();
    await animationFrame();
    expect(".overlayed").toHaveCount(2);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o3");
    expect(".o-overlay-container :nth-child(2) .overlayed").toHaveClass("o2");

    remove2();
    await animationFrame();
    expect(".overlayed").toHaveCount(1);
    expect(".o-overlay-container :nth-child(1) .overlayed").toHaveClass("o3");

    remove3();
    await animationFrame();
    expect(".overlayed").toHaveCount(0);
});

test("allow scope as option", async () => {
    class MyPlugin extends Plugin {
        A = useConfig("a");
        B = useConfig("b");
    }

    class Overlay extends Component {
        static template = xml`
            <ul class="outer">
                <li>A=<t t-out="this.p.A"/></li>
                <li>B=<t t-out="this.p.B"/></li>
            </ul>
        `;
        p = usePlugin(MyPlugin);
    }

    class Parent extends Component {
        static template = xml``;
        setup() {
            providePlugins([MyPlugin], { a: "foo", b: "bar" });
            const scope = useScope();
            useService("overlay").add(Overlay, {}, { scope });
        }
    }

    await mountWithCleanup(Parent);
    expect(".o-overlay-container li:nth-child(1)").toHaveText("A=foo");
    expect(".o-overlay-container li:nth-child(2)").toHaveText("B=bar");
});

test("add() does not leak as a reactive dependency into an unrelated caller's effect", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class MyComp extends Component {
        static template = xml`
            <div class="overlayed"></div>
        `;
    }
    class OtherComp extends Component {
        static template = xml``;
    }

    const plugin = getService(OverlayPlugin);

    let runCount = 0;
    const cleanup = effect(() => {
        runCount++;
        plugin.add(MyComp, {});
    });
    await animationFrame();
    expect(runCount).toBe(1);
    expect(".o-overlay-container .overlayed").toHaveCount(1);

    const removeOther = plugin.add(OtherComp, {});
    await animationFrame();
    expect(runCount).toBe(1);
    expect(".o-overlay-container .overlayed").toHaveCount(1);

    removeOther();
    await animationFrame();
    expect(runCount).toBe(1);

    cleanup();
});
