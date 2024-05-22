odoo.define('web.field_registry_owl', function (require) {
    "use strict";

    const Registry = require('web.Registry');

    return new Registry(
        null,
        (value) => value.prototype instanceof owl.Component
    );
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
        .add('badge', basicFields.FieldBadge)
        .add('boolean', basicFields.FieldBoolean);
});
