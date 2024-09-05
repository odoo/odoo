import { expect, getFixture, test } from "@odoo/hoot";
import { queryOne, resize, scroll, waitFor } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Popover } from "@web/core/popover/popover";
import { usePosition } from "@web/core/position/position_hook";

class Content extends Component {
    static props = ["*"];
    static template = xml`<div id="popover">Popover Content</div>`;
}

test("popover can have custom class", async () => {
    await mountWithCleanup(Popover, {
        props: {
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
            target: getFixture(),
            class: "custom-popover popover-custom",
            component: Content,
        },
    });

    expect(".o_popover.custom-popover.popover-custom").toHaveCount(1);
});

test("popover is rendered nearby target (default)", async () => {
    expect.assertions(2);
    class TestPopover extends Popover {
        onPositioned(el, { direction, variant }) {
            expect(direction).toBe("bottom");
            expect(variant).toBe("middle");
        }
    }

    await mountWithCleanup(TestPopover, {
        props: {
            target: getFixture(),
            class: "custom-popover popover-custom",
            component: Content,
        },
    });
});

test("popover is rendered nearby target (bottom)", async () => {
    expect.assertions(2);
    class TestPopover extends Popover {
        onPositioned(el, { direction, variant }) {
            expect(direction).toBe("bottom");
            expect(variant).toBe("middle");
        }
    }

    await mountWithCleanup(TestPopover, {
        props: {
            target: getFixture(),
            position: "bottom",
            component: Content,
        },
    });
});

test("popover is rendered nearby target (top)", async () => {
    expect.assertions(2);
    class TestPopover extends Popover {
        onPositioned(el, { direction, variant }) {
            expect(direction).toBe("top");
            expect(variant).toBe("middle");
        }
    }

    await mountWithCleanup(TestPopover, {
        props: {
            target: getFixture(),
            position: "top",
            component: Content,
        },
    });
});

test("popover is rendered nearby target (left)", async () => {
    expect.assertions(2);
    class TestPopover extends Popover {
        onPositioned(el, { direction, variant }) {
            expect(direction).toBe("left");
            expect(variant).toBe("middle");
        }
    }

    await mountWithCleanup(TestPopover, {
        props: {
            target: getFixture(),
            position: "left",
            component: Content,
        },
    });
});

test("popover is rendered nearby target (right)", async () => {
    expect.assertions(2);
    class TestPopover extends Popover {
        onPositioned(el, { direction, variant }) {
            expect(direction).toBe("right");
            expect(variant).toBe("middle");
        }
    }

    await mountWithCleanup(TestPopover, {
        props: {
            target: getFixture(),
            position: "right",
            component: Content,
        },
    });
});

test("popover is rendered nearby target (bottom-start)", async () => {
    expect.assertions(2);
    class TestPopover extends Popover {
        onPositioned(el, { direction, variant }) {
            expect(direction).toBe("bottom");
            expect(variant).toBe("start");
        }
    }

    await mountWithCleanup(TestPopover, {
        props: {
            target: getFixture(),
            position: "bottom-start",
            component: Content,
        },
    });
});

test("popover is rendered nearby target (bottom-middle)", async () => {
    expect.assertions(2);
    class TestPopover extends Popover {
        onPositioned(el, { direction, variant }) {
            expect(direction).toBe("bottom");
            expect(variant).toBe("middle");
        }
    }

    await mountWithCleanup(TestPopover, {
        props: {
            target: getFixture(),
            position: "bottom-middle",
            component: Content,
        },
    });
});

test("popover is rendered nearby target (bottom-end)", async () => {
    expect.assertions(2);
    class TestPopover extends Popover {
        onPositioned(el, { direction, variant }) {
            expect(direction).toBe("bottom");
            expect(variant).toBe("end");
        }
    }

    await mountWithCleanup(TestPopover, {
        props: {
            target: getFixture(),
            position: "bottom-end",
            component: Content,
        },
    });
});

test("popover is rendered nearby target (bottom-fit)", async () => {
    expect.assertions(2);
    class TestPopover extends Popover {
        onPositioned(el, { direction, variant }) {
            expect(direction).toBe("bottom");
            expect(variant).toBe("fit");
        }
    }

    await mountWithCleanup(TestPopover, {
        props: {
            target: getFixture(),
            position: "bottom-fit",
            component: Content,
        },
    });
});

