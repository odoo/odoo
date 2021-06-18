/** @odoo-module **/

import { Popover } from "@web/core/popover/popover";
import { registerCleanup } from "../../helpers/cleanup";
import { getFixture, patchWithCleanup } from "../../helpers/utils";

const { mount } = owl;

let fixture;
let popoverTarget;

function computePositioningDataTest(popover, target) {
    const rect = target.getBoundingClientRect();
    const top = Math.floor(rect.top);
    const left = Math.floor(rect.left);
    return {
        top: { name: "top", top, left },
        bottom: { name: "bottom", top: top + 10, left },
        left: { name: "left", top: top + 10, left },
        right: { name: "right", top: top + 10, left: left + 10 },
    };
}

function pointsTo(popover, element, position) {
    const hasCorrectClass = popover.classList.contains(`o_popover_${position}`);
    const expectedPosition = Popover.computePositioningData(popover, element)[position];
    const correctLeft = parseFloat(popover.style.left) === expectedPosition.left;
    const correctTop = parseFloat(popover.style.top) === expectedPosition.top;
    return hasCorrectClass && correctLeft && correctTop;
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

        patchWithCleanup(Popover, {
            computePositioningData: computePositioningDataTest,
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
    assert.ok(pointsTo(popoverEl, popoverTarget, "bottom"));
    popover.destroy();
});

QUnit.test("popover is rendered nearby target (bottom)", async (assert) => {
    const popover = await mount(Popover, {
        target: fixture,
        props: { target: popoverTarget, position: "bottom" },
    });

    const popoverEl = fixture.querySelector(".o_popover");
    assert.ok(pointsTo(popoverEl, popoverTarget, "bottom"));
    popover.destroy();
});

QUnit.test("popover is rendered nearby target (top)", async (assert) => {
    const popover = await mount(Popover, {
        target: fixture,
        props: { target: popoverTarget, position: "top" },
    });

    const popoverEl = fixture.querySelector(".o_popover");
    assert.ok(pointsTo(popoverEl, popoverTarget, "top"));
    popover.destroy();
});

QUnit.test("popover is rendered nearby target (left)", async (assert) => {
    const popover = await mount(Popover, {
        target: fixture,
        props: { target: popoverTarget, position: "left" },
    });

    const popoverEl = fixture.querySelector(".o_popover");
    assert.ok(pointsTo(popoverEl, popoverTarget, "left"));
    popover.destroy();
});

QUnit.test("popover is rendered nearby target (right)", async (assert) => {
    const popover = await mount(Popover, {
        target: fixture,
        props: { target: popoverTarget, position: "right" },
    });

    const popoverEl = fixture.querySelector(".o_popover");
    assert.ok(pointsTo(popoverEl, popoverTarget, "right"));
    popover.destroy();
});
