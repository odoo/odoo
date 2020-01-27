odoo.define('point_of_sale.PosComponent', function(require) {
    'use strict';

    class PosComponent extends owl.Component {}
    PosComponent.addComponents = function(components) {
        for (let component of components) {
            if (this.components[component.name]) {
                console.error(`${component.name} already exists in ${this.name}'s components so it was skipped.`);
            } else {
                this.components[component.name] = component;
            }
        }
    };

    return { PosComponent };
});
