odoo.define('point_of_sale.Registries', function(require) {
    'use strict';

    /**
     * This definition contains all the instances of ClassRegistry.
     */

    const ComponentRegistry = require('point_of_sale.ComponentRegistry');
    const ClassRegistry = require('point_of_sale.ClassRegistry');

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
            }
        }
    }

    return { Component: new ComponentRegistry(), Model: new ModelRegistry() };
});
