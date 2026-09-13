// @ts-check

import { expect, getFixture, onError, test } from "@odoo/hoot";
import { queryAll, queryOne, resize } from "@odoo/hoot-dom";
import { animationFrame, mockTouch, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    defineActions,
    defineModels,
    fields,
    getService,
    makeMockEnv,
    models,
    mountWebClient,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { attachShadowRoot, getTabableElements } from "@web/core/utils/dom/ui";
import { ConfirmationDialog } from "@web/ui/dialog/confirmation_dialog";
import { Dialog } from "@web/ui/dialog/dialog";
import { RainbowMan } from "@web/ui/effects/rainbow_man";
import { MainComponentsContainer } from "@web/ui/main_components_container";
import { OverlayContainer } from "@web/ui/overlay/overlay_container";
import { makeOverlayPresenter } from "@web/ui/overlay/presenter";
import {
    getDetachedTargetObserverCount,
    watchForDetachedTarget,
} from "@web/ui/popover/detached_target_watcher";
import { Popover } from "@web/ui/popover/popover";
import { usePopover } from "@web/ui/popover/popover_hook";

class Partner extends models.Model {
    name = fields.Char();
    _records = [
        { id: 1, name: "p1" },
        { id: 2, name: "p2" },
    ];
    _views = {
        list: `<list><field name="name"/></list>`,
        search: `<search/>`,
    };
}
defineModels({ ...webModels, Partner });
defineActions([
    { id: 1, name: "Partners", res_model: "partner", views: [[false, "list"]] },
]);

class Content extends Component {
    static template = xml`<div class="popover-content"/>`;
    static props = ["*"];
}

class DialogContent extends Component {
    static template = xml`<Dialog title="'t'"><div class="dlg-body"/></Dialog>`;
    static components = { Dialog };
    static props = ["*"];
}

test("detachment tracking notices removal of a shadow host", async () => {
    const host = document.createElement("div");
    getFixture().append(host);
    const root = attachShadowRoot(host);
    const target = document.createElement("button");
    root.append(target);
    const dispose = watchForDetachedTarget(target, () => expect.step("detached"));
    try {
        await animationFrame();
        expect.verifySteps([]);
        host.remove();
        await animationFrame();
        expect.verifySteps(["detached"]);
    } finally {
        dispose();
    }
    expect(getDetachedTargetObserverCount()).toBe(0);
});

test("detachment tracking follows a target moved into another shadow root", async () => {
    const first = document.createElement("div");
    const second = document.createElement("div");
    getFixture().append(first, second);
    const firstRoot = attachShadowRoot(first);
    const secondRoot = attachShadowRoot(second);
    const target = document.createElement("button");
    firstRoot.append(target);
    const dispose = watchForDetachedTarget(target, () => expect.step("detached"));
    try {
        secondRoot.append(target);
        await animationFrame();
        expect.verifySteps([]);
        target.remove();
        await animationFrame();
        expect.verifySteps(["detached"]);
    } finally {
        dispose();
    }
    expect(getDetachedTargetObserverCount()).toBe(0);
});

test("nested shadow roots share ancestor observers and release them independently", async () => {
    const outer = document.createElement("div");
    getFixture().append(outer);
    const outerRoot = attachShadowRoot(outer);
    const inner = document.createElement("div");
    outerRoot.append(inner);
    const innerRoot = attachShadowRoot(inner, { mode: "closed" });
    const target = document.createElement("button");
    innerRoot.append(target);
    const first = watchForDetachedTarget(target, () => expect.step("first"));
    const second = watchForDetachedTarget(target, () => expect.step("second"));
    try {
        expect(getDetachedTargetObserverCount()).toBe(3);
        first();
        first();
        expect(getDetachedTargetObserverCount()).toBe(3);
        outer.remove();
        await animationFrame();
        expect.verifySteps(["second"]);
    } finally {
        first();
        second();
    }
    expect(getDetachedTargetObserverCount()).toBe(0);
});

test.tags("mobile");
test("closing a mobile dropdown does not reload the action behind it", async () => {
    mockTouch(true);
    await resize({ width: 375, height: 667 });

    /** @type {string[]} */
    const calls = [];
    let recording = false;
    onRpc(({ model, method }) => {
        if (recording) {
            calls.push(`${model}.${method}`);
        }
    });

    await mountWebClient();
    await getService("action").doAction(1);
    await animationFrame();
    await runAllTimers();
    expect(".o_list_view").toHaveCount(1);
    const controllerBefore = getService("action").currentController?.jsId;

    recording = true;
    for (const toggle of queryAll(".o-dropdown")) {
        toggle.click();
        await animationFrame();
        await animationFrame();
        if (queryAll(".o_bottom_sheet").length) {
            break;
        }
    }
    expect(".o_bottom_sheet").toHaveCount(1);

    queryOne(".o_bottom_sheet_backdrop").click();
    await animationFrame();
    await runAllTimers();
    await animationFrame();
    await runAllTimers();
    recording = false;

    expect(".o_bottom_sheet").toHaveCount(0);
    expect(calls).toEqual([]);
    expect(getService("action").currentController?.jsId).toBe(controllerBefore);
});

let wantSheet = false;
class SheetHost extends Component {
    static template = xml`<div class="host"/>`;
    static props = ["*"];
    setup() {
        this.popover = usePopover(Content, { useBottomSheet: () => wantSheet });
    }
}

test("usePopover re-reads useBottomSheet on every open", async () => {
    await makeMockEnv();
    wantSheet = false;
    const host = await mountWithCleanup(SheetHost);

    host.popover.open(queryOne(".host"), {});
    await animationFrame();
    expect(".o_bottom_sheet").toHaveCount(0);
    expect(".o_popover").toHaveCount(1);
    host.popover.close();
    await animationFrame();

    wantSheet = true;
    host.popover.open(queryOne(".host"), {});
    await animationFrame();
    expect(".o_bottom_sheet").toHaveCount(1);
    expect(".o_popover").toHaveCount(0);
});

test("Dropdown follows the breakpoint without being remounted", async () => {
    mockTouch(true);
    await resize({ width: 1366, height: 768 });
    class Host extends Component {
        static components = { Dropdown };
        static props = ["*"];
        static template = xml`
            <Dropdown>
                <button class="dd-toggle">t</button>
                <t t-set-slot="content"><span class="dd-item">i</span></t>
            </Dropdown>`;
    }
    await makeMockEnv();
    await mountWithCleanup(Host);
    await animationFrame();

    queryOne(".dd-toggle").click();
    await animationFrame();
    expect(".o_bottom_sheet").toHaveCount(0);
    queryOne(".dd-toggle").click();
    await animationFrame();

    await resize({ width: 375, height: 667 });
    await runAllTimers();
    await animationFrame();

    queryOne(".dd-toggle").click();
    await animationFrame();
    await animationFrame();
    expect(".o_bottom_sheet").toHaveCount(1);
});

test("popovers share one detached-target observer per root", async () => {
    await makeMockEnv();
    class Host extends Component {
        static props = ["*"];
        static template = xml`
            <div>
                <div class="t1">1</div><div class="t2">2</div><div class="t3">3</div>
            </div>`;
    }
    await mountWithCleanup(Host);
    expect(getDetachedTargetObserverCount()).toBe(0);

    let observeCalls = 0;
    let disconnectCalls = 0;
    const Native = MutationObserver;
    patchWithCleanup(globalThis, {
        MutationObserver: class extends Native {
            observe(target, options) {
                observeCalls++;
                return super.observe(target, options);
            }
            disconnect() {
                disconnectCalls++;
                return super.disconnect();
            }
        },
    });

    const disposers = [
        watchForDetachedTarget(queryOne(".t1"), () => {}),
        watchForDetachedTarget(queryOne(".t2"), () => {}),
        watchForDetachedTarget(queryOne(".t3"), () => {}),
    ];
    expect(observeCalls).toBe(1);
    expect(getDetachedTargetObserverCount()).toBe(1);

    for (const dispose of disposers) {
        dispose();
    }
    expect(getDetachedTargetObserverCount()).toBe(0);
    expect(disconnectCalls).toBe(1);
});

test("a popover still closes when its target leaves the DOM", async () => {
    await makeMockEnv();
    class Host extends Component {
        static props = ["*"];
        static template = xml`<div class="wrap"><div class="anchor">a</div></div>`;
    }
    await mountWithCleanup(Host);
    const target = queryOne(".anchor");
    await mountWithCleanup(Popover, {
        props: { component: Content, target, close: () => expect.step("closed") },
    });
    await animationFrame();
    expect.verifySteps([]);

    target.remove();
    await animationFrame();
    await animationFrame();
    expect.verifySteps(["closed"]);
});

test("a hosted rainbowman component keeps its clicks", async () => {
    class Hosted extends Component {
        static template = xml`<button class="rm-btn" t-on-click="onClick">go</button>`;
        static props = ["*"];
        onClick() {
            expect.step("button");
        }
    }
    await mountWithCleanup(RainbowMan, {
        props: {
            fadeout: "no",
            close: () => expect.step("closed"),
            message: "hi",
            imgUrl: "/web/static/img/smile.svg",
            Component: Hosted,
            props: {},
        },
    });
    await animationFrame();
    queryOne(".rm-btn").click();
    await animationFrame();
    expect.verifySteps(["button"]);

    document.body.click();
    await animationFrame();
    expect.verifySteps(["closed"]);
});

test("a message-only rainbowman still closes on any click", async () => {
    await mountWithCleanup(RainbowMan, {
        props: {
            fadeout: "no",
            close: () => expect.step("closed"),
            message: "well done",
            imgUrl: "/web/static/img/smile.svg",
        },
    });
    await animationFrame();
    queryOne(".o_reward_msg_content").click();
    await animationFrame();
    expect.verifySteps(["closed"]);
});

test.tags("desktop");
test("a dialog waiting on a slow onClose says so instead of looking stuck", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    /** @type {(v?: any) => void} */
    let release = () => {};
    const slow = new Promise((r) => (release = r));
    getService("dialog").add(DialogContent, {}, { onClose: () => slow });
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog_closing").toHaveCount(0);
    expect(".o_dialog .btn-close").not.toHaveAttribute("disabled");

    queryOne(".o_dialog .btn-close").click();
    await animationFrame();
    await animationFrame();

    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog_closing").toHaveCount(1);
    expect(".o_dialog .btn-close").toHaveAttribute("disabled");

    release();
    await animationFrame();
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);
});

