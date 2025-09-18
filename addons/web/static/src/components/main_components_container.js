// @ts-check

/** @module @web/components/main_components_container - Renders all dynamically registered main_components from the registry */

import { Component, xml } from "@odoo/owl";
import { registry, useRegistry } from "@web/core/registry";
import { ErrorHandler } from "@web/core/utils/components";
/** @type {import("@web/core").Registry} */
const mainComponents = registry.category("main_components");

mainComponents.addValidation({
    Component: { validate: (c) => c.prototype instanceof Component },
    props: { type: Object, optional: true },
});

export class MainComponentsContainer extends Component {
    static components = { ErrorHandler };
    static props = {};
    static template = xml`
    <div class="o-main-components-container">
        <t t-foreach="Components.entries" t-as="C" t-key="C[0]">
            <ErrorHandler onError="error => this.handleComponentError(error, C)">
                <t t-component="C[1].Component" t-props="C[1].props"/>
            </ErrorHandler>
        </t>
    </div>
    `;

    setup() {
        this.Components = useRegistry(mainComponents);
    }

    /**
     * Remove the faulty component from the registry snapshot and re-render.
     * The error is re-thrown asynchronously so Owl finishes its render cycle first.
     * @param {Error} error - the error thrown by the child component
     * @param {[string, {Component: typeof Component, props?: Object}]} C - registry entry
     */
    handleComponentError(error, C) {
        this.Components.entries.splice(this.Components.entries.indexOf(C), 1);
        this.render();
        // Re-throw after a microtask so Owl can finish its render cycle first.
        Promise.resolve().then(() => {
            throw error;
        });
    }
}
