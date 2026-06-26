import { after, getFixture, queryFirst, queryOne } from "@odoo/hoot";
import { App, Component, onWillDestroy, xml } from "@odoo/owl";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { getPopoverForTarget } from "@web/core/popover/popover";
import { patch } from "@web/core/utils/patch";
import { getMockEnv, getTestApp, makeMockEnv } from "./app_test_helpers";
import { patchWithCleanup } from "./patch_test_helpers";

import { makeMockServer, MockServer } from "./mock_server/mock_server";

/**
 * @typedef {import("@odoo/hoot").Target} Target
 * @typedef {import("@odoo/owl").Component} Component
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 *
 * @typedef {ConstructorParameters<typeof App>[1]} AppConfig
 */

/**
 * @template [P=any]
 * @template [E=any]
 * @typedef {import("@odoo/owl").ComponentConstructor<P, E>} ComponentConstructor
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
    if (getMockEnv().isSmall) {
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
 * @template {ComponentConstructor<P, E>} C
 * @template [P={}]
 * @template [E=OdooEnv]
 * @param {C | string} ComponentClass
 * @param {AppConfig & {
 *  componentEnv?: Partial<OdooEnv>;
 *  containerEnv?: Partial<OdooEnv>;
 *  env?: E;
 *  noMainContainer?: boolean;
 *  props?: P;
 *  target?: Target;
 * }} [options]
 */
export async function mountWithCleanup(ComponentClass, options) {
    const { componentEnv, containerEnv, env, name, noMainContainer, props, target } = options || {};

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

    if (!MockServer.current) {
        // need a mock server before starting app (which starts plugins which
        // may need network)
        await makeMockServer();
    }

    const commonEnv = env || getMockEnv() || (await makeMockEnv());
    const app = getTestApp({ name: name || `TEST: ${ComponentClass.name}`, env });

    const componentRoot = app.createRoot(ComponentClass, {
        env: Object.assign(Object.create(commonEnv), componentEnv),
        props,
    });
    /** @type {InstanceType<C>} */
    const component = await componentRoot.mount(targetEl);

    if (!noMainContainer && !hasMainComponent) {
        const mainContainerRoot = app.createRoot(MainComponentsContainer, {
            env: Object.assign(Object.create(commonEnv), containerEnv),
            props: {},
        });
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
        const unpatch = patchWithCleanup(scheduler, {
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
