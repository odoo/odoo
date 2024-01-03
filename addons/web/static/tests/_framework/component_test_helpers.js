/** @odoo-module */

import { mountOnFixture } from "@odoo/hoot";
import { App, Component, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { getTemplate } from "@web/core/templates";
import { getMockEnv, makeMockEnv } from "./env_test_helpers";

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
 *  getTemplate?: Document;
 *  noMainContainer?: boolean;
 *  props?: P;
 *  target?: HTMLElement;
 * }} [options]
 */
export async function mountWithCleanup(ComponentClass, options) {
    const config = {
        env: options?.env || getMockEnv() || (await makeMockEnv()),
        getTemplate,
        props: options?.props || {},
        translateFn: _t,
    };

    if (typeof ComponentClass === "string") {
        ComponentClass = class TestComponent extends Component {
            static props = {};
            static template = xml`${ComponentClass}`;
        };
    }

    /** @type {InstanceType<C>} */
    const component = await mountOnFixture(ComponentClass, config, options?.target);
    if (
        !options?.noMainContainer &&
        !findComponent(component, (c) => c instanceof MainComponentsContainer)
    ) {
        await mountOnFixture(MainComponentsContainer, {
            ...config,
            props: {},
        });
    }

    return component;
}
