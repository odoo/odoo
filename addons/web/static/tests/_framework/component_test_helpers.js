import { after, destroy, getFixture } from "@odoo/hoot";
import { queryFirst, queryOne } from "@odoo/hoot-dom";
import { App, Component, xml } from "@odoo/owl";
import { appTranslateFn } from "@web/core/l10n/translation";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { getPopoverForTarget } from "@web/core/popover/popover";
import { getTemplate as defaultGetTemplate } from "@web/core/templates";
import { isIterable } from "@web/core/utils/arrays";
import { patch } from "@web/core/utils/patch";
import {
    customDirectives as defaultCustomDirectives,
    globalValues as defaultGlobalValues,
} from "@web/env";
import { getMockEnv, makeMockEnv } from "./env_test_helpers";

/**
 * @typedef {import("@odoo/hoot-dom").Target} Target
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

/**
 * @param {ComponentConstructor} ComponentClass
 * @param {HTMLElement | ShadowRoot} targetEl
 * @param {AppConfig} config
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
 *  fixtureClassName?: string | string[] | null;
 *  env?: E;
 *  noMainContainer?: boolean;
 *  props?: P;
 *  target?: Target;
 * }} [options]
 */
export async function mountWithCleanup(ComponentClass, options) {
    const {
        componentEnv,
        containerEnv,
        customDirectives = defaultCustomDirectives,
        env,
        fixtureClassName = "o_web_client",
        getTemplate = defaultGetTemplate,
        globalValues = defaultGlobalValues,
        noMainContainer,
        props,
        target,
        templates,
        translatableAttributes,
        translateFn = appTranslateFn,
    } = options || {};

    // Common component configuration
    const commonConfig = {
        customDirectives,
        getTemplate,
        globalValues,
        templates,
        translatableAttributes,
        translateFn,
        // The following keys are forced to ensure validation of all tested components
        dev: false,
        test: true,
        warnIfNoStaticProps: true,
    };

    // Fixture
    const fixture = getFixture();
    const targetEl = target ? queryOne(target) : fixture;
    if (fixtureClassName) {
        const list = isIterable(fixtureClassName) ? fixtureClassName : [fixtureClassName];
        fixture.classList.add(...list);
    }

    if (typeof ComponentClass === "string") {
        // Convert templates to components (if needed)
        ComponentClass = class extends Component {
            static name = "anonymous component";
            static props = {};
            static template = xml`${ComponentClass}`;
        };
    }

    const commonEnv = env || getMockEnv() || (await makeMockEnv());
    const componentConfig = {
        ...commonConfig,
        env: Object.assign(Object.create(commonEnv), componentEnv),
        name: `TEST: ${ComponentClass.name}`,
        props,
    };

    /** @type {InstanceType<C>} */
    const component = await mountComponentWithCleanup(ComponentClass, targetEl, componentConfig);

    if (!noMainContainer && !hasMainComponent) {
        const containerConfig = {
            ...commonConfig,
            env: Object.assign(Object.create(commonEnv), containerEnv),
            name: `TEST: ${ComponentClass.name} (main container)`,
            props: {},
        };
        await mountComponentWithCleanup(MainComponentsContainer, targetEl, containerConfig);
    }

    return component;
}
