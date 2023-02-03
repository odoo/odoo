odoo.define('web.field_registry_owl', function (require) {
    "use strict";

    const Registry = require('web.Registry');

    const { Component } = owl;

    return new Registry(
        null,
        (value) => value.prototype instanceof Component
    );
});
