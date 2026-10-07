import { after, getFixture, queryFirst, queryOne } from "@odoo/hoot";
import { App, Component, onWillDestroy, xml } from "@odoo/owl";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { getPopoverForTarget } from "@web/core/popover/popover";
import { patch } from "@web/core/utils/patch";
import { getTestApp, makeTestApp } from "./app_test_helpers";
import { isSmall } from "./ui_test_helpers";

/**
 * @typedef {import("@odoo/hoot").Target} Target
 * @typedef {import("@odoo/owl").Component} Component
 *
 * @typedef {ConstructorParameters<typeof App>[1]} AppConfig
 */

patch(MainComponentsContainer.prototype, {
    setup() {
        super.setup();

        hasMainComponent = true;
        onWillDestroy(() => {
            hasMainComponent = false;
        });
        after(() => {
            hasMainComponent = false;
        });
    },
});

let hasMainComponent = false;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {App | Component} appOrComponent
 * @param {(component: Component) => boolean} predicate
 * @returns {Component | null}
 */
export function findComponent(appOrComponent, predicate) {
    let compNode;
    if (appOrComponent instanceof App) {
        const [firstRoot] = appOrComponent.roots;
        compNode = firstRoot?.node;
    } else {
        compNode = appOrComponent.__owl__;
    }
    const queue = [compNode, ...Object.values(compNode.children)];
    while (queue.length) {
        const { children, component } = queue.pop();
        if (predicate(component)) {
            return component;
        }
        queue.unshift(...Object.values(children));
    }
    return null;
}

/**
 * Returns the dropdown menu for a specific toggler.
 *
 * @param {Target} togglerSelector
 * @returns {HTMLElement | undefined}
 */
export function getDropdownMenu(togglerSelector) {
    if (isSmall()) {
        return queryFirst(".o-dropdown--menu", { eq: -1 });
    }
    let el = queryFirst(togglerSelector);
    if (el && !el.classList.contains("o-dropdown")) {
        el = el.querySelector(".o-dropdown");
    }
    if (!el) {
        throw new Error(`getDropdownMenu: Could not find element "${togglerSelector}".`);
    }
    return getPopoverForTarget(el);
}

/**
 * Mounts a given component to the test fixture.
 *
 * By default, a `MainComponentsContainer` component is also mounted to the
 * fixture if none is found in the component tree (this can be overridden by the
 * `noMainContainer` option).
 *
 * @template {import("@odoo/owl").ComponentConstructor} C
 * @param {C | string} ComponentClass
 * @param {AppConfig & {
 *  noMainContainer?: boolean;
 *  props?: object;
 *  target?: Target;
 * }} [options]
 */
export async function mountWithCleanup(ComponentClass, options) {
    const { noMainContainer, props, target } = options || {};

    // Fixture
    const fixture = getFixture();
    const targetEl = target ? queryOne(target) : fixture;
    fixture.classList.add("o_web_client");

    if (typeof ComponentClass === "string") {
        // Convert templates to components (if needed)
        ComponentClass = class extends Component {
            static name = "anonymous component";
            static template = xml`${ComponentClass}`;
        };
    }

    const app = getTestApp() || (await makeTestApp());
    const componentRoot = app.createRoot(ComponentClass, { props });
    /** @type {InstanceType<C>} */
    const component = await componentRoot.mount(targetEl);

    if (!noMainContainer && !hasMainComponent) {
        const mainContainerRoot = app.createRoot(MainComponentsContainer);
        await mainContainerRoot.mount(targetEl);
    }

    return component;
}

/**
 * @param {App | Component} appOrComponent
 */
export async function waitUntilIdle(appOrComponent) {
    function isIdle() {
        return scheduler.tasks.size === 0;
    }

    const { scheduler } =
        appOrComponent instanceof App ? appOrComponent : appOrComponent.__owl__.app;

    if (isIdle()) {
        return Promise.resolve(true);
    }

    return new Promise((resolve) => {
        const unpatch = patch(scheduler, {
            processTasks() {
                const result = super.processTasks(...arguments);
                if (isIdle()) {
                    unpatch();
                    resolve(true);
                }
                return result;
            },
        });
    });
}
