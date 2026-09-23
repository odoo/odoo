// @ts-check

import { beforeEach, expect, getFixture, test } from "@odoo/hoot";
import {
    click,
    press,
    queryOne,
    queryRect,
    resize,
    scroll,
    waitFor,
} from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, useRef, useState, xml } from "@odoo/owl";
import {
    contains,
    defineStyle,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";
import { Dialog } from "@web/ui/dialog";
import { MainComponentsContainer } from "@web/ui/main_components_container";
import { Popover } from "@web/ui/popover/popover";
import { usePopover } from "@web/ui/popover/popover_hook";

class Content extends Component {
    static props = ["*"];
    static template = xml`<div id="popover">Popover Content</div>`;
}

beforeEach(() => {
    patchWithCleanup(Popover.defaultProps, {
        animation: false,
        arrow: false,
    });
});

test("popover can have custom class", async () => {
    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: getFixture(),
            class: "custom-popover",
            component: Content,
        },
    });

    expect(".o_popover.custom-popover").toHaveCount(1);
});

test("popover can have more than one custom class", async () => {
    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: getFixture(),
            class: "custom-popover popover-custom",
            component: Content,
        },
    });

    expect(".o_popover.custom-popover.popover-custom").toHaveCount(1);
});

test("popover is rendered nearby target (default)", async () => {
    expect.assertions(2);
    await mountWithCleanup(
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`,
    );
    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: queryOne("#target"),
            component: Content,
            onPositioned: (_, { direction, variant }) => {
                expect(direction).toBe("bottom");
                expect(variant).toBe("middle");
            },
        },
        noMainContainer: true,
    });
});

test("popover is rendered nearby target (bottom)", async () => {
    expect.assertions(2);
    await mountWithCleanup(
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`,
    );

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: queryOne("#target"),
            position: "bottom",
            component: Content,
            onPositioned: (_, { direction, variant }) => {
                expect(direction).toBe("bottom");
                expect(variant).toBe("middle");
            },
        },
        noMainContainer: true,
    });
});

test("popover is rendered nearby target (top)", async () => {
    expect.assertions(2);
    await mountWithCleanup(
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`,
    );

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: queryOne("#target"),
            position: "top",
            component: Content,
            onPositioned: (_, { direction, variant }) => {
                expect(direction).toBe("top");
                expect(variant).toBe("middle");
            },
        },
        noMainContainer: true,
    });
});

test("popover is rendered nearby target (left)", async () => {
    expect.assertions(2);
    await mountWithCleanup(
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`,
    );

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: queryOne("#target"),
            position: "left",
            component: Content,
            onPositioned: (_, { direction, variant }) => {
                expect(direction).toBe("left");
                expect(variant).toBe("middle");
            },
        },
        noMainContainer: true,
    });
});

test("popover is rendered nearby target (right)", async () => {
    expect.assertions(2);
    await mountWithCleanup(
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`,
    );

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: queryOne("#target"),
            position: "right",
            component: Content,
            onPositioned: (_, { direction, variant }) => {
                expect(direction).toBe("right");
                expect(variant).toBe("middle");
            },
        },
        noMainContainer: true,
    });
});

test("popover is rendered nearby target (bottom-start)", async () => {
    expect.assertions(2);
    await mountWithCleanup(
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`,
    );

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: queryOne("#target"),
            position: "bottom-start",
            component: Content,
            onPositioned: (_, { direction, variant }) => {
                expect(direction).toBe("bottom");
                expect(variant).toBe("start");
            },
        },
        noMainContainer: true,
    });
});

test("popover is rendered nearby target (bottom-middle)", async () => {
    expect.assertions(2);
    await mountWithCleanup(
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`,
    );

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: queryOne("#target"),
            position: "bottom-middle",
            component: Content,
            onPositioned: (_, { direction, variant }) => {
                expect(direction).toBe("bottom");
                expect(variant).toBe("middle");
            },
        },
        noMainContainer: true,
    });
});

test("popover is rendered nearby target (bottom-end)", async () => {
    expect.assertions(2);
    await mountWithCleanup(
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`,
    );

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: queryOne("#target"),
            position: "bottom-end",
            component: Content,
            onPositioned: (_, { direction, variant }) => {
                expect(direction).toBe("bottom");
                expect(variant).toBe("end");
            },
        },
        noMainContainer: true,
    });
});

