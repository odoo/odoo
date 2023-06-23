/** @odoo-module **/

    import Registry from "@web/legacy/js/core/registry";

    const { Component } = owl;

    export default new Registry(
        null,
        (value) => !(value.prototype instanceof Component)
    );
