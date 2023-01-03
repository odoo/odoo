/** @odoo-module */
/**
 * This definition contains all the instances of ClassRegistry.
 */

import ComponentRegistry from "@point_of_sale/js/ComponentRegistry";
import ClassRegistry from "@point_of_sale/js/ClassRegistry";

class ModelRegistry extends ClassRegistry {
    add(baseClass) {
        super.add(baseClass);
        /**
         * Introduce a static method (`create`) to each base class that can be
         * conveniently use to create an instance of the extended version
         * of the class.
         */
        baseClass.create = (...args) => {
            const ExtendedClass = this.get(baseClass);
            return new ExtendedClass(...args);
        };
    }
}

export const Component = new ComponentRegistry();
export const Model = new ModelRegistry();

export default { Component, Model };