test("reposition popover should properly change classNames", async () => {
    await resize({ height: 300 });

    class TestPopover extends Popover {
        setup() {
            // Don't call super.setup() in order to replace the use of usePosition hook...
            usePosition("ref", () => this.props.target, {
                container,
                onPositioned: this.onPositioned.bind(this),
                position: this.props.position,
            });
        }
    }

    // Force some style, to make this test independent of screen size
    await mountWithCleanup(/* xml */ `
        <div class="container" style="width: 450px; height: 450px; display: flex; align-items: center; justify-content: center;">
            <div class="popover-target" style="width: 50px; height: 50px;" />
        </div>
    `);

    const container = queryOne(".container");

    await mountWithCleanup(TestPopover, {
        props: {
            target: queryOne(".popover-target"),
            component: Content,
        },
    });

    const popover = queryOne("#popover");
    popover.style.height = "100px";
    popover.style.width = "100px";

    // Should have classes for a "bottom-middle" placement
    expect(".o_popover").toHaveClass(
        "o_popover popover mw-100 o-popover--with-arrow bs-popover-bottom o-popover-bottom o-popover--bm"
    );
    expect(".popover-arrow").toHaveClass("popover-arrow start-0 end-0 mx-auto");

    // Change container style and force update
    container.style.height = "125px"; // height of popper + 1/2 reference
    container.style.alignItems = "flex-end";
    await resize();
    await runAllTimers();
    await animationFrame();

    expect(".o_popover").toHaveClass(
        "o_popover popover mw-100 o-popover--with-arrow bs-popover-end o-popover-right o-popover--re"
    );
    expect(".popover-arrow").toHaveClass("popover-arrow top-auto");
});

test("within iframe", async () => {
    let popoverEl;
    class TestPopover extends Popover {
        onPositioned(el, { direction }) {
            popoverEl = el;
            expect.step(direction);
        }
    }

    await mountWithCleanup(/* xml */ `
        <iframe class="container" style="height: 200px; display: flex" srcdoc="&lt;div id='target' style='height:400px;'&gt;Within iframe&lt;/div&gt;" />
    `);

    await waitFor(":iframe #target");

    const popoverTarget = queryOne(":iframe #target");
    await mountWithCleanup(TestPopover, {
        props: {
            target: popoverTarget,
            component: Content,
            animation: false,
        },
    });

    expect.verifySteps(["bottom"]);
    expect(".o_popover").toHaveCount(1);
    expect(":iframe .o_popover").toHaveCount(0);

    // The popover should be rendered in the correct position
    const marginTop = parseFloat(getComputedStyle(popoverEl).marginTop);
    const { top: targetTop, left: targetLeft } = popoverTarget.getBoundingClientRect();
    const { top: iframeTop, left: iframeLeft } = queryOne("iframe").getBoundingClientRect();
    let popoverBox = popoverEl.getBoundingClientRect();
    let expectedTop = iframeTop + targetTop + popoverTarget.offsetHeight + marginTop;
    const expectedLeft =
        iframeLeft + targetLeft + (popoverTarget.offsetWidth - popoverBox.width) / 2;
    expect(Math.floor(popoverBox.top)).toBe(Math.floor(expectedTop));
    expect(Math.floor(popoverBox.left)).toBe(Math.floor(expectedLeft));

    await scroll(popoverTarget.ownerDocument.documentElement, { y: 100 });
    await animationFrame();
    expect.verifySteps(["bottom"]);
    popoverBox = popoverEl.getBoundingClientRect();
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
            target: wrongElement,
            component: Content,
        },
    });

    expect(".o_popover").toHaveCount(1);
    expect.verifySteps(['validate target props: "true"']);
});

test("popover fixed position", async () => {
    class TestPopover extends Popover {
        onPositioned() {
            expect.step("onPositioned");
        }
    }

    await mountWithCleanup(/* xml */ `
        <div class="container" style="width: 450px; height: 450px; display: flex">
            <div class="popover-target" style="width: 50px; height: 50px;" />
        </div>
    `);

    const container = queryOne(".container");

    await mountWithCleanup(TestPopover, {
        props: {
            target: container,
            position: "bottom-fit",
            fixedPosition: true,
            component: Content,
        },
    });

    expect(".o_popover").toHaveCount(1);
    expect.verifySteps(["onPositioned"]);

    // force the DOM update
    container.style.height = "125px";
    container.style.alignItems = "flex-end";
    await resize();
    await animationFrame();

    expect.verifySteps([]);
});
