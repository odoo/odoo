odoo.define('web.field_registry', function (require) {
    "use strict";

    const Registry = require('web.Registry');

    const { Component } = owl;

    return new Registry(
        null,
        (value) => !(value.prototype instanceof Component)
    );
});