test.tags("desktop");
test("confirmation dialog disables its buttons declaratively", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    /** @type {(v?: any) => void} */
    let release = () => {};
    const slow = new Promise((r) => (release = r));
    getService("dialog").add(ConfirmationDialog, {
        body: "sure?",
        confirm: () => slow,
        cancel: () => {},
    });
    await animationFrame();
    expect(".modal-footer button:not([disabled])").toHaveCount(2);

    queryOne(".modal-footer button:first").click();
    await animationFrame();
    expect(".modal-footer button[disabled]").toHaveCount(2);

    release();
    await animationFrame();
    await animationFrame();
    expect(".modal").toHaveCount(0);
});

test("a popstate that does not move the page leaves popovers open", async () => {
    await makeMockEnv();
    class Host extends Component {
        static props = ["*"];
        static template = xml`<div class="anchor">a</div>`;
    }
    await mountWithCleanup(Host);
    getService("popover").add(queryOne(".anchor"), Content, {});
    await animationFrame();
    expect(".o_popover").toHaveCount(1);

    window.dispatchEvent(new PopStateEvent("popstate", { state: null }));
    await animationFrame();
    expect(".o_popover").toHaveCount(1);
});

test("unblocking more than blocking does not broadcast a phantom unblock", async () => {
    await makeMockEnv();
    const ui = getService("ui");
    ui.bus.addEventListener("UNBLOCK", () => expect.step("UNBLOCK"));

    ui.unblock();
    expect.verifySteps([]);

    ui.block();
    ui.unblock();
    expect.verifySteps(["UNBLOCK"]);
});

