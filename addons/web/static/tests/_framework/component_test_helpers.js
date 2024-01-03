/** @odoo-module */

import { after } from "@odoo/hoot";
import { getFixture } from "@odoo/hoot-dom";
import { App, Component, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { templates } from "@web/core/templates";
import { getMockEnv, makeMockEnv } from "./env_test_helpers";

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/** @type {typeof import("@odoo/owl").mount} */
const mountAppWithCleanup = (ComponentClass, target, config) => {
    const app = new App(ComponentClass, config);
    after(() => app.destroy());

    return app.mount(target);
};

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
 *  noMainContainer?: boolean;
 *  props?: P;
 *  target?: HTMLElement;
 *  templates?: Document;
 * }} [options]
 */
export async function mountWithCleanup(ComponentClass, options) {
    const config = {
        env: options?.env || getMockEnv() || (await makeMockEnv()),
        props: options?.props || {},
        templates,
        test: true,
        translateFn: _t,
    };
    const target = options?.target || getFixture();

    if (typeof ComponentClass === "string") {
        ComponentClass = class TestComponent extends Component {
            static template = xml`${ComponentClass}`;
        };
    }

    /** @type {InstanceType<C>} */
    const component = await mountAppWithCleanup(ComponentClass, target, config);
    if (
        !options?.noMainContainer &&
        !findComponent(component, (c) => c instanceof MainComponentsContainer)
    ) {
        await mountAppWithCleanup(MainComponentsContainer, target, { ...config, props: {} });
    }

    return component;
}
