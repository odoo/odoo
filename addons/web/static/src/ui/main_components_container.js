// @ts-check
/** @odoo-module native */

import { Component, xml } from "@odoo/owl";
import { reportUncaught } from "@web/core/errors/error_utils";
import { localization } from "@web/core/l10n/localization";
import { registry, useRegistry } from "@web/core/registry";
import { ErrorHandler } from "@web/core/utils/components";
const mainComponents = registry.category("main_components");

mainComponents.addValidation({
    Component: {
        validate: (/** @type {import("@odoo/owl").ComponentConstructor} */ c) =>
            c.prototype instanceof Component,
    },
    props: { type: Object, optional: true },
});

/** @type {WeakMap<import("@odoo/owl").ComponentConstructor, import("registries").MainComponentsRegistryItemShape>} */
const ENTRIES = new WeakMap();

/**
 * @param {import("@odoo/owl").ComponentConstructor} Component
 * @returns {import("registries").MainComponentsRegistryItemShape}
 */
export function mainComponentEntry(Component) {
    let entry = ENTRIES.get(Component);
    if (!entry) {
        entry = { Component };
        ENTRIES.set(Component, entry);
    }
    return entry;
}

export class MainComponentsContainer extends Component {
    static components = { ErrorHandler };
    static props = {};
    static template = xml`
    <div class="o-main-components-container" t-att-class="{'o_rtl': this.isRTL}">
        <t t-foreach="this.Components.entries" t-as="C" t-key="C[0]">
            <ErrorHandler onError="error => this.handleComponentError(error, C)">
                <t t-component="C[1].Component" t-props="C[1].props"/>
            </ErrorHandler>
        </t>
    </div>
    `;

    /** @type {ReturnType<typeof useRegistry>} */
    Components;

    setup() {
        this.Components = useRegistry(mainComponents);
        this.isRTL = localization.direction === "rtl";
    }

    /**
     * @param {Error} error
     * @param {[string, {Component: typeof Component, props?: Object}]} C
     */
    handleComponentError(error, C) {
        if (mainComponents.contains(C[0])) {
            mainComponents.remove(C[0]);
        }
        reportUncaught(error);
    }
}