test("the overlay presenter reads each option getter exactly once", async () => {
    let classReads = 0;
    let positionReads = 0;
    /** @type {any[]} */
    const added = [];
    const add = makeOverlayPresenter({
        overlay: {
            add(component, props) {
                added.push(props);
                return () => {};
            },
        },
        component: /** @type {any} */ (class {}),
        toProps: (options) => ({ position: options.position }),
    });
    add(
        /** @type {any} */ (document.body),
        /** @type {any} */ (class {}),
        {},
        {
            get class() {
                classReads++;
                return `cls-${classReads}`;
            },
            get position() {
                positionReads++;
                return `pos-${positionReads}`;
            },
        },
    );

    expect(classReads).toBe(1);
    expect(positionReads).toBe(1);
    expect(added[0].class).toBe("cls-1");
    expect(added[0].position).toBe("pos-1");
    expect(added[0].class).toBe("cls-1");
    expect(classReads).toBe(1);
    expect(positionReads).toBe(1);
});

class ClosingContent extends Component {
    static template = xml`<button class="closer" t-on-click="() => this.props.close({ answer: 42 })">x</button>`;
    static props = ["*"];
}

test.tags("mobile");
test("a bottom sheet forwards its hosted component's close parameters", async () => {
    mockTouch(true);
    await resize({ width: 375, height: 667 });
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    /** @type {any[]} */
    const seen = [];
    class Host extends Component {
        static template = xml`<div class="host"/>`;
        static props = ["*"];
        setup() {
            this.popover = usePopover(ClosingContent, {
                useBottomSheet: () => true,
                onClose: (params) => seen.push(params),
            });
        }
    }
    const host = await mountWithCleanup(Host);
    host.popover.open(queryOne(".host"), {});
    await animationFrame();
    await animationFrame();
    expect(".o_bottom_sheet").toHaveCount(1);

    queryOne(".closer").click();
    await runAllTimers();
    await animationFrame();
    expect(seen).toEqual([{ answer: 42 }]);
});

