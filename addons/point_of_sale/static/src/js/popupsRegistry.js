odoo.define('point_of_sale.popupsRegistry', function(require) {
    'use strict';

    class PopupsRegistry {
        constructor() {
            this.registry = {};
        }
        add(popupComponent) {
            this.registry[popupComponent.name] = popupComponent;
        }
        get(popupName) {
            return this.registry[popupName];
        }
    }

    const popupsRegistry = new PopupsRegistry();

    return { popupsRegistry };
});
