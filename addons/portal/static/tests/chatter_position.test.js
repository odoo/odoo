import { Chatter } from "@mail/chatter/web_portal/chatter";
import { expect, getFixture, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";

async function preparePosition() {
    getFixture().innerHTML =
        '<div id="wrapwrap"><header id="test-header"></header></div>';
    const intersections = [];
    const resizes = [];
    function observerClass(instances) {
        return class {
            constructor(callback) {
                this.callback = callback;
                instances.push(this);
            }
            observe(element) {
                this.element = element;
            }
            unobserve() {}
            disconnect() {
                this.disconnected = true;
            }
        };
    }
    patchWithCleanup(window, {
        IntersectionObserver: observerClass(intersections),
        ResizeObserver: observerClass(resizes),
    });
    const dimensions = { height: 60, top: -1 };
    patchWithCleanup(HTMLElement.prototype, {
        getBoundingClientRect() {
            if (this.id === "test-header") {
                return { height: dimensions.height };
            }
            if (this.classList.contains("test-top")) {
                return { y: dimensions.top, top: dimensions.top };
            }
            return super.getBoundingClientRect(...arguments);
        },
    });
    patchWithCleanup(Chatter, {
        template: xml`<div t-ref="root"><div class="test-top" t-ref="top" style="padding-top: 20px"/></div>`,
    });
    // Keep the real component setup/effect; omit unrelated thread loading/rendering.
    patchWithCleanup(Chatter.prototype, { _onMounted() {}, load() {} });
    class Parent extends Component {
        static props = {};
        static components = { Chatter };
        static template = xml`<Chatter threadModel="'res.partner'" twoColumns="state.twoColumns"/>`;
        setup() {
            this.state = useState({ twoColumns: false });
        }
    }
    const parent = await mountWithCleanup(Parent);
    const top = queryOne(".test-top");
    const intersection = intersections.find((observer) => observer.element === top);
    intersection.callback([{ target: top }]);
    return { parent, top, dimensions, intersection, resizes };
}

test("sticky chatter responds to header resizing without another scroll", async () => {
    const { top, dimensions, resizes } = await preparePosition();
    expect(top.style.paddingTop).toBe("75px");
    dimensions.height = 120;
    resizes.find((observer) => observer.element?.id === "test-header")?.callback([]);
    expect(top.style.paddingTop).toBe("135px");
});

test("switching to two columns disconnects observers and restores padding", async () => {
    const { parent, top, intersection, resizes } = await preparePosition();
    parent.state.twoColumns = true;
    await animationFrame();
    expect(top.style.paddingTop).toBe("20px");
    expect(intersection.disconnected).toBe(true);
    const resize = resizes.find((observer) => observer.element?.id === "test-header");
    expect(resize?.disconnected).toBe(true);
});

test("scrolling away from the sticky edge restores ordinary spacing", async () => {
    const { top, dimensions, intersection } = await preparePosition();
    dimensions.top = 50;
    intersection.callback([{ target: top }]);
    expect(top.style.paddingTop).toBe("20px");
});

test("cleanup preserves a matching padding value whose priority another owner changed", async () => {
    const { parent, top } = await preparePosition();
    top.style.setProperty("padding-top", "75px", "important");
    parent.state.twoColumns = true;
    await animationFrame();
    expect(top.style.paddingTop).toBe("75px");
    expect(top.style.getPropertyPriority("padding-top")).toBe("important");
});
