// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, microTick } from "@odoo/hoot-mock";
import { Component, onMounted, onWillRender, useState, xml } from "@odoo/owl";
import {
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { useActiveElementScope } from "@web/core/utils/active_element_scope";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { useCommand } from "@web/ui/commands/command_hook";
import { Dialog } from "@web/ui/dialog/dialog";
import { MainComponentsContainer } from "@web/ui/main_components_container";
import { usePopover } from "@web/ui/popover/popover_hook";
import { SIZES } from "@web/ui/viewport";

describe.current.tags("desktop");

/**
 * @param {Document | HTMLElement} el
 * @returns {string[]}
 */
function commandNamesFor(el) {
    return getService("command")
        .getCommands(el)
        .map((/** @type {{ name: string }} */ c) => c.name);
}

test("a command keeps the scope it was registered in when another element is activated later", async () => {
    await makeMockEnv();
    const command = getService("command");
    const ui = getService("ui");

    command.add("registered-under-document", () => {});

    const later = document.createElement("div");
    document.body.appendChild(later);
    ui.activateElement(later);
    await microTick();

    expect(commandNamesFor(document)).toEqual(["registered-under-document"]);
    expect(commandNamesFor(later)).toEqual([]);

    ui.deactivateElement(later);
    later.remove();
});

test("a hotkey keeps the scope it was registered in when another element is activated later", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");
    const ui = getService("ui");

    hotkey.add("alt+q", () => {});

    const later = document.createElement("div");
    document.body.appendChild(later);
    ui.activateElement(later);
    await microTick();

    const registration = /** @type {any} */ (
        [...hotkey.registrations.values()].find(
            (/** @type {{ hotkey: string }} */ r) => r.hotkey === "alt+q",
        )
    );
    expect(registration.getScope()).toBe(document);

    ui.deactivateElement(later);
    later.remove();
});

test("useCommand binds to the active element owning the component, not to the newest one", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    class Outside extends Component {
        static template = xml`<div class="outside"/>`;
        static props = {};
        setup() {
            useCommand("outside", () => {});
        }
    }
    class Inside extends Component {
        static template = xml`<div class="inside"/>`;
        static props = ["*"];
        setup() {
            useCommand("inside", () => {});
        }
    }
    class InDialog extends Component {
        static template = xml`<Dialog><Inside/></Dialog>`;
        static components = { Dialog, Inside };
        static props = ["*"];
    }

    await mountWithCleanup(Outside);
    getService("dialog").add(InDialog, {});
    await animationFrame();
    await microTick();

    const modal = /** @type {HTMLElement} */ (document.querySelector(".modal"));
    expect(modal).not.toBe(/** @type {any} */ (null));
    expect(commandNamesFor(document)).toEqual(["outside"]);
    expect(commandNamesFor(modal)).toEqual(["inside"]);
});

test("a component rendering a dialog is scoped to that dialog", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    /** @type {(() => Document | HTMLElement) | null} */
    let ambient = null;
    /** @type {(() => Document | HTMLElement) | null} */
    let declared = null;
    class RendersADialog extends Component {
        static template = xml`<Dialog modalRef="modalRef"><div class="body"/></Dialog>`;
        static components = { Dialog };
        static props = ["*"];
        setup() {
            this.modalRef = useChildRef();
            ambient = useActiveElementScope();
            declared = () => /** @type {any} */ (this.modalRef).el;
        }
    }
    getService("dialog").add(RendersADialog, {});
    await animationFrame();

    const modal = /** @type {HTMLElement} */ (document.querySelector(".modal"));
    expect(getService("ui").activeElement).toBe(modal);
    expect(/** @type {any} */ (ambient)()).toBe(modal);
    expect(/** @type {any} */ (declared)()).toBe(modal);

    // a dialog it opens takes the active element away from it
    class Sub extends Component {
        static template = xml`<Dialog><div class="sub"/></Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }
    getService("dialog").add(Sub, {});
    await animationFrame();
    expect(getService("ui").activeElement).not.toBe(modal);
    expect(/** @type {any} */ (ambient)()).toBe(modal);
});

test("a component beside an open dialog is scoped to the document, not to the dialog", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    class Bare extends Component {
        static template = xml`<Dialog><div class="body"/></Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }
    getService("dialog").add(Bare, {});
    await animationFrame();

    /** @type {(() => Document | HTMLElement) | null} */
    let outsideScope = null;
    class Outside extends Component {
        static template = xml`<div class="outside"/>`;
        static props = {};
        setup() {
            outsideScope = useActiveElementScope();
        }
    }
    await mountWithCleanup(Outside);

    expect(getService("ui").activeElement).toBe(
        /** @type {HTMLElement} */ (document.querySelector(".modal")),
    );
    expect(/** @type {any} */ (outsideScope)()).toBe(document);
});

test("isSmall is its own reactive key, so a same-band resize does not invalidate it", async () => {
    let width = 1000;
    /** @type {(() => void)[]} */
    const listeners = [];
    patchWithCleanup(browser, {
        matchMedia: (/** @type {string} */ query) => {
            const min = Number(/min-width:\s*(\d+)/.exec(query)?.[1] ?? 0);
            return /** @type {any} */ ({
                get matches() {
                    return width >= min;
                },
                addEventListener: (
                    /** @type {string} */ _type,
                    /** @type {any} */ cb,
                ) => listeners.push(cb),
                removeEventListener: () => {},
            });
        },
    });
    const env = await makeMockEnv(undefined, { makeNew: true });
    const ui = /** @type {any} */ (env.services.ui);

    class Reader extends Component {
        static template = xml`<div class="reader" t-esc="ui.isSmall"/>`;
        static props = {};
        setup() {
            /** @type {any} */
            this.ui = useState(useService("ui"));
            onWillRender(() => expect.step(`render ${this.ui.isSmall}`));
        }
    }
    await mountWithCleanup(Reader, { env });
    expect.verifySteps(["render false"]);

    width = 1300;
    listeners.forEach((cb) => cb());
    await animationFrame();
    expect(ui.size).toBe(SIZES.XL);
    expect.verifySteps([]);

    width = 400;
    listeners.forEach((cb) => cb());
    await animationFrame();
    expect(ui.isSmall).toBe(true);
    expect.verifySteps(["render true"]);
});

test("popover content inherits the opener's scope only when the opener passes env", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    /** @type {Record<string, () => Document | HTMLElement>} */
    const scopes = {};
    class Content extends Component {
        static template = xml`<div class="pop"/>`;
        static props = ["*"];
        setup() {
            scopes[this.props.tag] = useActiveElementScope();
        }
    }
    class Body extends Component {
        static template = xml`<div class="body"/>`;
        static props = ["*"];
        setup() {
            const withEnv = usePopover(Content, {
                setActiveElement: false,
                env: /** @type {any} */ (this).__owl__.childEnv,
            });
            const withoutEnv = usePopover(Content, { setActiveElement: false });
            onMounted(() => {
                withEnv.open(document.body, { tag: "withEnv" });
                withoutEnv.open(document.body, { tag: "withoutEnv" });
            });
        }
    }
    class InDialog extends Component {
        static template = xml`<Dialog><Body/></Dialog>`;
        static components = { Dialog, Body };
        static props = ["*"];
    }
    getService("dialog").add(InDialog, {});
    await animationFrame();
    await animationFrame();

    const modal = /** @type {HTMLElement} */ (document.querySelector(".modal"));
    expect(getService("ui").activeElement).toBe(modal);
    expect(scopes.withEnv()).toBe(modal);
    expect(scopes.withoutEnv()).toBe(document);
});