test("popover is rendered nearby target (bottom-fit)", async () => {
    expect.assertions(2);
    await mountWithCleanup(
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`,
    );

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: queryOne("#target"),
            position: "bottom-fit",
            component: Content,
            onPositioned: (_, { direction, variant }) => {
                expect(direction).toBe("bottom");
                expect(variant).toBe("fit");
            },
        },
        noMainContainer: true,
    });
});

test("within iframe", async () => {
    await mountWithCleanup(`
        <iframe class="container" style="height: 200px; display: flex" srcdoc="&lt;div id='target' style='height:400px;'&gt;Within iframe&lt;/div&gt;" />
    `);

    await waitFor(":iframe #target");

    const popoverTarget = queryOne(":iframe #target");
    const comp = await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: popoverTarget,
            component: Content,
            arrow: true,
            onPositioned: (_, { direction }) => {
                expect.step(direction);
            },
        },
    });

    expect.verifySteps(["bottom"]);
    expect(".o_popover").toHaveCount(1);
    expect(":iframe .o_popover").toHaveCount(0);

    const marginTop = queryRect(".popover-arrow").height;
    const { top: targetTop, left: targetLeft } = popoverTarget.getBoundingClientRect();
    const { top: iframeTop, left: iframeLeft } =
        queryOne("iframe").getBoundingClientRect();
    let popoverBox = comp.popoverRef.el.getBoundingClientRect();
    let expectedTop = iframeTop + targetTop + popoverTarget.offsetHeight + marginTop;
    const expectedLeft =
        iframeLeft + targetLeft + (popoverTarget.offsetWidth - popoverBox.width) / 2;
    expect(Math.floor(popoverBox.top)).toBe(Math.floor(expectedTop));
    expect(Math.floor(popoverBox.left)).toBe(Math.floor(expectedLeft));

    await scroll(
        popoverTarget.ownerDocument.documentElement,
        { y: 100 },
        { scrollable: false },
    );
    await animationFrame();
    expect.verifySteps(["bottom"]);
    popoverBox = comp.popoverRef.el.getBoundingClientRect();
    expectedTop -= 100;
    expect(Math.floor(popoverBox.top)).toBe(Math.floor(expectedTop));
    expect(Math.floor(popoverBox.left)).toBe(Math.floor(expectedLeft));
});

test("within iframe -- wrong element class", async () => {
    class TestPopover extends Popover {
        static props = {
            ...Popover.props,
            target: {
                validate: (target) => {
                    const val = Popover.props.target.validate(target);
                    expect.step(`validate target props: "${val}"`);
                    return val;
                },
            },
        };
    }

    await mountWithCleanup(`
        <iframe class="container" style="height: 200px; display: flex" srcdoc="&lt;div id='target' style='height:400px;'&gt;Within iframe&lt;/div&gt;" />
    `);

    await waitFor(":iframe #target");

    const wrongElement = document.createElement("div");
    wrongElement.classList.add("wrong-element");
    queryOne(":iframe body").appendChild(wrongElement);

    await mountWithCleanup(TestPopover, {
        props: {
            close: () => {},
            target: wrongElement,
            component: Content,
        },
    });

    expect(".o_popover").toHaveCount(1);
    expect.verifySteps(['validate target props: "true"']);
});

test("popover fixed position", async () => {
    await resize({ width: 450, height: 450 });
    await mountWithCleanup(`
        <div class="container w-100 h-100" style="display: flex">
            <div class="popover-target" style="width: 50px; height: 50px;" />
        </div>
    `);

    const container = queryOne(".container");

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: container,
            position: "bottom-fit",
            fixedPosition: true,
            component: Content,
            onPositioned() {
                expect.step("onPositioned");
            },
        },
    });

    expect(".o_popover").toHaveCount(1);
    expect.verifySteps(["onPositioned"]);

    container.style.alignItems = "flex-end";
    await resize({ height: 125 });
    await animationFrame();

    expect.verifySteps([]);
});

test("popover with arrow and onPositioned", async () => {
    class TestPopover extends Popover {
        onPositioned(solution) {
            expect.step("onPositioned (from override)");
            super.onPositioned(solution);
        }
    }

    await mountWithCleanup(TestPopover, {
        props: {
            close: () => {},
            target: getFixture(),
            component: Content,
            arrow: true,
            onPositioned() {
                expect.step("onPositioned (from props)");
            },
        },
    });

    expect.verifySteps(["onPositioned (from override)", "onPositioned (from props)"]);
    expect(".o_popover").toHaveClass("o_popover popover mw-100 bs-popover-auto");
    expect(".o_popover").toHaveAttribute("data-popper-placement", "bottom");
    expect(".o_popover > .popover-arrow").toHaveClass("position-absolute z-n1");
});

test("popover closes when navigating", async () => {
    history.pushState({}, "", "/");
    history.pushState(null, "", "/aaa");

    await mountWithCleanup(Popover, {
        props: {
            close: () => expect.step("close"),
            closeOnClickAway: (target) => {
                expect.step(target.tagName);
                return true;
            },
            target: getFixture(),
            component: Content,
        },
    });

    expect(".o_popover").toHaveCount(1);

    history.back();
    await animationFrame();

    expect.verifySteps(["HTML", "close"]);
});

test("popover position is updated when the content dimensions change", async () => {
    class DynamicContent extends Component {
        setup() {
            this.state = useState({
                showMore: false,
            });
        }
        static props = ["*"];
        static template = xml`<div id="popover">
        Click on this <button t-on-click="() => this.state.showMore = true">button</button> to read more
        <span t-if="this.state.showMore">
            This tooltip gives your more information on this topic!
        </span>
    </div>`;
    }

    await mountWithCleanup(`
        <div class="popover-target" style="width: 50px; height: 50px;" />
    `);

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: queryOne(".popover-target"),
            position: "bottom-start",
            component: DynamicContent,
            onPositioned() {
                expect.step("onPositioned");
            },
        },
    });

    expect(".o_popover").toHaveCount(1);
    await runAllTimers();
    await expect.waitForSteps(["onPositioned"]);
    await contains("#popover button").click();
    expect("#popover span").toHaveCount(1);
    await expect.waitForSteps(["onPositioned"]);
});

test("arrow follows target and can get sucked", async () => {
    /** @type {import("@odoo/owl").Ref<HTMLElement>} */
    let container;
    patchWithCleanup(Popover.defaultProps, { arrow: true });
    patchWithCleanup(Popover.prototype, {
        get positioningOptions() {
            return {
                ...super.positioningOptions,
                container: () => container.el,
            };
        },
    });
    defineStyle(`
        .my-popover {
            height: 100px;
            width: 100px;
        }
        .popover-container {
            background-color: beige;
            display: flex;
            width: 200px;
            height: 200px;
            justify-content: center;
            align-items: flex-start;
        }
        .popover-target {
            background-color: bisque;
            width: 50px;
            height: 50px;
        }
    `);
    class Parent extends Component {
        static props = ["*"];
        static template = xml`
            <div class="popover-container" t-ref="popover-container">
                <div class="popover-target" t-ref="popover-target" t-on-click="this.openPopover"/>
            </div>
        `;
        setup() {
            container = useRef("popover-container");
            this.target = useRef("popover-target");
            this.popover = usePopover(Content, { class: "my-popover" });
        }
    }
    const parent = await mountWithCleanup(Parent);
    async function openPopover() {
        parent.popover.open(parent.target.el);
        return animationFrame();
    }
    await openPopover();

    let arrowRect = queryRect(".popover-arrow");
    let targetRect = queryRect(".popover-target");
    const initial = {
        top: targetRect.bottom,
        left: targetRect.left + targetRect.width / 2 - arrowRect.width / 2,
    };
    expect(".popover-arrow").toHaveRect(initial);
    expect(".popover-arrow").not.toHaveClass("sucked");

    container.el.style.justifyContent = "flex-start";
    await openPopover();
    arrowRect = queryRect(".popover-arrow");
    targetRect = queryRect(".popover-target");
    const newPosition = {
        top: targetRect.bottom,
        left: targetRect.left + targetRect.width / 2 - arrowRect.width / 2,
    };
    expect(newPosition).not.toBe(initial);
    expect(".popover-arrow").toHaveRect(newPosition);
    expect(".popover-arrow").not.toHaveClass("sucked");

    parent.target.el.style.marginLeft = "-100px";
    await openPopover();
    arrowRect = queryRect(".popover-arrow");
    const popoverRect = queryRect(".my-popover");
    expect(arrowRect.top).toBeWithin(
        popoverRect.top,
        popoverRect.bottom - arrowRect.height,
    );
    expect(arrowRect.left).toBeWithin(
        popoverRect.left,
        popoverRect.right - arrowRect.width,
    );
    expect(".popover-arrow").toHaveClass("sucked");
    expect(".popover-arrow").not.toBeVisible();
});

test("popover can animate", async () => {
    patchWithCleanup(window.Element.prototype, {
        animate() {
            expect(this).toHaveClass("o_popover");
            expect.step("animated");
            return super.animate(...arguments);
        },
    });

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: getFixture(),
            animation: true,
            component: Content,
        },
    });

    expect(".o_popover").toHaveCount(1);

    await animationFrame();
    await runAllTimers();

    expect.verifySteps(["animated"]);
});

test("holdOnHover does not release a fixedPosition popover", async () => {
    const popover = await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: getFixture(),
            component: Content,
            fixedPosition: true,
            holdOnHover: true,
        },
    });
    await animationFrame();

    let unlocks = 0;
    patchWithCleanup(popover.position, { unlock: () => (unlocks += 1) });
    const el = queryOne(".o_popover");
    el.dispatchEvent(new PointerEvent("pointerenter"));
    el.dispatchEvent(new PointerEvent("pointerleave"));
    expect(unlocks).toBe(0);
});

test("holdOnHover still releases a normally positioned popover", async () => {
    const popover = await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: getFixture(),
            component: Content,
            holdOnHover: true,
        },
    });
    await animationFrame();

    let unlocks = 0;
    patchWithCleanup(popover.position, { unlock: () => (unlocks += 1) });
    const el = queryOne(".o_popover");
    el.dispatchEvent(new PointerEvent("pointerenter"));
    expect(unlocks).toBe(0);
    el.dispatchEvent(new PointerEvent("pointerleave"));
    expect(unlocks).toBe(1);
});

test("closeOnClickAway is not consulted for clicks inside the popover", async () => {
    const asked = [];
    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: getFixture(),
            component: Content,
            closeOnClickAway: (t) => (asked.push(t), true),
        },
    });
    await animationFrame();

    await click("#popover");
    await animationFrame();
    expect(asked).toEqual([]);
    expect("#popover").toHaveCount(1);
});

test("holdOnHover survives a resize of the popover content", async () => {
    const popover = await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: getFixture(),
            component: Content,
            holdOnHover: true,
        },
    });
    await animationFrame();

    let unlocks = 0;
    patchWithCleanup(popover.position, { unlock: () => (unlocks += 1) });
    const el = queryOne(".o_popover");

    popover.onResized();
    expect(unlocks).toBe(1, { message: "a resize repositions an unheld popover" });

    el.dispatchEvent(new PointerEvent("pointerenter"));
    popover.onResized();
    popover.onResized();
    expect(unlocks).toBe(1, { message: "…but never while the pointer holds it" });

    el.dispatchEvent(new PointerEvent("pointerleave"));
    expect(unlocks).toBe(2);
});

test("holdOnHover survives the opening animation finishing", async () => {
    const animationDone = new Deferred();
    patchWithCleanup(Popover.prototype, {
        animate: () => ({ finished: animationDone }),
    });
    const popover = await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: getFixture(),
            component: Content,
            animation: true,
            holdOnHover: true,
        },
    });
    await animationFrame();

    let unlocks = 0;
    patchWithCleanup(popover.position, { unlock: () => (unlocks += 1) });
    queryOne(".o_popover").dispatchEvent(new PointerEvent("pointerenter"));

    animationDone.resolve();
    await animationDone;
    await animationFrame();
    expect(unlocks).toBe(0, { message: "hover outlives the opening animation" });

    queryOne(".o_popover").dispatchEvent(new PointerEvent("pointerleave"));
    expect(unlocks).toBe(1);
});

test("opening positions once; only a later resize of the content repositions", async () => {
    /** @type {() => void} */
    let grow;
    class GrowingContent extends Component {
        static props = ["*"];
        static template = xml`<div id="popover" t-att-style="'height: ' + this.state.height + 'px'">Popover Content</div>`;
        setup() {
            this.state = useState({ height: 30 });
            grow = () => (this.state.height = 300);
        }
    }
    await mountWithCleanup(
        `<div class="popover-target" style="width: 50px; height: 50px;" />`,
    );
    let positioned = 0;
    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: queryOne(".popover-target"),
            component: GrowingContent,
            onPositioned: () => positioned++,
        },
    });
    await animationFrame();
    await animationFrame();
    expect(positioned).toBe(1, {
        message: "the observer's first delivery is the mount size, not a resize",
    });

    // a change the popover itself never renders for: only the observer sees it
    grow();
    await animationFrame();
    await animationFrame();
    expect(positioned).toBe(2);
});

test("an unanimated, unheld popover is never locked", async () => {
    const popover = await mountWithCleanup(Popover, {
        props: { close: () => {}, target: getFixture(), component: Content },
    });
    await animationFrame();
    expect(popover.isPositionFrozen).toBe(false);
    expect(popover.positionLocked).toBe(false);
});

test("the cached position lock tracks isPositionFrozen through a prop change", async () => {
    const popover = await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: getFixture(),
            component: Content,
            holdOnHover: true,
            fixedPosition: true,
        },
    });
    await animationFrame();
    expect(popover.positionLocked).toBe(true);

    popover.props.fixedPosition = false;
    popover.onResized();
    expect(popover.isPositionFrozen).toBe(false);
    expect(popover.positionLocked).toBe(false);

    const locks = [];
    patchWithCleanup(popover.position, {
        lock: () => locks.push("lock"),
        unlock: () => locks.push("unlock"),
    });
    popover.onPointerEnter();
    expect(locks).toEqual(["lock"]);
    expect(popover.positionLocked).toBe(true);

    popover.onPointerLeave();
    expect(locks).toEqual(["lock", "unlock"]);
    expect(popover.positionLocked).toBe(false);
});

test("a popover whose target is not in the document does not build its content", async () => {
    class Probe extends Component {
        static template = xml`<div class="p-content"/>`;
        static props = ["*"];
        setup() {
            expect.step("content setup");
        }
    }
    await mountWithCleanup(MainComponentsContainer);
    getService("popover").add(document.createElement("div"), Probe, {});
    await animationFrame();
    await animationFrame();

    expect.verifySteps([]);
    expect(".p-content").toHaveCount(0);
    expect(".o_popover").toHaveCount(0);
    expect(Object.keys(getService("overlay").overlays)).toHaveLength(0);
});

test("escape closes the popover, not the dialog it was opened from", async () => {
    class InertContent extends Component {
        static template = xml`<div class="inert-pop">plain text</div>`;
        static props = ["*"];
    }
    class Host extends Component {
        static template = xml`<Dialog><div class="host"><input class="dlg-input"/><span class="anchor">?</span></div></Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }

    await mountWithCleanup(MainComponentsContainer);
    getService("dialog").add(Host, {});
    await animationFrame();

    getService("popover").add(queryOne(".anchor"), InertContent);
    await animationFrame();
    expect(".o_popover").toHaveCount(1);
    expect(".o_dialog").toHaveCount(1);

    await press("escape");
    await animationFrame();
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_dialog").toHaveCount(1);
});

test("a popover anchored outside a dialog is not left orphaned by escape", async () => {
    class InertContent extends Component {
        static template = xml`<div class="inert-pop">plain text</div>`;
        static props = ["*"];
    }
    class Host extends Component {
        static template = xml`<Dialog><div class="host"><input class="dlg-input"/></div></Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }

    await mountWithCleanup(MainComponentsContainer);
    getService("dialog").add(Host, {});
    await animationFrame();

    const anchor = document.createElement("span");
    getFixture().appendChild(anchor);
    getService("popover").add(anchor, InertContent);
    await animationFrame();

    await press("escape");
    await animationFrame();
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_dialog").toHaveCount(1);
});

test("a popover with nothing to focus claims the UI without taking the focus", async () => {
    class InertContent extends Component {
        static template = xml`<div class="inert-pop">plain text</div>`;
        static props = ["*"];
    }

    await mountWithCleanup(MainComponentsContainer);
    const input = document.createElement("input");
    getFixture().appendChild(input);
    input.focus();

    getService("popover").add(input, InertContent);
    await animationFrame();

    expect(getService("ui").activeElement).toBe(queryOne(".o_popover"));
    expect(input).toBeFocused();
});
