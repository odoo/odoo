/** @odoo-module **/

import { Popover } from "@web/core/popover/popover";
import { registerCleanup } from "../../helpers/cleanup";
import { getFixture, mount } from "../../helpers/utils";

let fixture;
let popoverTarget;

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
    await mount(Popover, fixture, {
        props: { target: popoverTarget, popoverClass: "custom-popover" },
    });

    assert.containsOnce(fixture, ".o_popover.custom-popover");
});

QUnit.test("popover is rendered nearby target (default)", async (assert) => {
    assert.expect(1);
    const TestPopover = class extends Popover {
        onPositioned(el, { direction }) {
            assert.equal(direction, "bottom");
        }
    };
    await mount(TestPopover, fixture, {
        props: { target: popoverTarget },
    });
});

QUnit.test("popover is rendered nearby target (bottom)", async (assert) => {
    const TestPopover = class extends Popover {
        onPositioned(el, { direction }) {
            assert.equal(direction, "bottom");
        }
    };
    await mount(TestPopover, fixture, {
        props: { target: popoverTarget, position: "bottom" },
    });
});

QUnit.test("popover is rendered nearby target (top)", async (assert) => {
    const TestPopover = class extends Popover {
        onPositioned(el, { direction }) {
            assert.equal(direction, "top");
        }
    };
    await mount(TestPopover, fixture, {
        props: { target: popoverTarget, position: "top" },
    });
});

QUnit.test("popover is rendered nearby target (left)", async (assert) => {
    const TestPopover = class extends Popover {
        onPositioned(el, { direction }) {
            assert.equal(direction, "left");
        }
    };
    await mount(TestPopover, fixture, {
        props: { target: popoverTarget, position: "left" },
    });
});

QUnit.test("popover is rendered nearby target (right)", async (assert) => {
    const TestPopover = class extends Popover {
        onPositioned(el, { direction }) {
            assert.equal(direction, "right");
        }
    };
    await mount(TestPopover, fixture, {
        props: { target: popoverTarget, position: "right" },
    });
});
