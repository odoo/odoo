/** @odoo-module alias=@web/../tests/helpers/mount_in_fixture default=false**/

import { App, Component, xml } from "@odoo/owl";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { mocks } from "@web/../tests/helpers/mock_services";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { getTemplate } from "@web/core/templates";

class TestComponent extends Component {
    static props = {
        components: { type: Array },
    };

    static template = xml`
        <t t-foreach="props.components" t-as="comp" t-key="comp.component.name">
            <t t-component="comp.component" t-props="comp.props"/>
        </t>
    `;

    /**
     * Returns the instance of the first component.
     * @returns {Component}
     */
    get defaultComponent() {
        return this.__owl__.bdom.children[0].child.component;
    }
}

function getApp(env, props) {
    const appConfig = {
        env,
        getTemplate,
        test: true,
        props: props,
    };
    if (env.services && "localization" in env.services) {
        appConfig.translateFn = env._t;
    }
    const app = new App(TestComponent, appConfig);
    registerCleanup(() => app.destroy());
    return app;
}

/**
 * @typedef {Object} Config
 * @property {Object} env
 * @property {Object} props
 * @property {string[]} templates
 */

/**
 * This functions will mount the given component and
 * will add a MainComponentsContainer if the overlay
 * service is loaded.
 *
 * @template T
 * @param {new (...args: any[]) => T} Comp
 * @param {HTMLElement} target
 * @param {Config} config
 * @returns {Promise<T>} Instance of Comp
 */
export async function mountInFixture(Comp, target, config = {}) {
    const serviceRegistry = registry.category("services");

    let env = config.env || {};
    const isEnvInitialized = env && env.services;

    function isServiceRegistered(serviceName) {
        return isEnvInitialized
            ? serviceName in env.services
            : serviceRegistry.contains(serviceName);
    }

    async function addService(serviceName, service) {
        if (isServiceRegistered(serviceName)) {
            return;
        }

        service = typeof service === "function" ? service() : service;
        if (isEnvInitialized) {
            env.services[serviceName] = await service.start(env);
        } else {
            serviceRegistry.add(serviceName, service);
        }
    }

    const components = [{ component: Comp, props: config.props || {} }];
    if (isServiceRegistered("overlay")) {
        await addService("localization", mocks.localization);
        components.push({ component: MainComponentsContainer, props: {} });
    }

    if (!isEnvInitialized) {
        env = await makeTestEnv(env);
    }

    const app = getApp(env, { components });

    if (config.templates) {
        app.addTemplates(config.templates);
    }

    const testComp = await app.mount(target);
    return testComp.defaultComponent;
}
