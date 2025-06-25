import { after, destroy, getFixture } from "@odoo/hoot";
import { queryFirst, queryOne } from "@odoo/hoot-dom";
import { App, Component, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { getPopoverForTarget } from "@web/core/popover/popover";
import { getTemplate } from "@web/core/templates";
import { isIterable } from "@web/core/utils/arrays";
import { patch } from "@web/core/utils/patch";
import { getMockEnv, makeMockEnv } from "./env_test_helpers";

/**
 * @typedef {import("@odoo/owl").Component} Component
 *
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 *
 * @typedef {Parameters<typeof import("@odoo/owl").mount>[2]} MountOptions
 *
 * @typedef {import("@odoo/hoot-dom").Target} Target
 */

/**
 * @template [P=any]
 * @template [E=any]
 * @typedef {import("@odoo/owl").ComponentConstructor<P, E>} ComponentConstructor
 */

/**
 * @param {ComponentConstructor} ComponentClass
 * @param {HTMLElement | ShadowRoot} targetEl
 * @param {MountOptions} [options]
 */
const mountComponentWithCleanup = (ComponentClass, targetEl, config) => {
    const app = new App(ComponentClass, config);
    after(() => destroy(app));
    return app.mount(targetEl);
};

patch(MainComponentsContainer.prototype, {
    setup() {
        super.setup();

        hasMainComponent = true;
        after(() => (hasMainComponent = false));
    },
});

let hasMainComponent = false;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {App | Component} parent
 * @param {(component: Component) => boolean} predicate
 * @returns {Component | null}
 */
export function findComponent(parent, predicate) {
    const rootNode = parent instanceof App ? parent.root : parent.__owl__;
    const queue = [rootNode, ...Object.values(rootNode.children)];
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
 * @param {MountOptions & {
 *  fixtureClassName?: string | string[] | null;
 *  env?: E;
 *  noMainContainer?: boolean;
 *  props?: P;
 *  target?: Target;
 * }} [options]
 */
export async function mountWithCleanup(ComponentClass, options) {
    const { fixtureClassName = "o_web_client", env, noMainContainer, target } = options || {};
    const config = {
        getTemplate,
        test: true,
        translateFn: _t,
        warnIfNoStaticProps: true,
        ...options,
        env: env || getMockEnv() || (await makeMockEnv()),
    };
    delete config.fixtureClassName;
    delete config.noMainContainer;
    delete config.target;

    const fixture = getFixture();
    const targetEl = target ? queryOne(target) : fixture;
    if (fixtureClassName) {
        const list = isIterable(fixtureClassName) ? fixtureClassName : [fixtureClassName];
        fixture.classList.add(...list);
    }

    if (typeof ComponentClass === "string") {
        ComponentClass = class extends Component {
            static name = "anonymous component";
            static props = {};
            static template = xml`${ComponentClass}`;
        };
    }

    /** @type {InstanceType<C>} */
    const component = await mountComponentWithCleanup(ComponentClass, targetEl, {
        ...config,
        name: `TEST: ${ComponentClass.name}`,
    });

    if (!noMainContainer && !hasMainComponent) {
        await mountComponentWithCleanup(MainComponentsContainer, targetEl, {
            ...config,
            name: `TEST: ${ComponentClass.name} (main container)`,
            props: {},
        });
    }

    return component;
}
