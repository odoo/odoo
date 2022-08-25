odoo.define('web.field_registry_owl', function (require) {
    "use strict";

    const Registry = require('web.Registry');

    const { Component } = owl;

    return new Registry(
        null,
        (value) => value.prototype instanceof Component
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
        .add('badge', basicFields.FieldBadge);
        // deactivate the owl FieldBoolean as it causes issues in the Settings form view
        // if it is in an invisible block. This was a legacy implementation of the owl FieldBoolean
        // anyway, and we're currently rewritting the basic views in owl.
        // .add('boolean', basicFields.FieldBoolean);
});
