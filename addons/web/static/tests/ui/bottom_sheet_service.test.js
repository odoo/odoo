// @ts-check

import { afterEach, expect, getFixture, test } from "@odoo/hoot";
import { click, press } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    getMockEnv,
    getService,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { MainComponentsContainer } from "@web/ui/main_components_container";

class DropdownParent extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["*"];
    static template = xml`
        <Dropdown>
            <button class="toggler">Open</button>
            <t t-set-slot="content">
                <DropdownItem class="'ditem'">Item</DropdownItem>
            </t>
        </Dropdown>`;
}

afterEach(() => {
    document.body.classList.remove("bottom-sheet-open", "bottom-sheet-open-multiple");
});

test("bottom sheet body classes count sheets from all service instances", async () => {
    await mountWithCleanup(MainComponentsContainer);
    class Content extends Component {
        static template = xml`<div>content</div>`;
        static props = ["*"];
    }
    const first = getService("bottom_sheet");
    const second = registry
        .category("services")
        .get("bottom_sheet")
        .start(getMockEnv(), { overlay: getService("overlay") });
    try {
        const closeFirst = first.add(getFixture(), Content);
        const closeSecond = second.add(getFixture(), Content);
        expect(document.body).toHaveClass("bottom-sheet-open-multiple");
        await closeFirst();
        expect(document.body).toHaveClass("bottom-sheet-open");
        expect(document.body).not.toHaveClass("bottom-sheet-open-multiple");
        first.destroy();
        expect(document.body).toHaveClass("bottom-sheet-open");
        await closeSecond();
        expect(document.body).not.toHaveClass("bottom-sheet-open");
    } finally {
        second.destroy();
    }
});

test("closing a bottom sheet decrements the count and clears the body class", async () => {
    await mountWithCleanup(MainComponentsContainer);

    class MyComp extends Component {
        static template = xml`<div class="sheet-content"/>`;
        static props = ["*"];
    }

    const close = getService("bottom_sheet").add(getFixture(), MyComp);
    await animationFrame();
    expect(document.body).toHaveClass("bottom-sheet-open");

    close();
    await animationFrame();
    expect(document.body).not.toHaveClass("bottom-sheet-open");

    close();
    await animationFrame();
    expect(document.body).not.toHaveClass("bottom-sheet-open");
});

test("a throwing onClose still decrements the count and clears the body class", async () => {
    expect.errors(1);
    await mountWithCleanup(MainComponentsContainer);

    class MyComp extends Component {
        static template = xml`<div class="sheet-content"/>`;
        static props = ["*"];
    }

    const close = getService("bottom_sheet").add(
        getFixture(),
        MyComp,
        {},
        {
            onClose: () => {
                throw new Error("onClose boom");
            },
        },
    );
    await animationFrame();
    expect(document.body).toHaveClass("bottom-sheet-open");

    close();
    await animationFrame();
    expect(document.body).not.toHaveClass("bottom-sheet-open");
    expect.verifyErrors(["Error: onClose boom"]);
});

test("a crashing bottom sheet subtree still decrements the count and clears the body class", async () => {
    expect.errors(1);
    await mountWithCleanup(MainComponentsContainer);

    class Boom extends Component {
        static template = xml``;
        static props = ["*"];
        setup() {
            throw new Error("bottom sheet crashed");
        }
    }

    getService("bottom_sheet").add(getFixture(), Boom);
    await animationFrame();

    expect(document.body).not.toHaveClass("bottom-sheet-open");
    expect.verifyErrors(["Error: bottom sheet crashed"]);
});

test.tags("mobile");
test("a sheet honours closeOnEscape, like the popover does", async () => {
    await mountWithCleanup(MainComponentsContainer);

    class MyComp extends Component {
        static template = xml`<div class="sheet-content"/>`;
        static props = ["*"];
    }

    getService("bottom_sheet").add(getFixture(), MyComp, {}, { closeOnEscape: false });
    await animationFrame();
    await animationFrame();
    expect(".sheet-content").toHaveCount(1);

    await press("escape");
    await runAllTimers();
    await animationFrame();
    expect(".sheet-content").toHaveCount(1);
});

test.tags("mobile");
test("a sheet closes on escape by default", async () => {
    await mountWithCleanup(MainComponentsContainer);

    class MyComp extends Component {
        static template = xml`<div class="sheet-content"/>`;
        static props = ["*"];
    }

    getService("bottom_sheet").add(getFixture(), MyComp);
    await animationFrame();
    await animationFrame();
    expect(".sheet-content").toHaveCount(1);

    await press("escape");
    await runAllTimers();
    await animationFrame();
    expect(".sheet-content").toHaveCount(0);
});

test.tags("mobile");
test("escape closes a dropdown menu rendered as a bottom sheet", async () => {
    await mountWithCleanup(DropdownParent);
    await click(".toggler");
    await runAllTimers();
    await animationFrame();
    expect(".o_bottom_sheet").toHaveCount(1);
    expect(".ditem").toHaveCount(1);

    await press("escape");
    await runAllTimers();
    await animationFrame();
    expect(".ditem").toHaveCount(0);
});

test.tags("mobile");
test("a sheet renders the `id` option, like the popover does", async () => {
    await mountWithCleanup(MainComponentsContainer);

    class MyComp extends Component {
        static template = xml`<div class="sheet-content"/>`;
        static props = ["*"];
    }

    getService("bottom_sheet").add(getFixture(), MyComp, {}, { id: "o-sheet-id" });
    await animationFrame();
    await animationFrame();

    const owner = document.getElementById("o-sheet-id");
    expect(owner).not.toBe(null);
    expect(owner.querySelector(".sheet-content")).not.toBe(null);
});

test.tags("mobile");
test("a dropdown's menuId survives being rendered as a bottom sheet", async () => {
    await mountWithCleanup(DropdownParent);
    await click(".toggler");
    await runAllTimers();
    await animationFrame();

    const menu = /** @type {HTMLElement} */ (
        document.querySelector(".o-dropdown--menu")
    );
    expect(menu.id).not.toBe("");
    expect(document.getElementById(menu.id)).toBe(menu);
});

test.tags("desktop");
test("escape closes a dropdown menu rendered as a popover", async () => {
    await mountWithCleanup(DropdownParent);
    await click(".toggler");
    await runAllTimers();
    await animationFrame();
    expect(".ditem").toHaveCount(1);

    await press("escape");
    await runAllTimers();
    await animationFrame();
    expect(".ditem").toHaveCount(0);
});

test("a sheet refused for a detached target does not uncount one that is open", async () => {
    await mountWithCleanup(MainComponentsContainer);

    class MyComp extends Component {
        static template = xml`<div class="sheet-content"/>`;
        static props = ["*"];
    }

    const sheet = getService("bottom_sheet");
    const closeOpen = sheet.add(getFixture(), MyComp);
    await animationFrame();
    expect(document.body).toHaveClass("bottom-sheet-open");

    const detached = document.createElement("div");
    const closeRefused = sheet.add(
        detached,
        MyComp,
        {},
        {
            onClose: () => expect.step("onClose"),
        },
    );
    await animationFrame();
    expect(".sheet-content").toHaveCount(1);
    expect.verifySteps(["onClose"]);
    expect(document.body).toHaveClass("bottom-sheet-open");

    await closeRefused();
    expect(document.body).toHaveClass("bottom-sheet-open");

    closeOpen();
    await runAllTimers();
    await animationFrame();
    expect(document.body).not.toHaveClass("bottom-sheet-open");
});
