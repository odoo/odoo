import { after, getFixture, mountOnFixture } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { App } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { getPopoverForTarget } from "@web/core/popover/popover";
import { getTemplate } from "@web/core/templates";
import { patch } from "@web/core/utils/patch";
import { getMockEnv, makeMockEnv } from "./env_test_helpers";

/**
 * @typedef {import("@odoo/owl").Component} Component
 *
 * @typedef {import("@odoo/hoot-dom").Target} Target
 */

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
 * @template {import("@odoo/owl").ComponentConstructor<P, E>} C
 * @template [P={}]
 * @template [E=import("@web/env").OdooEnv]
 * @param {C | string} ComponentClass
 * @param {{
 *  env?: E;
 *  getTemplate?: Document;
 *  noMainContainer?: boolean;
 *  props?: P;
 *  target?: Target;
 * }} [options]
 */
export async function mountWithCleanup(ComponentClass, options) {
    const config = {
        env: options?.env || getMockEnv() || (await makeMockEnv()),
        getTemplate,
        props: options?.props || {},
        translateFn: _t,
    };

    getFixture().classList.add("o_web_client");

    /** @type {InstanceType<C>} */
    const component = await mountOnFixture(ComponentClass, config, options?.target);
    if (!options?.noMainContainer && !hasMainComponent) {
        await mountOnFixture(MainComponentsContainer, { ...config, props: {} });
    }

    return component;
}
