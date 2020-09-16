odoo.define('mail/static/src/component_hooks/use_models/use_models.js', function (require) {
'use strict';

const { Component } = owl;

function useModels() {
    const component = Component.current;
    component.mself = component; // used to have reference in template
    component.env.modelManager.registerObserver(component);
    const __destroy = component.__destroy;
    component.__destroy = (parent) => {
        component.env.modelManager.unregisterObserver(component);
        __destroy.call(component, parent);
    };
}

return useModels;

});
