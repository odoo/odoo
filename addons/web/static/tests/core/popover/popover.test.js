import { expect, getFixture, test } from "@odoo/hoot";
import { queryOne, queryRect, resize, scroll, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useRef, useState, xml } from "@odoo/owl";
import {
    contains,
    defineStyle,
    mountWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { Popover } from "@web/core/popover/popover";
import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";

class Content extends Component {
    static props = ["*"];
    static template = xml`<div id="popover">Popover Content</div>`;
}

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
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`
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
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`
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
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`
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
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`
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
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`
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
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`
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
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`
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
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`
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
        `<div id="target" style="background-color: royalblue; width: 50px; height: 50px; position: absolute; top: 50%; left: 50%;"/>`
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
    await mountWithCleanup(/* xml */ `
        <iframe class="container" style="height: 200px; display: flex" srcdoc="&lt;div id='target' style='height:400px;'&gt;Within iframe&lt;/div&gt;" />
    `);

    await waitFor(":iframe #target");

    const popoverTarget = queryOne(":iframe #target");
    const comp = await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: popoverTarget,
            component: Content,
            animation: false,
            onPositioned: (_, { direction }) => {
                expect.step(direction);
            },
        },
    });

    expect.verifySteps(["bottom"]);
    expect(".o_popover").toHaveCount(1);
    expect(":iframe .o_popover").toHaveCount(0);

    // The popover should be rendered in the correct position
    const marginTop = queryRect(".popover-arrow").height;
    const { top: targetTop, left: targetLeft } = popoverTarget.getBoundingClientRect();
    const { top: iframeTop, left: iframeLeft } = queryOne("iframe").getBoundingClientRect();
    let popoverBox = comp.popoverRef.el.getBoundingClientRect();
    let expectedTop = iframeTop + targetTop + popoverTarget.offsetHeight + marginTop;
    const expectedLeft =
        iframeLeft + targetLeft + (popoverTarget.offsetWidth - popoverBox.width) / 2;
    expect(Math.floor(popoverBox.top)).toBe(Math.floor(expectedTop));
    expect(Math.floor(popoverBox.left)).toBe(Math.floor(expectedLeft));

    await scroll(popoverTarget.ownerDocument.documentElement, { y: 100 }, { scrollable: false });
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
                validate: (...args) => {
                    const val = Popover.props.target.validate(...args);
                    expect.step(`validate target props: "${val}"`);
                    return val;
                },
            },
        };
    }

    await mountWithCleanup(/* xml */ `
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
    await mountWithCleanup(/* xml */ `
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

    // force the DOM update
    container.style.alignItems = "flex-end";
    await resize({ height: 125 });
    await animationFrame();

    expect.verifySteps([]);
});

test("popover with arrow and onPositioned", async () => {
    class TestPopover extends Popover {
        onPositioned() {
            expect.step("onPositioned (from override)");
            super.onPositioned(...arguments);
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
    history.pushState({}, "", "/"); // Need non-null state
    history.pushState(null, "", "/aaa"); // Head to other page

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

    history.back(); // Head back
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
        <span t-if="state.showMore">
            This tooltip gives your more information on this topic!
        </span>
    </div>`;
    }

    await mountWithCleanup(Popover, {
        props: {
            close: () => {},
            target: getFixture(),
            position: "top-fit",
            component: DynamicContent,
            onPositioned() {
                expect.step("onPositioned");
            },
        },
    });

    expect(".o_popover").toHaveCount(1);
    expect.verifySteps(["onPositioned"]);
    await contains("#popover button").click();
    expect("#popover span").toHaveCount(1);
    await waitForSteps(["onPositioned"]);
});

test("arrow follows target and can get sucked", async () => {
    let container;
    patch(Popover, { animationTime: 0 });
    patch(Popover.prototype, {
        get positioningOptions() {
            return {
                ...super.positioningOptions,
                container: () => container.el,
            };
        },
    });
    defineStyle(/* css */ `
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
                <div class="popover-target" t-ref="popover-target" t-on-click="openPopover"/>
            </div>
        `;
        setup() {
            container = useRef("popover-container");
            this.target = useRef("popover-target");
            this.popover = usePopover(Content, { popoverClass: "my-popover" });
        }
    }
    const parent = await mountWithCleanup(Parent);
    async function openPopover() {
        parent.popover.open(parent.target.el);
        return animationFrame();
    }
    await openPopover();

    // Initial position of arrow should be at the middle of the target
    let arrowRect = queryRect(".popover-arrow");
    let targetRect = queryRect(".popover-target");
    const initial = {
        top: targetRect.bottom,
        left: targetRect.left + targetRect.width / 2 - arrowRect.width / 2,
    };
    expect(".popover-arrow").toHaveRect(initial);
    expect(".popover-arrow").not.toHaveClass("sucked");

    // Move the target to the left of the container, arrow should still be at the middle
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

    // Move the target further to the left, arrow should get sucked
    parent.target.el.style.marginLeft = "-100px";
    await openPopover();
    arrowRect = queryRect(".popover-arrow");
    const popoverRect = queryRect(".my-popover");
    expect(arrowRect.top).toBeWithin(popoverRect.top, popoverRect.bottom - arrowRect.height);
    expect(arrowRect.left).toBeWithin(popoverRect.left, popoverRect.right - arrowRect.width);
    expect(".popover-arrow").toHaveClass("sucked");
    expect(".popover-arrow").not.toBeVisible();
});