test("a popover forwards its hosted component's close parameters", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    /** @type {any[]} */
    const seen = [];
    class Host extends Component {
        static template = xml`<div class="host"/>`;
        static props = ["*"];
        setup() {
            this.popover = usePopover(ClosingContent, {
                onClose: (params) => seen.push(params),
            });
        }
    }
    const host = await mountWithCleanup(Host);
    host.popover.open(queryOne(".host"), {});
    await animationFrame();

    queryOne(".closer").click();
    await runAllTimers();
    await animationFrame();
    expect(seen).toEqual([{ answer: 42 }]);
});

test("a slotted popover is rejected rather than silently empty", async () => {
    await makeMockEnv();
    class SlotHost extends Component {
        static template = xml`<Popover target="target" close="() => {}" component="comp"><div class="slotted"/></Popover>`;
        static components = { Popover };
        static props = ["*"];
        setup() {
            this.target = document.body;
            this.comp = Content;
        }
    }
    let message = "none";
    onError((ev) => {
        const error = "reason" in ev ? ev.reason : ev.error;
        message = String(error?.message ?? error);
        ev.preventDefault();
    });
    try {
        await mountWithCleanup(SlotHost);
        await animationFrame();
    } catch (e) {
        message = String(e?.message ?? e);
    }
    expect(message).toInclude("slots");
    expect(".slotted").toHaveCount(0);
});

test("both presenters honour the class alias and the class option", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);
    class Host extends Component {
        static template = xml`<div class="anchor">a</div>`;
        static props = ["*"];
    }
    await mountWithCleanup(Host);
    const anchor = queryOne(".anchor");

    const closePopover = getService("popover").add(
        anchor,
        Content,
        {},
        {
            class: "via-alias",
        },
    );
    await animationFrame();
    expect(".o_popover.via-alias").toHaveCount(1);
    closePopover();
    await animationFrame();

    getService("popover").add(anchor, Content, {}, { class: "via-class" });
    await animationFrame();
    expect(".o_popover.via-class").toHaveCount(1);
});

class FocusableContent extends Component {
    static template = xml`<div class="popover-content"><button class="in">i</button></div>`;
    static props = ["*"];
}

