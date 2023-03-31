/** @odoo-module alias=web.field_registry **/
    
    import Registry from "web.Registry";

    const { Component } = owl;

    export default new Registry(
        null,
        (value) => !(value.prototype instanceof Component)
    );
