odoo.define('web.field_registry_owl', function (require) {
    "use strict";

    const Registry = require('web.Registry');

    const FieldRegistry = Registry.extend({
        add: function (key, value, score) {
            if (!(value.prototype instanceof owl.Component)) {
                throw new Error("This registry should only contain subclasses of Component");
            }
            return this._super(...arguments);
        },
    });

    return new FieldRegistry();
});

odoo.define('web._field_registry_owl', function (require) {
    "use strict";

    /**
     * This module registers field components (specifications of the AbstractField Component)
     */

    const basicFields = require('web.basic_fields_owl');
    const registry = require('web.field_registry_owl');

    // Basic fields
    registry
        .add('boolean', basicFields.FieldBoolean);
});