test("a <Popover> written in a template claims the UI like a sheet does", async () => {
    await makeMockEnv();
    class DirectHost extends Component {
        static template = xml`<Popover target="t" close="() => {}" component="c"/>`;
        static components = { Popover };
        static props = ["*"];
        setup() {
            this.t = document.body;
            this.c = FocusableContent;
        }
    }
    await mountWithCleanup(DirectHost);
    await animationFrame();
    await animationFrame();
    expect(getService("ui").activeElement).not.toBe(document);
});

test("Dropdown can still opt out of claiming the UI", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);
    class Host extends Component {
        static template = xml`<div class="anchor">a</div>`;
        static props = ["*"];
    }
    await mountWithCleanup(Host);
    const anchor = queryOne(".anchor");

    const close = getService("popover").add(anchor, FocusableContent, {}, {});
    await animationFrame();
    await animationFrame();
    expect(getService("ui").activeElement).not.toBe(document);
    close();
    await animationFrame();

    getService("popover").add(
        anchor,
        FocusableContent,
        {},
        {
            setActiveElement: false,
        },
    );
    await animationFrame();
    await animationFrame();
    expect(getService("ui").activeElement).toBe(document);
});

test("the popover hook hands back an awaitable close", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);
    /** @type {string[]} */
    const order = [];
    let release = () => {};
    const slow = new Promise((resolve) => {
        release = () => resolve(undefined);
    });
    class Host extends Component {
        static template = xml`<div class="anchor">a</div>`;
        static props = ["*"];
        setup() {
            this.popover = usePopover(Content, {
                onClose: async () => {
                    await slow;
                    order.push("onClose");
                },
            });
        }
    }
    const host = await mountWithCleanup(Host);
    host.popover.open(queryOne(".anchor"), {});
    await animationFrame();

    const closed = host.popover.close().then(() => order.push("awaited"));
    release();
    await closed;
    expect(order).toEqual(["onClose", "awaited"]);
});

test("a target watched before it is attached still reports its removal", async () => {
    const orphan = document.createElement("div");
    let detached = 0;
    const unwatch = watchForDetachedTarget(orphan, () => detached++);

    document.body.appendChild(orphan);
    await animationFrame();
    expect(detached).toBe(0);

    orphan.remove();
    await animationFrame();
    expect(detached).toBe(1);
    unwatch();
});

test("an app that lives only in a shadow root still gets its rootless overlays", async () => {
    const host = document.createElement("div");
    host.setAttribute("id", "o-livechat-root-1");
    host.attachShadow({ mode: "open" });
    getFixture().appendChild(host);

    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer, { target: host.shadowRoot });
    await animationFrame();

    getService("dialog").add(DialogContent, {});
    await animationFrame();

    expect("#o-livechat-root-1:shadow .o_dialog").toHaveCount(1);
    expect(".o_dialog").toHaveCount(0);
    expect(document.body).toHaveClass("modal-open");

    await getService("dialog").closeAll();
    await animationFrame();
    expect(document.body).not.toHaveClass("modal-open");
});

test("a main document container still outranks a shadow one for rootless overlays", async () => {
    const host = document.createElement("div");
    host.setAttribute("id", "o-shadow-root-2");
    host.attachShadow({ mode: "open" });
    getFixture().appendChild(host);

    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);
    await mountWithCleanup(MainComponentsContainer, {
        target: host.shadowRoot,
        noMainContainer: true,
    });
    await animationFrame();

    getService("dialog").add(DialogContent, {});
    await animationFrame();

    expect(".o_dialog").toHaveCount(1);
    expect("#o-shadow-root-2:shadow .o_dialog").toHaveCount(0);

    await getService("dialog").closeAll();
    await animationFrame();
});

test("only the first shadow container adopts, so two of them do not double-render", async () => {
    const hosts = ["o-shadow-a", "o-shadow-b"].map((id) => {
        const host = document.createElement("div");
        host.setAttribute("id", id);
        host.attachShadow({ mode: "open" });
        getFixture().appendChild(host);
        return host;
    });

    await makeMockEnv();
    for (const host of hosts) {
        await mountWithCleanup(MainComponentsContainer, {
            target: host.shadowRoot,
            noMainContainer: true,
        });
    }
    await animationFrame();

    getService("dialog").add(DialogContent, {});
    await animationFrame();

    expect("#o-shadow-a:shadow .o_dialog").toHaveCount(1);
    expect("#o-shadow-b:shadow .o_dialog").toHaveCount(0);

    const removeDuplicate = getService("overlay").registerContainer("o-shadow-a");
    removeDuplicate();
    await animationFrame();
    expect("#o-shadow-a:shadow .o_dialog").toHaveCount(1);
    expect("#o-shadow-b:shadow .o_dialog").toHaveCount(0);

    await getService("dialog").closeAll();
    await animationFrame();
});

