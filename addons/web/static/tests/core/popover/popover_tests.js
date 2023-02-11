/** @odoo-module **/

import { Popover } from "@web/core/popover/popover";
import { registerCleanup } from "../../helpers/cleanup";
import { getFixture } from "../../helpers/utils";

const { mount } = owl;

let fixture;
let popoverTarget;

const positionClassMap = {
    top: "o-popper-position--tm",
    right: "o-popper-position--rm",
    bottom: "o-popper-position--bm",
    left: "o-popper-position--lm",
};

function pointsTo(popover, position) {
    const hasCorrectClass = popover.classList.contains(positionClassMap[position]);
    return hasCorrectClass;
}

QUnit.module("Popover", {
    async beforeEach() {
        fixture = getFixture();

        popoverTarget = document.createElement("div");
        popoverTarget.id = "target";
        fixture.appendChild(popoverTarget);

        registerCleanup(() => {
            fixture.removeChild(popoverTarget);
        });
    },
});

QUnit.test("popover can have custom class", async (assert) => {
    const popover = await mount(Popover, {
        target: fixture,
        props: { target: popoverTarget, popoverClass: "custom-popover" },
    });

    assert.containsOnce(fixture, ".o_popover.custom-popover");
    popover.destroy();
});

QUnit.test("popover is rendered nearby target (default)", async (assert) => {
    const popover = await mount(Popover, {
        target: fixture,
        props: { target: popoverTarget },
    });

    const popoverEl = fixture.querySelector(".o_popover");
    assert.ok(pointsTo(popoverEl, "bottom"));
    popover.destroy();
});

QUnit.test("popover is rendered nearby target (bottom)", async (assert) => {
    const popover = await mount(Popover, {
        target: fixture,
        props: { target: popoverTarget, position: "bottom" },
    });

    const popoverEl = fixture.querySelector(".o_popover");
    assert.ok(pointsTo(popoverEl, "bottom"));
    popover.destroy();
});

QUnit.test("popover is rendered nearby target (top)", async (assert) => {
    const popover = await mount(Popover, {
        target: fixture,
        props: { target: popoverTarget, position: "top" },
    });

    const popoverEl = fixture.querySelector(".o_popover");
    assert.ok(pointsTo(popoverEl, "top"));
    popover.destroy();
});

QUnit.test("popover is rendered nearby target (left)", async (assert) => {
    const popover = await mount(Popover, {
        target: fixture,
        props: { target: popoverTarget, position: "left" },
    });

    const popoverEl = fixture.querySelector(".o_popover");
    assert.ok(pointsTo(popoverEl, "left"));
    popover.destroy();
});

QUnit.test("popover is rendered nearby target (right)", async (assert) => {
    const popover = await mount(Popover, {
        target: fixture,
        props: { target: popoverTarget, position: "right" },
    });

    const popoverEl = fixture.querySelector(".o_popover");
    assert.ok(pointsTo(popoverEl, "right"));
    popover.destroy();
});