test.tags("mobile");
test("opening a dropdown as a bottom sheet says nothing to the console", async () => {
    patchWithCleanup(odoo, { debug: "" });
    /** @type {string[]} */
    const warnings = [];
    patchWithCleanup(console, {
        warn: (/** @type {string} */ message) => warnings.push(message),
    });

    class Parent extends Component {
        static template = xml`
            <Dropdown>
                <button class="opener">open</button>
                <t t-set-slot="content"><span class="item">item</span></t>
            </Dropdown>`;
        static components = { Dropdown };
        static props = ["*"];
    }
    await mountWithCleanup(Parent);
    queryOne(".opener").click();
    await animationFrame();
    await animationFrame();

    expect(".o_bottom_sheet").toHaveCount(1);
    expect(warnings).toEqual([]);
});

test("a popover waiting on a slow onClose stops taking clicks", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    class Body extends Component {
        static template = xml`<button class="pop-btn">go</button>`;
        static props = ["*"];
    }
    /** @type {(v?: any) => void} */
    let release = () => {};
    const slow = new Promise((r) => (release = r));

    const target = document.createElement("div");
    getFixture().appendChild(target);
    const close = getService("popover").add(target, Body, {}, { onClose: () => slow });
    await animationFrame();
    expect(".o_popover").not.toHaveClass("o_popover_closing");

    close();
    await animationFrame();
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover").toHaveClass("o_popover_closing");
    expect(".o_popover").toHaveAttribute("inert");
    expect(getTabableElements(queryOne(".o_popover"))).toHaveLength(0);
    queryOne(".pop-btn").focus();
    expect(queryOne(".pop-btn")).not.toBeFocused();

    release();
    await animationFrame();
    expect(".o_popover").toHaveCount(0);
});

test("a dialog waiting on a slow onClose stops taking clicks too", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    class Body extends Component {
        static template = xml`<Dialog><button class="dlg-btn">go</button></Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }
    /** @type {(v?: any) => void} */
    let release = () => {};
    const slow = new Promise((r) => (release = r));
    const close = getService("dialog").add(Body, {}, { onClose: () => slow });
    await animationFrame();

    close();
    await animationFrame();
    await animationFrame();

    expect(".o_dialog .modal").toHaveAttribute("inert");
    expect(getTabableElements(queryOne(".o_dialog .modal"))).toHaveLength(0);
    queryOne(".dlg-btn").focus();
    expect(queryOne(".dlg-btn")).not.toBeFocused();

    release();
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);
});

test("the portal chatter shape: a second container in the same env, fed by a prop", async () => {
    const host = document.createElement("div");
    host.setAttribute("id", "chatterRoot");
    host.attachShadow({ mode: "open" });
    getFixture().appendChild(host);

    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    const overlays = getService("overlay").overlays;
    class ChatterRoot extends Component {
        static components = { OverlayContainer };
        static props = {};
        static template = xml`<OverlayContainer overlays="overlays" rootId="'chatterRoot'"/>`;
        setup() {
            this.overlays = overlays;
        }
    }
    await mountWithCleanup(ChatterRoot, {
        target: host.shadowRoot,
        noMainContainer: true,
    });
    await animationFrame();

    getService("dialog").add(DialogContent, {}, { rootId: "chatterRoot" });
    getService("dialog").add(DialogContent, {});
    await animationFrame();

    expect("#chatterRoot:shadow .o_dialog").toHaveCount(1);
    expect(".o_dialog").toHaveCount(1);

    await getService("dialog").closeAll();
    await animationFrame();
    document.body.classList.remove("modal-open");
});
